"""Persistência local em SQLite (offline)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.paths import data_path

DEFAULT_DB = data_path("data", "sessions.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at    TEXT DEFAULT (datetime('now')),
    mode          TEXT,
    features_json TEXT,
    analysis_json TEXT,
    risk_level    TEXT
);
"""


class SessionStore:
    def __init__(self, db_path: Path | str = DEFAULT_DB):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.executescript(_SCHEMA)

    def save(self, mode: str, features: dict, analysis: dict) -> int:
        cur = self._conn.execute(
            "INSERT INTO sessions (mode, features_json, analysis_json, risk_level) "
            "VALUES (?, ?, ?, ?)",
            (mode, json.dumps(features, ensure_ascii=False),
             json.dumps(analysis, ensure_ascii=False),
             analysis.get("risk_level", "indeterminado")),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def recent(self, limit: int = 50, mode: str | None = None) -> list[dict]:
        """Últimas sessões (mais recentes primeiro) com features/analysis já decodificados."""
        sql = ("SELECT id, created_at, mode, features_json, analysis_json, risk_level "
               "FROM sessions")
        params: tuple = ()
        if mode:
            sql += " WHERE mode = ?"
            params = (mode,)
        sql += " ORDER BY id DESC LIMIT ?"
        params = params + (int(limit),)
        rows = self._conn.execute(sql, params).fetchall()
        out: list[dict] = []
        for rid, created, md, fj, aj, risk in rows:
            try:
                feats = json.loads(fj) if fj else {}
            except json.JSONDecodeError:
                feats = {}
            try:
                analysis = json.loads(aj) if aj else {}
            except json.JSONDecodeError:
                analysis = {}
            out.append({"id": rid, "created_at": created, "mode": md,
                        "features": feats, "analysis": analysis, "risk_level": risk})
        return out

    def close(self) -> None:
        self._conn.close()
