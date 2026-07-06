"""Testa a governança para conformidade de licitação: controle de acesso,
auditoria (LGPD), dados institucionais e backup/restauração."""

import tempfile
from pathlib import Path

import pytest

from app.security.governance import GovernanceStore, validate_password


def _store(tmp_path, name="g.db"):
    return GovernanceStore(Path(tmp_path) / name)


def test_password_policy():
    assert validate_password("curta") is not None
    assert validate_password("semnumeros") is not None
    assert validate_password("12345678") is not None
    assert validate_password("boaSenha1") is None


def test_user_lifecycle_and_auth(tmp_path):
    g = _store(tmp_path)
    assert g.user_count() == 0
    g.create_user("admin", "Admin1234", "administrador")
    assert g.user_count() == 1
    assert g.verify("admin", "Admin1234") == "administrador"
    assert g.verify("admin", "errada") is None
    with pytest.raises(ValueError):
        g.create_user("admin", "Outro1234", "administrador")   # duplicado
    with pytest.raises(ValueError):
        g.create_user("x", "fraca", "administrador")           # senha fraca
    with pytest.raises(ValueError):
        g.create_user("y", "Boa12345", "perfil_invalido")      # perfil inválido


def test_password_reset_and_deactivation(tmp_path):
    g = _store(tmp_path)
    g.create_user("p", "Pesq1234", "pesquisador")
    g.set_password("p", "NovaSenha9")
    assert g.verify("p", "NovaSenha9") == "pesquisador"
    g.set_active("p", False)
    assert g.verify("p", "NovaSenha9") is None                 # inativo não loga


def test_audit_log_append_only(tmp_path):
    g = _store(tmp_path)
    g.log("admin", "login", "perfil=administrador")
    g.log("admin", "analise", "risco=baixo")
    events = g.audit(10)
    assert len(events) == 2
    assert events[0]["event"] == "analise"                     # mais recente primeiro
    assert events[0]["username"] == "admin"


def test_institution_roundtrip(tmp_path):
    g = _store(tmp_path)
    assert g.get_institution()["nome"] == ""
    g.set_institution({"nome": "Órgão X", "cnpj": "00.000.000/0001-00",
                       "responsavel": "Dr. Y", "conselho": "CRM 1"})
    inst = g.get_institution()
    assert inst["nome"] == "Órgão X"
    assert inst["responsavel"] == "Dr. Y"


def test_backup_and_restore(tmp_path):
    g = _store(tmp_path, "orig.db")
    g.create_user("admin", "Admin1234", "administrador")
    g.set_institution({"nome": "Órgão X"})
    bkp = Path(tmp_path) / "bkp.db"
    g.backup_to(bkp)
    g2 = _store(tempfile.mkdtemp(), "empty.db")
    assert g2.user_count() == 0
    g2.restore_from(bkp)
    assert g2.verify("admin", "Admin1234") == "administrador"
    assert g2.get_institution()["nome"] == "Órgão X"
