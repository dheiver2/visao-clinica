"""Interface desktop (PySide6) com os modos Pesquisa e Triagem.

O trabalho pesado (captura da webcam + carga do modelo + inferência) roda em uma
QThread dedicada para a UI nunca congelar. Um preview ao vivo da câmera é exibido
durante a captura.
"""

from __future__ import annotations

from app import DISCLAIMER


def _rgb_to_qimage(rgb):
    """Converte um frame RGB (numpy HxWx3) em QImage para exibição."""
    from PySide6.QtGui import QImage
    h, w, ch = rgb.shape
    return QImage(rgb.tobytes(), w, h, ch * w, QImage.Format_RGB888)


def _build_worker_class():
    """Cria a classe Worker (QThread) — feito tardiamente para não importar Qt cedo."""
    from PySide6.QtCore import QThread, Signal

    class Worker(QThread):
        progress = Signal(str)
        frame = Signal(object)          # numpy rgb
        finished_ok = Signal(object, object)  # (features, analysis)
        failed = Signal(str)

        def __init__(self, mode: str, duration: float, engine, extractor):
            super().__init__()
            self.mode = mode
            self.duration = duration
            self.engine = engine
            self.extractor = extractor
            self._stop = False

        def stop(self):
            self._stop = True

        def run(self):
            try:
                if not self.extractor.available():
                    raise RuntimeError(
                        "OpenCV/MediaPipe indisponíveis — verifique a instalação.")
                self.progress.emit("Capturando pela webcam… olhe para a câmera.")

                def _on_frame(rgb, elapsed, total):
                    self.frame.emit(rgb)
                    if int(elapsed) != int(elapsed - 0.05):
                        self.progress.emit(f"Capturando… {elapsed:0.0f}/{total:0.0f}s")

                features = self.extractor.capture(
                    duration_s=self.duration, on_frame=_on_frame,
                    should_stop=lambda: self._stop)

                self.progress.emit("Preparando IA local (modelo + bitnet.cpp)…")
                self.engine.load_model(progress=lambda m: self.progress.emit(f"  · {m}"))
                self.progress.emit(f"Backend: {self.engine.backend_name}")

                self.progress.emit("Analisando biomarcadores (pode demorar em CPU)…")
                analysis = self.engine.analyze_features(features)
                self.finished_ok.emit(features, analysis)
            except Exception as e:  # noqa: BLE001
                self.failed.emit(str(e))

    return Worker


def launch_gui(default_mode: str = "pesquisa") -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QHBoxLayout, QLabel, QProgressBar,
        QPushButton, QTextEdit, QVBoxLayout, QWidget,
    )

    from app.clinical.reasoning_engine import ClinicalReasoningEngine
    from app.vision.extractor import FeatureExtractor

    app = QApplication.instance() or QApplication([])
    Worker = _build_worker_class()

    win = QWidget()
    win.setWindowTitle("Visão Clínica — Triagem por IA Local (BitNet b1.58 2B4T)")
    win.resize(900, 720)

    mode_box = QComboBox()
    mode_box.addItems(["pesquisa", "triagem"])
    mode_box.setCurrentText(default_mode)
    run_btn = QPushButton("Iniciar captura (30s)")

    preview = QLabel("Pré-visualização da câmera aparecerá aqui")
    preview.setAlignment(Qt.AlignCenter)
    preview.setMinimumHeight(280)
    preview.setStyleSheet("background:#111; color:#888; border:1px solid #333;")

    progress_bar = QProgressBar()
    progress_bar.setRange(0, 0)  # indeterminado
    progress_bar.hide()

    out = QTextEdit()
    out.setReadOnly(True)

    disclaimer = QLabel(DISCLAIMER)
    disclaimer.setWordWrap(True)
    disclaimer.setStyleSheet("color:#a33; font-style:italic;")

    engine = ClinicalReasoningEngine()
    extractor = FeatureExtractor()
    state = {"worker": None}

    def set_running(running: bool):
        run_btn.setEnabled(not running)
        mode_box.setEnabled(not running)
        progress_bar.setVisible(running)

    def on_progress(msg: str):
        out.append(msg)

    def on_frame(rgb):
        img = _rgb_to_qimage(rgb)
        preview.setPixmap(QPixmap.fromImage(img).scaled(
            preview.width(), preview.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def on_finished(features, analysis):
        if mode_box.currentText() == "triagem":
            out.append(f"\n=== RESULTADO (Triagem) ===\nNível de risco: {analysis.risk_level}")
        else:
            out.append("\n=== Biomarcadores ===\n" + features.summary_text())
            out.append("\nHipóteses: " + "; ".join(analysis.hypotheses))
            out.append("Variáveis influentes: "
                       + "; ".join(analysis.influential_variables))
            try:
                out.append("\n=== Explicação ===\n" + engine.explain_decision())
            except Exception as e:  # noqa: BLE001
                out.append(f"[explicação indisponível: {e}]")
        set_running(False)

    def on_failed(msg: str):
        out.append(f"\n[ERRO] {msg}")
        set_running(False)

    def on_run():
        out.clear()
        set_running(True)
        w = Worker(mode_box.currentText(), 30.0, engine, extractor)
        w.progress.connect(on_progress)
        w.frame.connect(on_frame)
        w.finished_ok.connect(on_finished)
        w.failed.connect(on_failed)
        state["worker"] = w
        w.start()

    run_btn.clicked.connect(on_run)

    top = QHBoxLayout()
    top.addWidget(QLabel("Modo:"))
    top.addWidget(mode_box)
    top.addWidget(run_btn)
    top.addStretch()

    layout = QVBoxLayout(win)
    layout.addLayout(top)
    layout.addWidget(preview)
    layout.addWidget(progress_bar)
    layout.addWidget(out)
    layout.addWidget(disclaimer)

    win.show()
    return app.exec()
