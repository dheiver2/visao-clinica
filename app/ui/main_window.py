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

    class CameraWorker(QThread):
        """Mantém a webcam ATIVA continuamente; a análise é uma janela de 12s
        disparada pelo usuário, que pode ser repetida sem reabrir a câmera."""
        frame = Signal(object)
        progress = Signal(str)
        analysis_ready = Signal(object)        # features
        failed = Signal(str)

        def __init__(self, duration, extractor):
            super().__init__()
            self.duration = duration
            self.extractor = extractor
            self._stop = False
            self._analyze = False

        def request_analysis(self):
            self._analyze = True

        def stop(self):
            self._stop = True

        def run(self):
            try:
                def _flag():
                    if self._analyze:
                        self._analyze = False   # consome o pedido (uma janela)
                        return True
                    return False

                self.extractor.stream(
                    on_frame=lambda rgb: self.frame.emit(rgb),
                    should_stop=lambda: self._stop,
                    analyze_flag=_flag,
                    duration_s=self.duration,
                    on_analysis=lambda feats: self.analysis_ready.emit(feats),
                    on_progress=lambda e, t: self.progress.emit(f"__cap__{e:.1f}/{t:.0f}"),
                )
            except Exception as e:  # noqa: BLE001
                self.failed.emit(str(e))

    return CameraWorker


