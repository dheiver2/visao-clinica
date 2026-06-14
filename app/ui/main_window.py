"""Interface desktop (PySide6) — tema dark, preview ao vivo e painel clínico.

O trabalho pesado (captura + carga do modelo + inferência) roda numa QThread, e
o resultado é apresentado como cards por condição (saída clínica garantida por
doença), coloridos por nível de risco. Modos Pesquisa e Triagem.
"""

from __future__ import annotations

from app import DISCLAIMER
from app.ui import theme


def _rgb_to_qimage(rgb):
    from PySide6.QtGui import QImage
    h, w, ch = rgb.shape
    return QImage(rgb.tobytes(), w, h, ch * w, QImage.Format_RGB888)


def _build_worker_class():
    from PySide6.QtCore import QThread, Signal

    class Worker(QThread):
        progress = Signal(str)
        frame = Signal(object)
        finished_ok = Signal(object, object)   # (features, analysis)
        failed = Signal(str)

        def __init__(self, mode, duration, engine, extractor):
            super().__init__()
            self.mode, self.duration = mode, duration
            self.engine, self.extractor = engine, extractor
            self._stop = False

        def stop(self):
            self._stop = True

        def run(self):
            try:
                if not self.extractor.available():
                    raise RuntimeError("OpenCV/MediaPipe indisponíveis.")
                self.progress.emit("Capturando pela webcam — olhe para a câmera.")

                def _on_frame(rgb, elapsed, total):
                    self.frame.emit(rgb)
                    self.progress.emit(f"__cap__{elapsed:.1f}/{total:.0f}")

                features = self.extractor.capture(
                    duration_s=self.duration, on_frame=_on_frame,
                    should_stop=lambda: self._stop)

                self.progress.emit("Preparando IA local (BitNet)…")
                self.engine.load_model(progress=lambda m: self.progress.emit(f"· {m}"))
                self.progress.emit(f"Backend: {self.engine.backend_name}")
                self.progress.emit("Analisando biomarcadores…")
                analysis = self.engine.analyze_features(features)
                self.finished_ok.emit(features, analysis)
            except Exception as e:  # noqa: BLE001
                self.failed.emit(str(e))

    return Worker


