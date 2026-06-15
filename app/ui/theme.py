"""Tema premium black e helpers visuais da interface."""

from __future__ import annotations

# Paleta premium black
BG = "#060708"
BG_2 = "#0a0c10"
PANEL = "#0f1216"
PANEL_2 = "#161a20"
BORDER = "#23272f"
BORDER_2 = "#2e333d"
TEXT = "#eef0f3"
MUTED = "#878d99"
ACCENT = "#5b8cff"
ACCENT_2 = "#7b6bff"

# Cores por nível de risco
LEVEL_COLOR = {
    "alto": "#ff5d6c",
    "moderado": "#ffb84d",
    "baixo": "#3ddc97",
    "indeterminado": "#6b7280",
}

QSS = f"""
* {{
    font-family: -apple-system, "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif;
    color: {TEXT};
    outline: none;
}}
QWidget {{ background: {BG}; }}
QWidget#root {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {BG_2}, stop:0.5 {BG}, stop:1 {BG});
}}

QLabel#title {{ font-size: 19px; font-weight: 800; letter-spacing: -0.4px; }}
QLabel#subtitle {{ color: {MUTED}; font-size: 12px; }}
QLabel#sectionTitle {{ color: {MUTED}; font-size: 10px; font-weight: 700;
    letter-spacing: 2px; }}

/* combo / inputs */
QComboBox, QLineEdit {{
    background: {PANEL_2}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 8px 12px; min-height: 18px; selection-background-color: {ACCENT};
}}
QComboBox:hover, QLineEdit:hover {{ border-color: {BORDER_2}; }}
QComboBox:focus, QLineEdit:focus {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: none; border-left: 4px solid transparent;
    border-right: 4px solid transparent; border-top: 5px solid {MUTED}; margin-right: 8px; }}
QComboBox QAbstractItemView {{ background: {PANEL_2}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 4px; selection-background-color: {ACCENT};
    outline: none; }}

/* botões */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {ACCENT}, stop:1 {ACCENT_2});
    color: white; border: none; border-radius: 10px;
    padding: 9px 20px; font-weight: 700; font-size: 13px;
}}
QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 #6e9bff, stop:1 #8d7eff); }}
QPushButton:pressed {{ padding-top: 10px; }}
QPushButton:disabled {{ background: {PANEL_2}; color: #565c66; }}
QPushButton#ghost {{ background: transparent; border: 1px solid {BORDER_2}; color: {TEXT}; }}
QPushButton#ghost:hover {{ background: {PANEL_2}; border-color: {ACCENT}; }}

/* checkbox */
QCheckBox {{ color: {MUTED}; font-size: 12px; spacing: 7px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 5px;
    border: 1px solid {BORDER_2}; background: {PANEL_2}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border-color: {ACCENT}; }}

/* cards e preview */
QFrame#card {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 14px; }}
QLabel#preview {{ background: #000; border: 1px solid {BORDER};
    border-radius: 16px; color: {MUTED}; }}

QTextEdit {{ background: {PANEL}; border: 1px solid {BORDER}; border-radius: 14px;
    padding: 10px; font-size: 12px; selection-background-color: {ACCENT}; }}

QProgressBar {{ background: {PANEL_2}; border: none; border-radius: 5px;
    max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ border-radius: 5px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACCENT}, stop:1 {ACCENT_2}); }}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER_2}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #3a4150; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QToolTip {{ background: {PANEL_2}; color: {TEXT}; border: 1px solid {BORDER_2};
    border-radius: 8px; padding: 6px 9px; }}
"""
