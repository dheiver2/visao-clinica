"""Tema dark (black) e helpers visuais da interface."""

from __future__ import annotations

# Paleta
BG = "#0a0b0e"
PANEL = "#14161b"
PANEL_2 = "#1b1e25"
BORDER = "#2a2e37"
TEXT = "#e6e8ec"
MUTED = "#8b909b"
ACCENT = "#4c8dff"

# Cores por nível de risco
LEVEL_COLOR = {
    "alto": "#ff5c5c",
    "moderado": "#ffb020",
    "baixo": "#3ecf8e",
    "indeterminado": "#6b7280",
}

QSS = f"""
* {{
    font-family: -apple-system, "SF Pro Text", "Segoe UI", sans-serif;
    color: {TEXT};
}}
QWidget {{ background: {BG}; }}
QLabel#title {{ font-size: 16px; font-weight: 600; }}
QLabel#subtitle {{ color: {MUTED}; font-size: 12px; }}
QLabel#sectionTitle {{ color: {MUTED}; font-size: 11px; font-weight: 600;
    letter-spacing: 1px; }}

QComboBox {{
    background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 6px 10px; min-width: 120px;
}}
QComboBox QAbstractItemView {{ background: {PANEL_2}; selection-background-color: {ACCENT}; }}

QPushButton {{
    background: {ACCENT}; color: white; border: none; border-radius: 8px;
    padding: 8px 18px; font-weight: 600;
}}
QPushButton:hover {{ background: #5d99ff; }}
QPushButton:disabled {{ background: {PANEL_2}; color: {MUTED}; }}
QPushButton#ghost {{ background: transparent; border: 1px solid {BORDER}; color: {TEXT}; }}
QPushButton#ghost:hover {{ background: {PANEL_2}; }}

QFrame#card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px; }}
QLabel#preview {{ background: #000; border: 1px solid {BORDER}; border-radius: 12px;
    color: {MUTED}; }}

QTextEdit {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 12px;
    padding: 8px; }}
QProgressBar {{ background: {PANEL_2}; border: none; border-radius: 6px; height: 6px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 6px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; }}
"""
