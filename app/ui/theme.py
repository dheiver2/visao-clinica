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

# Paleta de ALTO CONTRASTE (acessibilidade — eMAG/WCAG): preto puro, texto branco,
# bordas claras e foco visível reforçado.
_HC = {
    "BG": "#000000", "BG_2": "#000000", "PANEL": "#0a0a0a", "PANEL_2": "#161616",
    "BORDER": "#6a6a6a", "BORDER_2": "#8a8a8a", "TEXT": "#ffffff", "MUTED": "#e0e0e0",
    "ACCENT": "#4da3ff", "ACCENT_2": "#4da3ff",
}
_STD = {
    "BG": BG, "BG_2": BG_2, "PANEL": PANEL, "PANEL_2": PANEL_2, "BORDER": BORDER,
    "BORDER_2": BORDER_2, "TEXT": TEXT, "MUTED": MUTED, "ACCENT": ACCENT, "ACCENT_2": ACCENT_2,
}


def build_qss(scale: float = 1.0, high_contrast: bool = False) -> str:
    """Gera o QSS com escala de fonte e (opcional) alto contraste — acessibilidade.

    ``scale`` multiplica os tamanhos de fonte (0.85–1.6). ``high_contrast`` troca a
    paleta por uma de máximo contraste e reforça o realce de foco por teclado.
    """
    scale = max(0.85, min(1.6, float(scale)))
    p = _HC if high_contrast else _STD

    def fs(px: float) -> str:
        return f"{round(px * scale)}px"

    focus = (f"QComboBox:focus, QLineEdit:focus, QPushButton:focus, QCheckBox:focus, "
             f"QTableWidget:focus, QTextEdit:focus {{ border: 2px solid {p['ACCENT']}; }}"
             if high_contrast else
             f"QComboBox:focus, QLineEdit:focus {{ border-color: {p['ACCENT']}; }}")

    return f"""
* {{
    font-family: -apple-system, "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif;
    color: {p['TEXT']};
    outline: none;
}}
QWidget {{ background: {p['BG']}; font-size: {fs(13)}; }}
QWidget#root {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {p['BG_2']}, stop:0.5 {p['BG']}, stop:1 {p['BG']});
}}

QLabel#title {{ font-size: {fs(19)}; font-weight: 800; letter-spacing: -0.4px; }}
QLabel#subtitle {{ color: {p['MUTED']}; font-size: {fs(12)}; }}
QLabel#sectionTitle {{ color: {p['MUTED']}; font-size: {fs(10)}; font-weight: 700;
    letter-spacing: 2px; }}

/* combo / inputs */
QComboBox, QLineEdit {{
    background: {p['PANEL_2']}; border: 1px solid {p['BORDER']}; border-radius: 10px;
    padding: 8px 12px; min-height: 18px; selection-background-color: {p['ACCENT']};
}}
QComboBox:hover, QLineEdit:hover {{ border-color: {p['BORDER_2']}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: none; border-left: 4px solid transparent;
    border-right: 4px solid transparent; border-top: 5px solid {p['MUTED']}; margin-right: 8px; }}
QComboBox QAbstractItemView {{ background: {p['PANEL_2']}; border: 1px solid {p['BORDER']};
    border-radius: 10px; padding: 4px; selection-background-color: {p['ACCENT']};
    outline: none; }}

/* botões */
QPushButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {p['ACCENT']}, stop:1 {p['ACCENT_2']});
    color: white; border: none; border-radius: 10px;
    padding: 9px 20px; font-weight: 700; font-size: {fs(13)};
}}
QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
    stop:0 #6e9bff, stop:1 #8d7eff); }}
QPushButton:pressed {{ padding-top: 10px; }}
QPushButton:disabled {{ background: {p['PANEL_2']}; color: #565c66; }}
QPushButton#ghost {{ background: transparent; border: 1px solid {p['BORDER_2']}; color: {p['TEXT']}; }}
QPushButton#ghost:hover {{ background: {p['PANEL_2']}; border-color: {p['ACCENT']}; }}

/* checkbox */
QCheckBox {{ color: {p['MUTED']}; font-size: {fs(12)}; spacing: 7px; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 5px;
    border: 1px solid {p['BORDER_2']}; background: {p['PANEL_2']}; }}
QCheckBox::indicator:checked {{ background: {p['ACCENT']}; border-color: {p['ACCENT']}; }}

/* tabelas (auditoria/usuários/histórico) */
QTableWidget {{ background: {p['PANEL']}; border: 1px solid {p['BORDER']}; border-radius: 10px;
    gridline-color: {p['BORDER']}; font-size: {fs(12)}; }}
QHeaderView::section {{ background: {p['PANEL_2']}; color: {p['MUTED']}; border: none;
    padding: 6px; font-weight: 700; font-size: {fs(11)}; }}

/* cards e preview */
QFrame#card {{ background: {p['PANEL']}; border: 1px solid {p['BORDER']}; border-radius: 14px; }}
QLabel#preview {{ background: #000; border: 1px solid {p['BORDER']};
    border-radius: 16px; color: {p['MUTED']}; }}

QTextEdit {{ background: {p['PANEL']}; border: 1px solid {p['BORDER']}; border-radius: 14px;
    padding: 10px; font-size: {fs(12)}; selection-background-color: {p['ACCENT']}; }}

QProgressBar {{ background: {p['PANEL_2']}; border: none; border-radius: 5px;
    max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ border-radius: 5px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {p['ACCENT']}, stop:1 {p['ACCENT_2']}); }}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p['BORDER_2']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #3a4150; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

{focus}
QToolTip {{ background: {p['PANEL_2']}; color: {p['TEXT']}; border: 1px solid {p['BORDER_2']};
    border-radius: 8px; padding: 6px 9px; }}
"""


# Compatibilidade: QSS padrão (sem escala / contraste).
QSS = build_qss()