def _condition_card(cond, research: bool):
    """Cria um card visual para uma condição do painel clínico."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

    color = theme.LEVEL_COLOR.get(cond.level, theme.MUTED)
    card = QFrame()
    card.setObjectName("card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(14, 12, 14, 12)
    lay.setSpacing(6)

    header = QHBoxLayout()
    name = QLabel(cond.name)
    name.setStyleSheet("font-weight:600; font-size:13px;")
    name.setWordWrap(True)
    badge = QLabel(cond.level.upper())
    badge.setAlignment(Qt.AlignCenter)
    badge.setStyleSheet(
        f"background:{color}; color:#0a0b0e; border-radius:8px; "
        f"padding:2px 10px; font-size:10px; font-weight:700;")
    header.addWidget(name, 1)
    header.addWidget(badge, 0, Qt.AlignTop)
    lay.addLayout(header)

    # barra de score
    bar_bg = QFrame()
    bar_bg.setFixedHeight(6)
    bar_bg.setStyleSheet(f"background:{theme.PANEL_2}; border-radius:3px;")
    bar = QFrame(bar_bg)
    pct = int(max(0.02, cond.score) * 100)
    bar.setStyleSheet(f"background:{color}; border-radius:3px;")
    bar.setGeometry(0, 0, 0, 6)
    bar_bg._bar, bar_bg._pct = bar, pct
    def _resize(ev, b=bar, bg=bar_bg, p=pct):
        b.setGeometry(0, 0, int(bg.width() * p / 100), 6)
    bar_bg.resizeEvent = _resize
    lay.addWidget(bar_bg)

    if research:
        info = QLabel(f"score {cond.score:.2f} — {cond.rationale}")
        info.setStyleSheet(f"color:{theme.MUTED}; font-size:11px;")
        info.setWordWrap(True)
        lay.addWidget(info)
    return card


def launch_gui(default_mode: str = "pesquisa") -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QFrame, QHBoxLayout, QLabel, QProgressBar,
        QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
    )

    from app.clinical.reasoning_engine import ClinicalReasoningEngine
    from app.vision.extractor import FeatureExtractor

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.QSS)
    Worker = _build_worker_class()

    win = QWidget()
    win.setWindowTitle("Visão Clínica — Triagem por IA Local (BitNet b1.58 2B4T)")
    win.resize(1180, 760)

    # ---- cabeçalho ----
    title = QLabel("Visão Clínica")
    title.setObjectName("title")
    subtitle = QLabel("Triagem por visão computacional + BitNet b1.58 2B4T (local)")
    subtitle.setObjectName("subtitle")
    head_txt = QVBoxLayout()
    head_txt.setSpacing(2)
    head_txt.addWidget(title)
    head_txt.addWidget(subtitle)

    mode_box = QComboBox()
    mode_box.addItems(["pesquisa", "triagem"])
    mode_box.setCurrentText(default_mode)
    run_btn = QPushButton("Iniciar captura")
    stop_btn = QPushButton("Parar")
    stop_btn.setObjectName("ghost")
    stop_btn.setEnabled(False)

    header = QHBoxLayout()
    header.addLayout(head_txt)
    header.addStretch()
    header.addWidget(QLabel("Modo:"))
    header.addWidget(mode_box)
    header.addWidget(run_btn)
    header.addWidget(stop_btn)

    # ---- coluna esquerda: câmera ----
    preview = QLabel("A pré-visualização da câmera aparecerá aqui")
    preview.setObjectName("preview")
    preview.setAlignment(Qt.AlignCenter)
    preview.setMinimumSize(560, 420)

    progress_bar = QProgressBar()
    progress_bar.setRange(0, 100)
    progress_bar.setValue(0)
    progress_bar.setTextVisible(False)

    status = QLabel("Pronto.")
    status.setObjectName("subtitle")

    left = QVBoxLayout()
    left.addWidget(preview, 1)
    left.addWidget(progress_bar)
    left.addWidget(status)

    # ---- coluna direita: painel clínico ----
    panel_title = QLabel("INDICADORES CLÍNICOS DE TRIAGEM")
    panel_title.setObjectName("sectionTitle")
    overall = QLabel("Nível global: —")
    overall.setStyleSheet("font-size:14px; font-weight:600;")

    cards_host = QWidget()
    cards_layout = QVBoxLayout(cards_host)
    cards_layout.setContentsMargins(0, 0, 6, 0)
    cards_layout.setSpacing(8)
    cards_layout.addStretch()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(cards_host)

    log = QTextEdit()
    log.setReadOnly(True)
    log.setMaximumHeight(150)
    log.setObjectName("card")

    right = QVBoxLayout()
    right.addWidget(panel_title)
    right.addWidget(overall)
    right.addWidget(scroll, 1)
    log_title = QLabel("LOG")
    log_title.setObjectName("sectionTitle")
    right.addWidget(log_title)
    right.addWidget(log)

    body = QHBoxLayout()
    body.addLayout(left, 5)
    body.addLayout(right, 4)

    disclaimer = QLabel(DISCLAIMER)
    disclaimer.setWordWrap(True)
    disclaimer.setStyleSheet("color:#ff8a8a; font-style:italic; font-size:11px;")

    root = QVBoxLayout(win)
    root.setContentsMargins(18, 16, 18, 14)
    root.setSpacing(12)
    root.addLayout(header)
    root.addLayout(body, 1)
    root.addWidget(disclaimer)

    engine = ClinicalReasoningEngine()
    extractor = FeatureExtractor()
    state = {"worker": None}

    def clear_cards():
        while cards_layout.count() > 1:
            item = cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def set_running(running: bool):
        run_btn.setEnabled(not running)
        stop_btn.setEnabled(running)
        mode_box.setEnabled(not running)
        if running:
            progress_bar.setValue(0)

    def on_progress(msg: str):
        if msg.startswith("__cap__"):
            try:
                cur, tot = msg[7:].split("/")
                progress_bar.setValue(int(float(cur) / float(tot) * 100))
                status.setText(f"Capturando… {float(cur):.0f}/{float(tot):.0f}s")
            except Exception:  # noqa: BLE001
                pass
            return
        status.setText(msg)
        log.append(msg)
        if msg.startswith("Analisando"):
            progress_bar.setRange(0, 0)  # indeterminado durante inferência

    def on_frame(rgb):
        pm = QPixmap.fromImage(_rgb_to_qimage(rgb)).scaled(
            preview.width(), preview.height(), Qt.KeepAspectRatio,
            Qt.SmoothTransformation)
        preview.setPixmap(pm)

    def on_finished(features, analysis):
        progress_bar.setRange(0, 100)
        progress_bar.setValue(100)
        research = mode_box.currentText() == "pesquisa"
        color = theme.LEVEL_COLOR.get(analysis.risk_level, theme.MUTED)
        overall.setText(f"Nível global: {analysis.risk_level.upper()}")
        overall.setStyleSheet(f"font-size:14px; font-weight:700; color:{color};")

        clear_cards()
        shown = analysis.conditions if research else analysis.top_conditions
        if not shown:
            empty = QLabel("Nenhum indicador relevante (modo triagem).")
            empty.setStyleSheet(f"color:{theme.MUTED};")
            cards_layout.insertWidget(0, empty)
        for i, cond in enumerate(shown):
            cards_layout.insertWidget(i, _condition_card(cond, research))

        status.setText("Concluído.")
        if research and analysis.summary:
            log.append("\n— Resumo do BitNet —\n" + analysis.summary)
        set_running(False)

    def on_failed(msg: str):
        progress_bar.setRange(0, 100)
        status.setText("Erro.")
        log.append(f"[ERRO] {msg}")
        set_running(False)

    def on_run():
        log.clear()
        clear_cards()
        set_running(True)
        w = Worker(mode_box.currentText(), 30.0, engine, extractor)
        w.progress.connect(on_progress)
        w.frame.connect(on_frame)
        w.finished_ok.connect(on_finished)
        w.failed.connect(on_failed)
        state["worker"] = w
        w.start()

    def on_stop():
        if state["worker"] is not None:
            state["worker"].stop()
            status.setText("Interrompendo…")

    run_btn.clicked.connect(on_run)
    stop_btn.clicked.connect(on_stop)

    win.show()
    return app.exec()
