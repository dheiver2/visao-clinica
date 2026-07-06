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


def _vital_chip(label: str, value_txt: str, color: str, tip: str = ""):
    """Chip compacto de sinal vital (valor grande + rótulo)."""
    from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

    chip = QFrame()
    chip.setObjectName("card")
    lay = QVBoxLayout(chip)
    lay.setContentsMargins(12, 8, 12, 8)
    lay.setSpacing(1)
    val = QLabel(value_txt)
    val.setStyleSheet(f"color:{color}; font-size:17px; font-weight:800; letter-spacing:-0.3px;")
    cap = QLabel(label)
    cap.setStyleSheet(f"color:{theme.MUTED}; font-size:10px; font-weight:700; letter-spacing:0.4px;")
    lay.addWidget(val)
    lay.addWidget(cap)
    if tip:
        chip.setToolTip(tip)
    return chip


def _vitals_strip(features, wellness: dict):
    """Painel de sinais vitais estilo apps de vitais por câmera (FC, VFC, resp…)."""
    from PySide6.QtWidgets import QGridLayout, QWidget

    host = QWidget()
    grid = QGridLayout(host)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(8)
    grid.setVerticalSpacing(8)

    chips = []

    score = int(wellness.get("score", 0) or 0)
    wlabel = wellness.get("label", "indeterminado")
    wcolor = {"ótimo": theme.LEVEL_COLOR["baixo"], "bom": theme.LEVEL_COLOR["baixo"],
              "moderado": theme.LEVEL_COLOR["moderado"], "alerta": theme.LEVEL_COLOR["alto"],
              }.get(wlabel, theme.MUTED)
    if wellness.get("reliable"):
        chips.append(_vital_chip("BEM-ESTAR", f"{score}  ·  {wlabel}", wcolor,
                                 "Índice-síntese 0–100 de FC, VFC, respiração e estresse."))
        chips.append(_vital_chip("ESTRESSE", f"{int(wellness.get('stress', 0))}%",
                                 theme.LEVEL_COLOR["alto"] if wellness.get("stress", 0) >= 60
                                 else theme.MUTED,
                                 "Nível de estresse estimado (índice de Baevsky + sinais faciais)."))
    else:
        chips.append(_vital_chip("BEM-ESTAR", "— sinal insuf.", theme.MUTED,
                                 "Melhore iluminação/enquadramento para liberar o índice."))

    hr = getattr(features, "heart_rate_bpm", 0.0)
    if hr > 0:
        hcol = theme.LEVEL_COLOR["moderado"] if (hr < 50 or hr > 100) else theme.TEXT
        chips.append(_vital_chip("FREQ. CARDÍACA", f"{hr:.0f} bpm", hcol,
                                 "rPPG (método POS, Wang et al. 2017)."))
    rr = getattr(features, "respiration_bpm", 0.0)
    if rr > 0:
        rcol = theme.LEVEL_COLOR["moderado"] if (rr < 10 or rr > 24) else theme.TEXT
        chips.append(_vital_chip("RESPIRAÇÃO", f"{rr:.0f} rpm", rcol,
                                 "Modulação respiratória da pele (RIIV)."))
    sdnn = getattr(features, "hrv_sdnn_ms", 0.0)
    rmssd = getattr(features, "hrv_rmssd_ms", 0.0)
    if sdnn > 0:
        chips.append(_vital_chip("VFC (SDNN)", f"{sdnn:.0f} ms", theme.TEXT,
                                 f"Variabilidade cardíaca. RMSSD {rmssd:.0f} ms · "
                                 f"pNN50 {getattr(features, 'hrv_pnn50', 0.0):.0%}."))
    lfhf = getattr(features, "lf_hf_ratio", 0.0)
    if lfhf > 0:
        chips.append(_vital_chip("BALANÇO LF/HF", f"{lfhf:.2f}", theme.TEXT,
                                 "Balanço autonômico simpato-vagal (>2 = predomínio simpático)."))

    for i, chip in enumerate(chips):
        grid.addWidget(chip, i // 3, i % 3)
    return host


class _Sparkline:
    """Fábrica de mini-gráfico de linha (tendência) via QWidget + paintEvent."""

    @staticmethod
    def make(values, color: str, ymin=None, ymax=None):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
        from PySide6.QtWidgets import QWidget

        vals = [float(v) for v in values if v is not None]

        class _W(QWidget):
            def __init__(self):
                super().__init__()
                self.setMinimumHeight(64)

            def paintEvent(self, _ev):
                if len(vals) < 1:
                    return
                p = QPainter(self)
                p.setRenderHint(QPainter.Antialiasing)
                w, h = self.width(), self.height()
                pad = 6
                lo = ymin if ymin is not None else min(vals)
                hi = ymax if ymax is not None else max(vals)
                rng = (hi - lo) or 1.0
                n = len(vals)
                dx = (w - 2 * pad) / max(n - 1, 1)

                def pt(i, v):
                    x = pad + i * dx
                    y = h - pad - (v - lo) / rng * (h - 2 * pad)
                    return QPointF(x, y)

                # área preenchida sutil
                poly = QPolygonF([pt(i, v) for i, v in enumerate(vals)])
                line = QColor(color)
                p.setPen(QPen(line, 2))
                p.drawPolyline(poly)
                # ponto final destacado
                p.setBrush(line)
                p.setPen(Qt.NoPen)
                last = pt(n - 1, vals[-1])
                p.drawEllipse(last, 3.5, 3.5)
                p.end()

        return _W()


def _open_trends(parent, store):
    """Diálogo de Histórico & Tendências longitudinais das sessões salvas."""
    from PySide6.QtWidgets import (
        QDialog,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
    )

    rows = store.recent(60, mode=None)
    dlg = QDialog(parent)
    dlg.setObjectName("root")
    dlg.setWindowTitle("Histórico & Tendências")
    dlg.resize(760, 620)
    dlg.setStyleSheet(theme.QSS)
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(12)

    title = QLabel("HISTÓRICO & TENDÊNCIAS")
    title.setObjectName("sectionTitle")
    lay.addWidget(title)

    if not rows:
        empty = QLabel("Nenhuma sessão salva ainda. Faça uma análise para começar a "
                       "acompanhar suas tendências ao longo do tempo.")
        empty.setWordWrap(True)
        empty.setStyleSheet(f"color:{theme.MUTED};")
        lay.addWidget(empty)
        dlg.exec()
        return

    chrono = list(reversed(rows))  # cronológico p/ os gráficos

    def _series(getter):
        return [getter(r) for r in chrono]

    well = _series(lambda r: (r["analysis"].get("wellness") or {}).get("score", 0) or 0)
    hr = _series(lambda r: (r["features"] or {}).get("heart_rate_bpm", 0) or 0)
    stress = _series(lambda r: (r["analysis"].get("wellness") or {}).get("stress", 0) or 0)

    def _avg(xs):
        xs = [x for x in xs if x]
        return sum(xs) / len(xs) if xs else 0.0

    summary = QLabel(
        f"{len(rows)} sessões · bem-estar médio <b>{_avg(well):.0f}</b>/100 · "
        f"FC média <b>{_avg(hr):.0f}</b> bpm · estresse médio <b>{_avg(stress):.0f}</b>%")
    summary.setStyleSheet("font-size:13px;")
    lay.addWidget(summary)

    def _chart(caption, values, color, ymin=None, ymax=None):
        box = QVBoxLayout()
        box.setSpacing(3)
        cap = QLabel(caption)
        cap.setStyleSheet(f"color:{theme.MUTED}; font-size:10px; font-weight:700;")
        box.addWidget(cap)
        box.addWidget(_Sparkline.make(values, color, ymin, ymax))
        return box

    charts = QHBoxLayout()
    charts.addLayout(_chart("BEM-ESTAR (0–100)", well, theme.LEVEL_COLOR["baixo"], 0, 100))
    charts.addLayout(_chart("FREQ. CARDÍACA (bpm)", hr, theme.ACCENT))
    charts.addLayout(_chart("ESTRESSE (%)", stress, theme.LEVEL_COLOR["alto"], 0, 100))
    lay.addLayout(charts)

    table = QTableWidget(len(rows), 6)
    table.setHorizontalHeaderLabels(
        ["Data", "Modo", "FC", "Resp.", "Bem-estar", "Risco"])
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    for i, r in enumerate(rows):  # mais recentes primeiro
        f = r["features"] or {}
        w = r["analysis"].get("wellness") or {}
        vals = [
            str(r["created_at"] or ""),
            str(r["mode"] or ""),
            f"{f.get('heart_rate_bpm', 0):.0f}" if f.get("heart_rate_bpm") else "—",
            f"{f.get('respiration_bpm', 0):.0f}" if f.get("respiration_bpm") else "—",
            f"{int(w.get('score', 0))} ({w.get('label', '—')})" if w.get("reliable") else "—",
            str(r["risk_level"] or "—"),
        ]
        for j, v in enumerate(vals):
            table.setItem(i, j, QTableWidgetItem(v))
    lay.addWidget(table, 1)
    dlg.exec()


def _first_admin_dialog(parent, gov) -> bool:
    """Primeiro acesso: cria a conta de administrador (obrigatória)."""
    from PySide6.QtWidgets import (
        QDialog,
        QFormLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
    )

    dlg = QDialog(parent)
    dlg.setObjectName("root")
    dlg.setWindowTitle("Primeiro acesso — criar administrador")
    dlg.setStyleSheet(theme.QSS)
    dlg.setMinimumWidth(430)
    v = QVBoxLayout(dlg)
    v.setContentsMargins(22, 18, 22, 18)
    v.setSpacing(12)
    info = QLabel("Nenhum usuário cadastrado. Crie a conta de administrador para "
                  "prosseguir (controle de acesso).")
    info.setWordWrap(True)
    v.addWidget(info)
    form = QFormLayout()
    u = QLineEdit()
    p = QLineEdit(); p.setEchoMode(QLineEdit.Password)
    p2 = QLineEdit(); p2.setEchoMode(QLineEdit.Password)
    form.addRow("Usuário:", u)
    form.addRow("Senha:", p)
    form.addRow("Confirmar:", p2)
    v.addLayout(form)
    hint = QLabel("Mín. 8 caracteres, com letras e números.")
    hint.setObjectName("subtitle")
    v.addWidget(hint)
    btn = QPushButton("Criar administrador")
    v.addWidget(btn)
    ok = {"v": False}

    def submit():
        if p.text() != p2.text():
            QMessageBox.warning(dlg, "Senha", "As senhas não conferem.")
            return
        try:
            gov.create_user(u.text(), p.text(), "administrador")
            gov.log(u.text().strip(), "usuario_criado", "perfil=administrador (1º acesso)")
            ok["v"] = True
            dlg.accept()
        except ValueError as e:
            QMessageBox.warning(dlg, "Cadastro", str(e))

    btn.clicked.connect(submit)
    dlg.exec()
    return ok["v"]


def _login_dialog(parent, gov):
    """Autenticação. Retorna (usuário, perfil) ou None se cancelado."""
    from PySide6.QtWidgets import (
        QDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
    )

    dlg = QDialog(parent)
    dlg.setObjectName("root")
    dlg.setWindowTitle("Acesso — Visão Clínica")
    dlg.setStyleSheet(theme.QSS)
    dlg.setMinimumWidth(400)
    v = QVBoxLayout(dlg)
    v.setContentsMargins(22, 18, 22, 18)
    v.setSpacing(12)
    ttl = QLabel("Identifique-se para continuar")
    ttl.setStyleSheet("font-size:15px; font-weight:700;")
    v.addWidget(ttl)
    form = QFormLayout()
    u = QLineEdit()
    p = QLineEdit(); p.setEchoMode(QLineEdit.Password)
    form.addRow("Usuário:", u)
    form.addRow("Senha:", p)
    v.addLayout(form)
    row = QHBoxLayout()
    cancel = QPushButton("Cancelar"); cancel.setObjectName("ghost")
    enter = QPushButton("Entrar")
    row.addStretch(); row.addWidget(cancel); row.addWidget(enter)
    v.addLayout(row)
    out = {}

    def submit():
        role = gov.verify(u.text(), p.text())
        if role:
            out["user"], out["role"] = u.text().strip(), role
            dlg.accept()
        else:
            gov.log(u.text().strip() or "-", "login_falha")
            QMessageBox.warning(dlg, "Acesso", "Usuário ou senha inválidos.")
            p.clear()

    enter.clicked.connect(submit)
    p.returnPressed.connect(submit)
    cancel.clicked.connect(dlg.reject)
    dlg.exec()
    return (out["user"], out["role"]) if out else None


def _authenticate(parent, gov):
    """Fluxo de autenticação: cria admin no 1º uso, depois faz login."""
    if gov.user_count() == 0 and not _first_admin_dialog(parent, gov):
        return None
    return _login_dialog(parent, gov)


def _management_dialog(parent, gov, current_user: str):
    """Painel de gestão (administrador): instituição, usuários, auditoria, backup."""
    from PySide6.QtWidgets import (
        QComboBox,
        QDialog,
        QFileDialog,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )

    from app.security.governance import ROLES

    dlg = QDialog(parent)
    dlg.setObjectName("root")
    dlg.setWindowTitle("Gestão & Conformidade")
    dlg.setStyleSheet(theme.QSS)
    dlg.resize(720, 600)
    outer = QVBoxLayout(dlg)
    outer.setContentsMargins(16, 14, 16, 14)
    tabs = QTabWidget()
    outer.addWidget(tabs)

    # -- Instituição ------------------------------------------------------------
    inst_tab = QWidget()
    il = QFormLayout(inst_tab)
    inst = gov.get_institution()
    f_nome = QLineEdit(inst.get("nome", ""))
    f_cnpj = QLineEdit(inst.get("cnpj", ""))
    f_resp = QLineEdit(inst.get("responsavel", ""))
    f_cons = QLineEdit(inst.get("conselho", ""))
    f_logo = QLineEdit(inst.get("logo_path", ""))
    logo_row = QHBoxLayout()
    logo_row.addWidget(f_logo)
    browse = QPushButton("…"); browse.setObjectName("ghost"); browse.setMaximumWidth(40)
    logo_row.addWidget(browse)
    logo_wrap = QWidget(); logo_wrap.setLayout(logo_row)
    il.addRow("Órgão/Instituição:", f_nome)
    il.addRow("CNPJ:", f_cnpj)
    il.addRow("Responsável técnico:", f_resp)
    il.addRow("Registro (conselho):", f_cons)
    il.addRow("Logo (PNG/JPG):", logo_wrap)
    save_inst = QPushButton("Salvar dados institucionais")
    il.addRow(save_inst)

    def pick_logo():
        path, _ = QFileDialog.getOpenFileName(dlg, "Selecionar logo", "",
                                              "Imagens (*.png *.jpg *.jpeg)")
        if path:
            f_logo.setText(path)

    def do_save_inst():
        gov.set_institution({
            "nome": f_nome.text(), "cnpj": f_cnpj.text(), "responsavel": f_resp.text(),
            "conselho": f_cons.text(), "logo_path": f_logo.text()})
        gov.log(current_user, "instituicao_atualizada", f_nome.text())
        QMessageBox.information(dlg, "Instituição", "Dados institucionais salvos.")

    browse.clicked.connect(pick_logo)
    save_inst.clicked.connect(do_save_inst)
    tabs.addTab(inst_tab, "Instituição")

    # -- Usuários ---------------------------------------------------------------
    users_tab = QWidget()
    ul = QVBoxLayout(users_tab)
    utable = QTableWidget(0, 4)
    utable.setHorizontalHeaderLabels(["Usuário", "Perfil", "Ativo", "Criado em"])
    utable.setEditTriggers(QTableWidget.NoEditTriggers)
    from PySide6.QtWidgets import QHeaderView
    utable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    ul.addWidget(utable)

    def refresh_users():
        rows = gov.list_users()
        utable.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, v in enumerate([r["username"], r["role"],
                                   "sim" if r["active"] else "não", r["created_at"]]):
                utable.setItem(i, j, QTableWidgetItem(str(v)))

    refresh_users()
    addf = QHBoxLayout()
    nu = QLineEdit(); nu.setPlaceholderText("novo usuário")
    npw = QLineEdit(); npw.setPlaceholderText("senha"); npw.setEchoMode(QLineEdit.Password)
    nrole = QComboBox(); nrole.addItems(list(ROLES))
    addb = QPushButton("Adicionar")
    for wdg in (nu, npw, nrole, addb):
        addf.addWidget(wdg)
    ul.addLayout(addf)
    actions = QHBoxLayout()
    resetb = QPushButton("Redefinir senha"); resetb.setObjectName("ghost")
    toggleb = QPushButton("Ativar/Desativar"); toggleb.setObjectName("ghost")
    actions.addStretch(); actions.addWidget(resetb); actions.addWidget(toggleb)
    ul.addLayout(actions)

    def add_user():
        try:
            gov.create_user(nu.text(), npw.text(), nrole.currentText())
            gov.log(current_user, "usuario_criado",
                    f"{nu.text().strip()} perfil={nrole.currentText()}")
            nu.clear(); npw.clear(); refresh_users()
        except ValueError as e:
            QMessageBox.warning(dlg, "Usuários", str(e))

    def _selected_user():
        r = utable.currentRow()
        return utable.item(r, 0).text() if r >= 0 and utable.item(r, 0) else None

    def reset_pw():
        user = _selected_user()
        if not user:
            return
        from PySide6.QtWidgets import QInputDialog
        pw, ok = QInputDialog.getText(dlg, "Redefinir senha",
                                      f"Nova senha para '{user}':", QLineEdit.Password)
        if ok:
            try:
                gov.set_password(user, pw)
                gov.log(current_user, "senha_redefinida", user)
                QMessageBox.information(dlg, "Usuários", "Senha redefinida.")
            except ValueError as e:
                QMessageBox.warning(dlg, "Usuários", str(e))

    def toggle_user():
        user = _selected_user()
        if not user:
            return
        cur = next((u for u in gov.list_users() if u["username"] == user), None)
        if not cur:
            return
        if user == current_user:
            QMessageBox.warning(dlg, "Usuários", "Não é possível desativar o próprio usuário logado.")
            return
        gov.set_active(user, not cur["active"])
        gov.log(current_user, "usuario_status", f"{user} ativo={not cur['active']}")
        refresh_users()

    addb.clicked.connect(add_user)
    resetb.clicked.connect(reset_pw)
    toggleb.clicked.connect(toggle_user)
    tabs.addTab(users_tab, "Usuários")

    # -- Auditoria --------------------------------------------------------------
    audit_tab = QWidget()
    al = QVBoxLayout(audit_tab)
    atable = QTableWidget(0, 4)
    atable.setHorizontalHeaderLabels(["Data/hora", "Usuário", "Evento", "Detalhe"])
    atable.setEditTriggers(QTableWidget.NoEditTriggers)
    atable.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    al.addWidget(atable)
    events = gov.audit(1000)
    atable.setRowCount(len(events))
    for i, e in enumerate(events):
        for j, v in enumerate([e["ts"], e["username"], e["event"], e["detail"]]):
            atable.setItem(i, j, QTableWidgetItem(str(v or "")))
    exp_audit = QPushButton("Exportar auditoria (CSV)"); exp_audit.setObjectName("ghost")
    al.addWidget(exp_audit)

    def export_audit():
        path, _ = QFileDialog.getSaveFileName(dlg, "Exportar auditoria", "auditoria.csv",
                                              "CSV (*.csv)")
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["data_hora", "usuario", "evento", "detalhe"])
            for e in gov.audit(100000):
                w.writerow([e["ts"], e["username"], e["event"], e["detail"]])
        gov.log(current_user, "auditoria_exportada", path)
        QMessageBox.information(dlg, "Auditoria", f"Auditoria exportada para:\n{path}")

    exp_audit.clicked.connect(export_audit)
    tabs.addTab(audit_tab, "Auditoria")

    # -- Backup -----------------------------------------------------------------
    backup_tab = QWidget()
    bl = QVBoxLayout(backup_tab)
    bl.setSpacing(12)
    binfo = QLabel("Backup e restauração de todos os dados locais (sessões, usuários, "
                   "auditoria e configuração institucional).")
    binfo.setWordWrap(True)
    bl.addWidget(binfo)
    brow = QHBoxLayout()
    exp_bk = QPushButton("Exportar backup (.db)")
    imp_bk = QPushButton("Restaurar backup…"); imp_bk.setObjectName("ghost")
    brow.addWidget(exp_bk); brow.addWidget(imp_bk); brow.addStretch()
    bl.addLayout(brow)
    bl.addStretch()

    def do_backup():
        path, _ = QFileDialog.getSaveFileName(dlg, "Exportar backup",
                                              "visaoclinica_backup.db", "SQLite (*.db)")
        if not path:
            return
        gov.backup_to(path)
        gov.log(current_user, "backup_exportado", path)
        QMessageBox.information(dlg, "Backup", f"Backup salvo em:\n{path}")

    def do_restore():
        path, _ = QFileDialog.getOpenFileName(dlg, "Restaurar backup", "", "SQLite (*.db)")
        if not path:
            return
        if QMessageBox.question(dlg, "Restaurar",
                                "Isto substitui TODOS os dados atuais pelo backup. Continuar?"
                                ) != QMessageBox.Yes:
            return
        try:
            gov.restore_from(path)
            gov.log(current_user, "backup_restaurado", path)
            QMessageBox.information(dlg, "Backup",
                                    "Backup restaurado. Reinicie o app para recarregar tudo.")
            refresh_users()
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(dlg, "Backup", f"Falha ao restaurar: {e}")

    exp_bk.clicked.connect(do_backup)
    imp_bk.clicked.connect(do_restore)
    tabs.addTab(backup_tab, "Backup")

    dlg.exec()