def _condition_card(cond, research: bool):
    """Cria um card visual para uma condição do painel clínico."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

    color = theme.LEVEL_COLOR.get(cond.level, theme.MUTED)
    card = QFrame()
    card.setObjectName("card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(9)

    header = QHBoxLayout()
    dot = QLabel("●")
    dot.setStyleSheet(f"color:{color}; font-size:11px;")
    name = QLabel(cond.name)
    name.setStyleSheet("font-weight:700; font-size:13.5px; letter-spacing:-0.2px;")
    name.setWordWrap(True)
    badge = QLabel(cond.level.upper())
    badge.setAlignment(Qt.AlignCenter)
    badge.setStyleSheet(
        f"background: rgba(0,0,0,0.0); color:{color}; border:1px solid {color}; "
        f"border-radius:9px; padding:2px 11px; font-size:10px; font-weight:800; "
        f"letter-spacing:0.5px;")
    header.addWidget(dot, 0, Qt.AlignVCenter)
    header.addWidget(name, 1)
    header.addWidget(badge, 0, Qt.AlignTop)
    lay.addLayout(header)

    # barra de score
    bar_bg = QFrame()
    bar_bg.setFixedHeight(7)
    bar_bg.setStyleSheet(f"background:{theme.PANEL_2}; border-radius:4px;")
    bar = QFrame(bar_bg)
    pct = int(max(0.02, cond.score) * 100)
    bar.setStyleSheet(f"background:{color}; border-radius:4px;")
    bar.setGeometry(0, 0, 0, 7)
    bar_bg._bar, bar_bg._pct = bar, pct
    def _resize(ev, b=bar, bg=bar_bg, p=pct):
        b.setGeometry(0, 0, int(bg.width() * p / 100), 7)
    bar_bg.resizeEvent = _resize
    lay.addWidget(bar_bg)

    if research:
        from app.clinical.validation import accuracy_band
        acc = accuracy_band(cond.confidence)
        info = QLabel(f"score {cond.score:.2f} · acurácia {acc} ({cond.confidence:.0%}) — "
                      f"{cond.rationale}")
        info.setStyleSheet(f"color:{theme.MUTED}; font-size:11px;")
        info.setWordWrap(True)
        lay.addWidget(info)
    return card


def launch_gui(default_mode: str = "pesquisa") -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import (
        QApplication, QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
        QProgressBar, QPushButton, QScrollArea, QTextEdit, QVBoxLayout, QWidget,
    )

    from app.clinical.reasoning_engine import ClinicalReasoningEngine
    from app.vision.extractor import FeatureExtractor

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.QSS)
    Worker = _build_worker_class()

    win = QWidget()
    win.setObjectName("root")
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

    DURATION = 12.0
    mode_box = QComboBox()
    mode_box.addItems(["pesquisa", "triagem", "ocupacional (NR-01)"])
    mode_box.setCurrentText(default_mode)
    llm_chk = QCheckBox("Narrativa IA (lento)")
    llm_chk.setChecked(False)
    llm_chk.setToolTip("Gera um resumo do BitNet em background. O resultado clínico "
                       "já aparece instantaneamente sem isso.")
    run_btn = QPushButton(f"Analisar ({DURATION:.0f}s)")
    stop_btn = QPushButton("Encerrar câmera")
    stop_btn.setObjectName("ghost")
    stop_btn.setEnabled(False)

    from PySide6.QtWidgets import QLineEdit
    sector_edit = QLineEdit()
    sector_edit.setPlaceholderText("Setor (NR-01)")
    sector_edit.setMaximumWidth(140)
    sector_edit.setText("Geral")
    report_btn = QPushButton("Relatório do setor")
    report_btn.setObjectName("ghost")

    header = QHBoxLayout()
    header.addLayout(head_txt)
    header.addStretch()
    header.addWidget(QLabel("Modo:"))
    header.addWidget(mode_box)
    header.addWidget(sector_edit)
    header.addWidget(llm_chk)
    header.addWidget(run_btn)
    header.addWidget(report_btn)
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
        # `running` = análise de 12s em andamento. A câmera segue ativa nos dois casos.
        run_btn.setEnabled(not running)
        stop_btn.setEnabled(True)          # "Encerrar câmera" sempre disponível
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
        if msg.startswith("Gerando narrativa"):
            progress_bar.setRange(0, 0)  # indeterminado durante a narrativa do LLM

    def on_frame(rgb):
        pm = QPixmap.fromImage(_rgb_to_qimage(rgb)).scaled(
            preview.width(), preview.height(), Qt.KeepAspectRatio,
            Qt.SmoothTransformation)
        preview.setPixmap(pm)

    def on_panel(features, analysis):
        progress_bar.setRange(0, 100)
        progress_bar.setValue(100)
        research = mode_box.currentText() == "pesquisa"
        color = theme.LEVEL_COLOR.get(analysis.risk_level, theme.MUTED)
        overall.setText(f"Nível global: {analysis.risk_level.upper()}")
        overall.setStyleSheet(f"font-size:14px; font-weight:700; color:{color};")

        from app.clinical.validation import validate_session
        val = validate_session(features)

        clear_cards()
        # Só exibe indicadores com acurácia média/alta.
        displayable = analysis.displayable_conditions
        shown = displayable if research else [c for c in displayable
                                             if c.level in ("moderado", "alto")]
        if not val.ok or not analysis.displayable_conditions:
            msg = QLabel("Acurácia insuficiente para exibir indicadores confiáveis.\n• "
                         + "\n• ".join(val.messages or ["Refaça a captura."]))
            msg.setWordWrap(True)
            msg.setStyleSheet(f"color:{theme.LEVEL_COLOR['moderado']};")
            cards_layout.insertWidget(0, msg)
        elif not shown:
            empty = QLabel("Nenhum indicador relevante (modo triagem).")
            empty.setStyleSheet(f"color:{theme.MUTED};")
            cards_layout.insertWidget(0, empty)
        else:
            for i, cond in enumerate(shown):
                cards_layout.insertWidget(i, _condition_card(cond, research))

        q = getattr(features, "signal_quality", 1.0)
        qtxt = f"qualidade do sinal {q:.0%}"
        if q < 0.5:
            qtxt += " ⚠ (melhore iluminação/enquadramento)"
        status.setText(f"Concluído — resultado instantâneo · {qtxt}.")
        # Resultado já está pronto: libera a UI para nova captura imediatamente.
        if not llm_chk.isChecked():
            set_running(False)
        else:
            run_btn.setEnabled(False)  # narrativa ainda rodando em background

    def on_summary(text: str):
        if text:
            log.append("\n— Resumo do BitNet —\n" + text)
        status.setText("Concluído.")
        set_running(False)

    def on_failed(msg: str):
        progress_bar.setRange(0, 100)
        status.setText("Erro.")
        log.append(f"[ERRO] {msg}")
        set_running(False)

    from PySide6.QtCore import QThread, Signal

    class NarrativeWorker(QThread):
        done = Signal(str)
        def __init__(self, analysis, features):
            super().__init__(); self.analysis, self.features = analysis, features
        def run(self):
            try:
                engine.enrich_with_llm(self.analysis, self.features)
                self.done.emit(self.analysis.summary or "")
            except Exception as e:  # noqa: BLE001
                self.done.emit(f"[narrativa indisponível: {e}]")

    def on_analysis(features):
        if "ocupacional" in mode_box.currentText():
            on_occupational(features)
            set_running(False)
            return
        analysis = engine.screen(features)
        on_panel(features, analysis)
        # câmera continua ativa; libera novo "Analisar" imediatamente
        set_running(False)
        if llm_chk.isChecked():
            status.setText("Gerando narrativa do BitNet (câmera segue ativa)…")
            nw = NarrativeWorker(analysis, features)
            nw.done.connect(on_summary)
            state["narr"] = nw
            nw.start()

    def on_occupational(features):
        from app.clinical.nr01 import (action_plan, assess_psychosocial,
                                       overall_risk)
        from app.report.exporter import export_nr01_pdf
        ind = assess_psychosocial(features)
        risk = overall_risk(ind)
        plan = action_plan(ind)
        progress_bar.setRange(0, 100); progress_bar.setValue(100)
        color = theme.LEVEL_COLOR.get(risk, theme.MUTED)
        overall.setText(f"Risco psicossocial: {risk.upper()}")
        overall.setStyleSheet(f"font-size:14px; font-weight:700; color:{color};")
        clear_cards()
        from app.clinical.conditions import ConditionResult
        for i, p in enumerate(ind):
            card = _condition_card(ConditionResult(
                key=p.key, name=p.name, score=p.score, level=p.level,
                factors=p.factors, rationale="Sustentado por: " + "; ".join(p.factors)
                if p.factors else "Sem sinais relevantes.", confidence=1.0), True)
            cards_layout.insertWidget(i, card)
        try:
            import os
            os.makedirs("data", exist_ok=True)
            out = "data/plano_acao_nr01.pdf"
            export_nr01_pdf(ind, plan, out, risk_level=risk)
            # grava a sessão ANONIMIZADA (só níveis) na amostra do setor
            from app.clinical.nr01_aggregate import append_session
            setor = sector_edit.text().strip() or "Geral"
            append_session(setor, ind)
            log.append(f"Plano de ação NR-01 salvo em {out}")
            log.append(f"Sessão anonimizada adicionada à amostra do setor '{setor}'.")
        except Exception as e:  # noqa: BLE001
            log.append(f"[PDF indisponível: {e}]")
        status.setText("Triagem ocupacional concluída — plano de ação gerado.")

    def on_sector_report():
        from app.clinical.nr01 import action_plan
        from app.clinical.nr01_aggregate import aggregate
        from app.report.exporter import export_nr01_aggregate_pdf
        setor = sector_edit.text().strip() or "Geral"
        rep = aggregate(setor)
        if rep.n == 0:
            log.append(f"Nenhuma triagem registrada para o setor '{setor}'.")
            status.setText("Amostra do setor vazia.")
            return
        clear_cards()
        overall.setText(f"Setor {setor} · n={rep.n}")
        overall.setStyleSheet("font-size:14px; font-weight:700;")
        from app.clinical.conditions import ConditionResult
        for i, (fator, d) in enumerate(rep.by_factor.items()):
            lvl = "alto" if d["alto"] >= 34 else ("moderado" if d["moderado"] + d["alto"] >= 34 else "baixo")
            c = ConditionResult(key=fator, name=fator, score=(d["alto"] + 0.5 * d["moderado"]) / 100.0,
                                level=lvl,
                                rationale=f"alto {d['alto']}% · moderado {d['moderado']}% · baixo {d['baixo']}%",
                                confidence=1.0, factors=[])
            cards_layout.insertWidget(i, _condition_card(c, True))
        try:
            import os
            os.makedirs("data", exist_ok=True)
            out = f"data/relatorio_setor_{setor}.pdf"
            # plano com base no fator prioritário (usa o template de alto risco)
            from app.clinical.nr01 import assess_psychosocial
            from app.vision.features import BiomarkerFeatures
            plan = action_plan(assess_psychosocial(BiomarkerFeatures(
                frames=360, fps=30, microexpression_rate=18, blink_rate_per_min=46,
                hrv_sdnn_ms=12, rppg_quality=0.9))) if rep.overall_dist.get("alto", 0) > 0 else action_plan([])
            export_nr01_aggregate_pdf(rep, plan, out)
            log.append(f"Relatório agregado do setor salvo em {out} (n={rep.n}, anonimizado).")
        except Exception as e:  # noqa: BLE001
            log.append(f"[PDF indisponível: {e}]")
        status.setText(f"Relatório agregado do setor '{setor}' gerado.")

    def on_run():
        # Modo ocupacional exige consentimento informado (LGPD) a cada sessão.
        if "ocupacional" in mode_box.currentText() and not state.get("consent"):
            from PySide6.QtWidgets import QMessageBox
            box = QMessageBox(win)
            box.setWindowTitle("Consentimento — Uso Ocupacional (LGPD)")
            box.setIcon(QMessageBox.Information)
            box.setText("Triagem de bem-estar (NR-01)")
            box.setInformativeText(
                "Esta análise é VOLUNTÁRIA e de apoio ao bem-estar. NÃO é exame médico "
                "nem base para decisão disciplinar. Os dados são sensíveis (LGPD) e o uso "
                "recomendado é agregado/anonimizado.\n\nVocê autoriza esta captura?")
            box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            box.button(QMessageBox.Yes).setText("Autorizo")
            box.button(QMessageBox.No).setText("Não autorizo")
            if box.exec() != QMessageBox.Yes:
                status.setText("Captura cancelada (sem consentimento).")
                return
            state["consent"] = True
        log.clear(); clear_cards()
        set_running(True)
        status.setText("Analisando… olhe para a câmera (12s).")
        state["worker"].request_analysis()

    def on_stop():
        # encerra o streaming da câmera
        if state["worker"] is not None:
            state["worker"].stop()
            status.setText("Câmera encerrada.")
            run_btn.setEnabled(False); stop_btn.setEnabled(False)

    # inicia a câmera assim que a janela abre (preview contínuo)
    cam = Worker(DURATION, extractor)
    cam.frame.connect(on_frame)
    cam.progress.connect(on_progress)
    cam.analysis_ready.connect(on_analysis)
    cam.failed.connect(on_failed)
    state["worker"] = cam

    run_btn.clicked.connect(on_run)
    stop_btn.clicked.connect(on_stop)
    report_btn.clicked.connect(on_sector_report)

    def on_close(ev):
        cam.stop(); cam.wait(2000); ev.accept()
    win.closeEvent = on_close

    win.show()
    cam.start()
    stop_btn.setEnabled(True)   # câmera ativa
    status.setText("Câmera ativa — clique em Analisar para iniciar a triagem.")
    return app.exec()
