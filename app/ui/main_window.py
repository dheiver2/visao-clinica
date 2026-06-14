"""Interface desktop (PySide6) com os modos Pesquisa e Triagem."""

from __future__ import annotations

from app import DISCLAIMER


def launch_gui(default_mode: str = "pesquisa") -> int:
    from PySide6.QtWidgets import (
        QApplication, QComboBox, QHBoxLayout, QLabel, QPushButton,
        QTextEdit, QVBoxLayout, QWidget,
    )

    from app.clinical.reasoning_engine import ClinicalReasoningEngine
    from app.vision.extractor import FeatureExtractor

    app = QApplication.instance() or QApplication([])
    win = QWidget()
    win.setWindowTitle("Visão Clínica — Triagem por IA Local (BitNet b1.58 2B4T)")
    win.resize(820, 620)

    mode_box = QComboBox()
    mode_box.addItems(["pesquisa", "triagem"])
    mode_box.setCurrentText(default_mode)
    run_btn = QPushButton("Iniciar captura (30s)")
    out = QTextEdit()
    out.setReadOnly(True)
    disclaimer = QLabel(DISCLAIMER)
    disclaimer.setWordWrap(True)
    disclaimer.setStyleSheet("color:#a33; font-style:italic;")

    engine = ClinicalReasoningEngine()
    extractor = FeatureExtractor()

    def on_run():
        out.append("Capturando pela webcam...")
        app.processEvents()
        try:
            features = extractor.capture(duration_s=30.0)
            engine.load_model()
            out.append(f"LLM backend: {engine.backend_name}")
            analysis = engine.analyze_features(features)
            if mode_box.currentText() == "triagem":
                out.append(f"\nNível de risco: {analysis.risk_level}")
            else:
                out.append("\n--- Biomarcadores ---\n" + features.summary_text())
                out.append("\nHipóteses: " + "; ".join(analysis.hypotheses))
                out.append("Variáveis influentes: "
                           + "; ".join(analysis.influential_variables))
                out.append("\n--- Explicação ---\n" + engine.explain_decision())
        except Exception as e:  # noqa: BLE001
            out.append(f"[Erro] {e}")

    run_btn.clicked.connect(on_run)

    top = QHBoxLayout()
    top.addWidget(QLabel("Modo:"))
    top.addWidget(mode_box)
    top.addWidget(run_btn)
    top.addStretch()

    layout = QVBoxLayout(win)
    layout.addLayout(top)
    layout.addWidget(out)
    layout.addWidget(disclaimer)

    win.show()
    return app.exec()
