"""Resolução central de caminhos — funciona tanto em desenvolvimento quanto
empacotado pelo PyInstaller (`.app` autocontido).

Dois espaços distintos:

* **recursos (read-only)** — assets embutidos no bundle (modelos `.task`/`.gguf`).
  Em modo congelado vivem em ``sys._MEIPASS``; em dev, na raiz do projeto.
* **dados do usuário (graváveis)** — banco SQLite, PDFs/CSVs, store NR-01,
  downloads de modelos. NUNCA dentro do bundle (read-only). Em macOS:
  ``~/Library/Application Support/VisaoClinica``.

Assim o mesmo código roda do `python -m app.main` e do `.app` distribuído.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "VisaoClinica"


def is_frozen() -> bool:
    """True quando rodando dentro de um bundle PyInstaller."""
    return bool(getattr(sys, "frozen", False))


def resource_dir() -> Path:
    """Raiz dos recursos read-only embutidos."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parents[1]


def user_data_dir() -> Path:
    """Diretório gravável e persistente para dados do usuário."""
    override = os.environ.get("VISAOCLINICA_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


def bundled_models_dir() -> Path:
    """``models/`` embutido no bundle (read-only) — pode conter assets."""
    return resource_dir() / "models"


def models_dir() -> Path:
    """``models/`` gravável (downloads de modelos na 1ª execução)."""
    d = user_data_dir() / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_path(*parts: str) -> Path:
    """Caminho gravável em dados do usuário, criando o diretório-pai."""
    p = user_data_dir().joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p
