"""Store de governança (SQLite, offline) — conformidade para licitação.

Reúne, no mesmo banco das sessões, três domínios exigidos por editais públicos:

- **Controle de acesso**: usuários com perfil (administrador/profissional/
  pesquisador) e senha com hash forte (PBKDF2-HMAC-SHA256, sem dependências).
- **Trilha de auditoria (LGPD)**: log append-only de eventos com usuário e
  data/hora — não há API de UPDATE/DELETE de eventos (imutável por design).
- **Dados institucionais**: nome/CNPJ/logo do órgão e responsável técnico, usados
  nos relatórios.

Inclui backup/restauração via a API nativa de backup do SQLite (consistente).
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

from app.paths import data_path

DEFAULT_DB = data_path("data", "sessions.db")
ROLES = ("administrador", "profissional", "pesquisador")
_PBKDF2_ITERATIONS = 200_000

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT UNIQUE NOT NULL,
    salt       TEXT NOT NULL,
    pwd_hash   TEXT NOT NULL,
    role       TEXT NOT NULL,
    active     INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS audit_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT DEFAULT (datetime('now','localtime')),
    username TEXT,
    event    TEXT NOT NULL,
    detail   TEXT
);
CREATE TABLE IF NOT EXISTS institution (
    id          INTEGER PRIMARY KEY CHECK (id = 1),
    nome        TEXT, cnpj TEXT, responsavel TEXT, conselho TEXT, logo_path TEXT
);
"""

_INST_FIELDS = ("nome", "cnpj", "responsavel", "conselho", "logo_path")


def validate_password(pwd: str) -> str | None:
    """Política mínima de senha. Retorna mensagem de erro ou None se válida."""
    if len(pwd) < 8:
        return "A senha deve ter ao menos 8 caracteres."
    if not any(c.isalpha() for c in pwd) or not any(c.isdigit() for c in pwd):
        return "A senha deve conter letras e números."
    return None


def _hash(pwd: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", pwd.encode("utf-8"), bytes.fromhex(salt_hex), _PBKDF2_ITERATIONS).hex()


class GovernanceStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._c = sqlite3.connect(self.db_path)
        self._c.executescript(_SCHEMA)
        self._c.commit()

    # -- usuários / controle de acesso ------------------------------------------

    def user_count(self) -> int:
        return int(self._c.execute("SELECT COUNT(*) FROM users WHERE active=1").fetchone()[0])

    def create_user(self, username: str, password: str, role: str) -> None:
        username = username.strip()
        if not username:
            raise ValueError("Informe um nome de usuário.")
        if role not in ROLES:
            raise ValueError("Perfil inválido.")
        err = validate_password(password)
        if err:
            raise ValueError(err)
        salt = os.urandom(16).hex()
        try:
            self._c.execute(
                "INSERT INTO users (username, salt, pwd_hash, role) VALUES (?, ?, ?, ?)",
                (username, salt, _hash(password, salt), role))
            self._c.commit()
        except sqlite3.IntegrityError as e:
            raise ValueError("Já existe um usuário com esse nome.") from e

    def verify(self, username: str, password: str) -> str | None:
        """Retorna o perfil se as credenciais conferem; caso contrário, None."""
        row = self._c.execute(
            "SELECT salt, pwd_hash, role FROM users WHERE username=? AND active=1",
            (username.strip(),)).fetchone()
        if not row:
            return None
        salt, stored, role = row
        return role if _hash(password, salt) == stored else None

    def list_users(self) -> list[dict]:
        return [{"id": i, "username": u, "role": r, "active": bool(a), "created_at": c}
                for i, u, r, a, c in self._c.execute(
                    "SELECT id, username, role, active, created_at FROM users "
                    "ORDER BY username")]

    def set_password(self, username: str, password: str) -> None:
        err = validate_password(password)
        if err:
            raise ValueError(err)
        salt = os.urandom(16).hex()
        self._c.execute("UPDATE users SET salt=?, pwd_hash=? WHERE username=?",
                        (salt, _hash(password, salt), username.strip()))
        self._c.commit()

    def set_active(self, username: str, active: bool) -> None:
        self._c.execute("UPDATE users SET active=? WHERE username=?",
                        (1 if active else 0, username.strip()))
        self._c.commit()

    # -- auditoria (append-only) ------------------------------------------------

    def log(self, username: str | None, event: str, detail: str = "") -> None:
        self._c.execute("INSERT INTO audit_log (username, event, detail) VALUES (?, ?, ?)",
                        (username or "-", event, detail))
        self._c.commit()

    def audit(self, limit: int = 1000) -> list[dict]:
        return [{"ts": t, "username": u, "event": e, "detail": d}
                for t, u, e, d in self._c.execute(
                    "SELECT ts, username, event, detail FROM audit_log "
                    "ORDER BY id DESC LIMIT ?", (int(limit),))]

    # -- dados institucionais ---------------------------------------------------

    def get_institution(self) -> dict:
        row = self._c.execute(
            "SELECT nome, cnpj, responsavel, conselho, logo_path FROM institution "
            "WHERE id=1").fetchone()
        if not row:
            return dict.fromkeys(_INST_FIELDS, "")
        return dict(zip(_INST_FIELDS, [v or "" for v in row], strict=False))

    def set_institution(self, data: dict) -> None:
        vals = tuple(data.get(f, "") for f in _INST_FIELDS)
        self._c.execute(
            "INSERT INTO institution (id, nome, cnpj, responsavel, conselho, logo_path) "
            "VALUES (1, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET nome=excluded.nome, cnpj=excluded.cnpj, "
            "responsavel=excluded.responsavel, conselho=excluded.conselho, "
            "logo_path=excluded.logo_path", vals)
        self._c.commit()

    # -- backup / restauração ---------------------------------------------------

    def backup_to(self, path: str | Path) -> Path:
        """Cópia consistente do banco (API de backup do SQLite)."""
        path = Path(path)
        dst = sqlite3.connect(path)
        try:
            with dst:
                self._c.backup(dst)
        finally:
            dst.close()
        return path

    def restore_from(self, path: str | Path) -> None:
        """Sobrescreve o banco atual com o conteúdo do arquivo informado."""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de backup não encontrado: {path}")
        src = sqlite3.connect(path)
        try:
            with self._c:
                src.backup(self._c)
        finally:
            src.close()

    def close(self) -> None:
        self._c.close()