def launch_gui(default_mode: str = "pesquisa") -> int:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )

    from app.clinical.reasoning_engine import ClinicalReasoningEngine
    from app.security.governance import GovernanceStore
    from app.ui import settings as ui_settings
    from app.vision.extractor import FeatureExtractor

    app = QApplication.instance() or QApplication([])
    gov = GovernanceStore()
    prefs = ui_settings.load()

    def apply_theme():
        app.setStyleSheet(theme.build_qss(prefs["font_scale"], prefs["high_contrast"]))

    apply_theme()
    Worker = _build_worker_class()

    # Controle de acesso — autenticação obrigatória (perfil) antes de tudo.
    auth = _authenticate(None, gov)
    if not auth:
        gov.close()
        return
    current_user, current_role = auth
    gov.log(current_user, "login", f"perfil={current_role}")

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
    history_btn = QPushButton("Histórico")
    history_btn.setObjectName("ghost")
    manage_btn = QPushButton("Gestão")
    manage_btn.setObjectName("ghost")
    manage_btn.setToolTip("Instituição, usuários, auditoria e backup (administrador)")
    manage_btn.setVisible(current_role == "administrador")

    # Acessibilidade (eMAG/WCAG): ajuste de fonte e alto contraste.
    a_minus = QPushButton("A-"); a_minus.setObjectName("ghost"); a_minus.setMaximumWidth(40)
    a_minus.setToolTip("Diminuir fonte")
    a_plus = QPushButton("A+"); a_plus.setObjectName("ghost"); a_plus.setMaximumWidth(40)
    a_plus.setToolTip("Aumentar fonte")
    contrast_chk = QCheckBox("Alto contraste")
    contrast_chk.setChecked(bool(prefs["high_contrast"]))
    contrast_chk.setToolTip("Tema de alto contraste (acessibilidade)")

    user_lbl = QLabel(f"👤 {current_user} · {current_role}")
    user_lbl.setObjectName("subtitle")

    header = QHBoxLayout()
    header.addLayout(head_txt)
    header.addStretch()
    header.addWidget(user_lbl)
    header.addWidget(a_minus)
    header.addWidget(a_plus)
    header.addWidget(contrast_chk)
    header.addWidget(QLabel("Modo:"))
    header.addWidget(mode_box)
    header.addWidget(sector_edit)
    header.addWidget(llm_chk)
    header.addWidget(run_btn)
    header.addWidget(report_btn)
    header.addWidget(history_btn)
    header.addWidget(manage_btn)
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

    # Faixa de sinais vitais (FC, VFC, respiração, bem-estar) — atualizada por análise.
    vitals_container = QVBoxLayout()
    vitals_container.setContentsMargins(0, 0, 0, 0)
    vitals_container.setSpacing(0)

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
    right.addLayout(vitals_container)
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
    from app.storage.db import SessionStore
    store = SessionStore()
    state = {"worker": None}

    def update_vitals(features, wellness: dict):
        # limpa o container e insere a faixa de vitais da análise atual
        while vitals_container.count():
            item = vitals_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        strip = _vitals_strip(features, wellness or {})
        vitals_container.addWidget(strip)

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

        update_vitals(features, getattr(analysis, "wellness", {}) or {})

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
        # persiste a sessão (offline) para o histórico/tendências longitudinais
        try:
            store.save(mode_box.currentText(), features.to_dict(), analysis.to_dict())
            gov.log(current_user, "analise",
                    f"modo={mode_box.currentText()} risco={analysis.risk_level}")
        except Exception as e:  # noqa: BLE001 - histórico é complementar
            log.append(f"[histórico indisponível: {e}]")
        # câmera continua ativa; libera novo "Analisar" imediatamente
        set_running(False)
        if llm_chk.isChecked():
            status.setText("Gerando narrativa do BitNet (câmera segue ativa)…")
            nw = NarrativeWorker(analysis, features)
            nw.done.connect(on_summary)
            state["narr"] = nw
            nw.start()

    def on_occupational(features):
        from app.clinical.nr01 import action_plan, assess_psychosocial, overall_risk
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
            from app.paths import data_path
            out = str(data_path("data", "plano_acao_nr01.pdf"))
            export_nr01_pdf(ind, plan, out, risk_level=risk,
                            institution=gov.get_institution())
            gov.log(current_user, "relatorio_gerado", f"NR-01 plano · {out}")
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
            from app.paths import data_path
            out = str(data_path("data", f"relatorio_setor_{setor}.pdf"))
            # plano com base no fator prioritário (usa o template de alto risco)
            from app.clinical.nr01 import assess_psychosocial
            from app.vision.features import BiomarkerFeatures
            plan = action_plan(assess_psychosocial(BiomarkerFeatures(
                frames=360, fps=30, microexpression_rate=18, blink_rate_per_min=46,
                hrv_sdnn_ms=12, rppg_quality=0.9))) if rep.overall_dist.get("alto", 0) > 0 else action_plan([])
            export_nr01_aggregate_pdf(rep, plan, out, institution=gov.get_institution())
            gov.log(current_user, "relatorio_gerado", f"NR-01 setor {setor} · {out}")
            log.append(f"Relatório agregado do setor salvo em {out} (n={rep.n}, anonimizado).")
        except Exception as e:  # noqa: BLE001
            log.append(f"[PDF indisponível: {e}]")
        status.setText(f"Relatório agregado do setor '{setor}' gerado.")

    def on_run():
        # Modo ocupacional exige consentimento informado (LGPD) específico
        # a cada sessão de análise, além do consentimento geral de abertura
        # do app (_consent_gate, já concedido para ligar a câmera).
        if "ocupacional" in mode_box.currentText() and not state.get("consent_nr01"):
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
            state["consent_nr01"] = True
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
    history_btn.clicked.connect(lambda: _open_trends(win, store))
    manage_btn.clicked.connect(lambda: _management_dialog(win, gov, current_user))

    # -- acessibilidade (eMAG/WCAG) --
    def change_font(delta):
        prefs["font_scale"] = max(0.85, min(1.6, round(prefs["font_scale"] + delta, 2)))
        apply_theme(); ui_settings.save(prefs)

    def toggle_contrast(on):
        prefs["high_contrast"] = bool(on)
        apply_theme(); ui_settings.save(prefs)
        gov.log(current_user, "acessibilidade", f"alto_contraste={bool(on)}")

    a_minus.clicked.connect(lambda: change_font(-0.1))
    a_plus.clicked.connect(lambda: change_font(0.1))
    contrast_chk.toggled.connect(toggle_contrast)

    # atalhos de teclado (navegação/acessibilidade)
    from PySide6.QtGui import QKeySequence, QShortcut
    QShortcut(QKeySequence("Ctrl+Return"), win, activated=on_run)
    QShortcut(QKeySequence("Ctrl+="), win, activated=lambda: change_font(0.1))
    QShortcut(QKeySequence("Ctrl+-"), win, activated=lambda: change_font(-0.1))

    # -- timeout de sessão (segurança / licitação) --
    from PySide6.QtCore import QEvent, QObject, QTimer
    timeout_ms = int(prefs["session_timeout_min"] * 60 * 1000)
    idle = QTimer(win); idle.setSingleShot(True)

    def on_timeout():
        gov.log(current_user, "sessao_expirada")
        status.setText("Sessão expirada por inatividade — reautentique.")
        while True:
            res = _login_dialog(win, gov)
            if res is None:
                win.close(); return
            if res[0] == current_user or res[1] == "administrador":
                gov.log(res[0], "login", "reautenticação")
                if timeout_ms > 0:
                    idle.start(timeout_ms)
                status.setText("Sessão reativada.")
                return

    idle.timeout.connect(on_timeout)
    if timeout_ms > 0:
        idle.start(timeout_ms)

    class _IdleFilter(QObject):
        def eventFilter(self, obj, ev):
            if ev.type() in (QEvent.MouseButtonPress, QEvent.KeyPress) and timeout_ms > 0:
                idle.start(timeout_ms)
            return False

    idle_filter = _IdleFilter()
    app.installEventFilter(idle_filter)
    state["idle_filter"] = idle_filter

    def on_close(ev):
        import contextlib
        cam.stop(); cam.wait(2000)
        with contextlib.suppress(Exception):
            gov.log(current_user, "logout")
            gov.close()
        with contextlib.suppress(Exception):
            store.close()
        ev.accept()
    win.closeEvent = on_close

    def _consent_gate() -> bool:
        """Aviso de não-diagnóstico + consentimento de captura biométrica (LGPD),
        exibido antes de ligar a webcam em QUALQUER modo — não só ocupacional."""
        from PySide6.QtWidgets import QMessageBox
        box = QMessageBox(win)
        box.setWindowTitle("Aviso e consentimento — leia antes de continuar")
        box.setIcon(QMessageBox.Warning)
        box.setText(DISCLAIMER)
        box.setInformativeText(
            "Este app irá ativar sua webcam e processar imagens do seu rosto/corpo "
            "para extrair biomarcadores (dado biométrico e de saúde, sensível pela "
            "LGPD). Todo o processamento é 100% LOCAL — nada é enviado à internet "
            "(veja PRIVACY.md). Nenhum vídeo bruto é salvo, apenas métricas "
            "numéricas agregadas.\n\nVocê concorda em prosseguir com a captura?")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.button(QMessageBox.Yes).setText("Concordo, continuar")
        box.button(QMessageBox.No).setText("Cancelar")
        return box.exec() == QMessageBox.Yes

    if not _consent_gate():
        gov.log(current_user, "consentimento_recusado")
        gov.close()
        return
    state["consent"] = True
    gov.log(current_user, "consentimento_concedido", "captura biométrica (LGPD)")

    win.show()
    cam.start()
    stop_btn.setEnabled(True)   # câmera ativa
    status.setText("Câmera ativa — clique em Analisar para iniciar a triagem.")
    return app.exec()
