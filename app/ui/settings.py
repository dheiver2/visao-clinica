"""Preferências de interface persistidas (acessibilidade e sessão).

Guarda escala de fonte, alto contraste e timeout de sessão num JSON gravável.
"""

from __future__ import annotations

import contextlib
import json

from app.paths import data_path

_PATH = data_path("data", "ui_settings.json")
_DEFAULTS = {"font_scale": 1.0, "high_contrast": False, "session_timeout_min": 15}


def load() -> dict:
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    return {**_DEFAULTS, **{k: data[k] for k in _DEFAULTS if k in data}}


def save(settings: dict) -> None:
    merged = {**_DEFAULTS, **{k: settings[k] for k in _DEFAULTS if k in settings}}
    with contextlib.suppress(OSError):
        _PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
