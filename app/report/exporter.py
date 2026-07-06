"""Exportação de relatórios em PDF (ReportLab) e CSV."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from app import DISCLAIMER
from app.clinical.reasoning_engine import ClinicalAnalysis
from app.vision.features import BiomarkerFeatures


def make_protocol(prefix: str = "VC") -> str:
    """Número de protocolo do relatório (rastreabilidade — exigido em editais)."""
    return f"{prefix}-{datetime.now():%Y%m%d-%H%M%S}"


def _institution_header(inst: dict | None, styles) -> list:
    """Cabeçalho com identificação do órgão (logo + nome + CNPJ)."""
    if not inst or not (inst.get("nome") or inst.get("cnpj")):
        return []
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

    nome = inst.get("nome") or ""
    cnpj = f"CNPJ: {inst['cnpj']}" if inst.get("cnpj") else ""
    txt = Paragraph(f"<b>{nome}</b><br/>{cnpj}", styles["Normal"])
    logo_path = inst.get("logo_path") or ""
    cell0 = txt
    cols = [txt]
    if logo_path and Path(logo_path).exists():
        try:
            cell0 = Image(logo_path, width=18 * mm, height=18 * mm)
            cols = [cell0, txt]
        except Exception:  # noqa: BLE001 - logo inválida não bloqueia o relatório
            cols = [txt]
    tbl = Table([cols], hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.6, colors.grey),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return [tbl, Spacer(1, 10)]


def _institution_footer(inst: dict | None, protocol: str, styles) -> list:
    """Rodapé com responsável técnico, registro no conselho e protocolo."""
    from reportlab.platypus import Paragraph, Spacer

    parts = [f"Protocolo: {protocol}",
             f"Emitido em: {datetime.now():%d/%m/%Y %H:%M}"]
    if inst:
        if inst.get("responsavel"):
            parts.append(f"Responsável técnico: {inst['responsavel']}")
        if inst.get("conselho"):
            parts.append(f"Registro: {inst['conselho']}")
    return [Spacer(1, 12),
            Paragraph("<font size=8 color='#666666'>" + " · ".join(parts) + "</font>",
                      styles["Normal"])]


def export_csv(features: BiomarkerFeatures, analysis: ClinicalAnalysis,
               out_path: str | Path) -> Path:
    out_path = Path(out_path)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["categoria", "variavel", "valor"])
        for k, v in features.to_dict().items():
            w.writerow(["biomarcador", k, v])
        w.writerow(["analise", "risk_level", analysis.risk_level])
        for c in analysis.conditions:
            w.writerow(["condicao", c.name, f"{c.level} (score {c.score:.2f})"])
        for h in analysis.hypotheses:
            w.writerow(["analise", "hipotese", h])
        w.writerow(["aviso", "disclaimer", DISCLAIMER])
    return out_path


def export_pdf(report_text: str, analysis: ClinicalAnalysis,
               out_path: str | Path, institution: dict | None = None,
               protocol: str | None = None) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    out_path = Path(out_path)
    protocol = protocol or make_protocol()
    doc = SimpleDocTemplate(str(out_path), pagesize=A4)
    styles = getSampleStyleSheet()
    flow = _institution_header(institution, styles) + [
        Paragraph("Relatório Técnico — Triagem por Visão Computacional", styles["Title"]),
        Paragraph(f"Nível de risco global: <b>{analysis.risk_level}</b>", styles["Normal"]),
    ]
    w = getattr(analysis, "wellness", None) or {}
    if w.get("reliable"):
        flow.append(Paragraph(
            f"Índice de bem-estar: <b>{int(w.get('score', 0))}/100</b> "
            f"({w.get('label', '—')}) · estresse estimado {int(w.get('stress', 0))}%",
            styles["Normal"]))
    flow += [
        Spacer(1, 10),
        Paragraph("Indicadores clínicos de triagem por condição:", styles["Heading3"]),
    ]
    for c in analysis.conditions:
        flow.append(Paragraph(
            f"• <b>{c.name}</b>: {c.level} (score {c.score:.2f}) — {c.rationale}",
            styles["Normal"]))
    flow.append(Spacer(1, 12))
    for para in report_text.split("\n\n"):
        flow.append(Paragraph(para.replace("\n", "<br/>"), styles["Normal"]))
        flow.append(Spacer(1, 8))
    flow.append(Spacer(1, 12))
    flow.append(Paragraph(f"<i>{DISCLAIMER}</i>", styles["Italic"]))
    flow += _institution_footer(institution, protocol, styles)
    doc.build(flow)
    return out_path


def export_nr01_pdf(indicators, plan, out_path, risk_level="indeterminado",
                    institution=None, protocol=None):
    """Gera o relatório PDF do plano de ação NR-01 (riscos psicossociais)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    from app.clinical.nr01 import DISCLAIMER_NR01

    out_path = Path(out_path)
    protocol = protocol or make_protocol("NR01")
    doc = SimpleDocTemplate(str(out_path), pagesize=A4)
    st = getSampleStyleSheet()
    flow = _institution_header(institution, st) + [
        Paragraph("Plano de Ação — NR-01 (Riscos Psicossociais)", st["Title"]),
        Paragraph(f"Nível de risco psicossocial: <b>{risk_level.upper()}</b>", st["Normal"]),
        Spacer(1, 10),
        Paragraph("Indicadores de bem-estar (triagem voluntária)", st["Heading3"]),
    ]
    for i in indicators:
        flow.append(Paragraph(f"• <b>{i.name}</b>: {i.level} (score {i.score:.2f})", st["Normal"]))
    flow.append(Spacer(1, 12))
    flow.append(Paragraph("Plano de ação (GRO/PGR)", st["Heading3"]))
    for p in plan:
        flow.append(Paragraph(f"<b>{p['fase']}</b> — <i>{p['prazo']}</i>", st["Normal"]))
        for a in p["acoes"]:
            flow.append(Paragraph(f"&nbsp;&nbsp;• {a}", st["Normal"]))
        flow.append(Spacer(1, 6))
    flow.append(Spacer(1, 12))
    flow.append(Paragraph(f"<i>{DISCLAIMER_NR01}</i>", st["Italic"]))
    flow += _institution_footer(institution, protocol, st)
    doc.build(flow)
    return out_path


def export_nr01_aggregate_pdf(report, plan, out_path, institution=None, protocol=None):
    """Relatório AGREGADO e anonimizado por setor (NR-01) em PDF."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from app.clinical.nr01 import DISCLAIMER_NR01

    out_path = Path(out_path)
    protocol = protocol or make_protocol("NR01AG")
    doc = SimpleDocTemplate(str(out_path), pagesize=A4)
    st = getSampleStyleSheet()
    flow = _institution_header(institution, st) + [
        Paragraph(f"Relatório Agregado NR-01 — Setor: {report.setor}", st["Title"]),
        Paragraph(f"Amostra: <b>{report.n}</b> triagens voluntárias (anonimizadas)", st["Normal"]),
        Spacer(1, 8),
        Paragraph("Distribuição do risco psicossocial global", st["Heading3"]),
        Paragraph(" · ".join(f"{lv}: {pct}%" for lv, pct in report.overall_dist.items()), st["Normal"]),
        Spacer(1, 10),
        Paragraph("Distribuição por fator (% de colaboradores)", st["Heading3"]),
    ]
    data = [["Fator", "Baixo", "Moderado", "Alto"]]
    for fator, d in report.by_factor.items():
        data.append([fator, f"{d['baixo']}%", f"{d['moderado']}%", f"{d['alto']}%"])
    tbl = Table(data, hAlign="LEFT")
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b1e25")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))
    flow += [tbl, Spacer(1, 12)]
    if report.priority:
        flow.append(Paragraph("Fatores prioritários: " + ", ".join(report.priority), st["Normal"]))
        flow.append(Spacer(1, 8))
    flow.append(Paragraph("Plano de ação (GRO/PGR)", st["Heading3"]))
    for p in plan:
        flow.append(Paragraph(f"<b>{p['fase']}</b> — <i>{p['prazo']}</i>", st["Normal"]))
        for a in p["acoes"]:
            flow.append(Paragraph(f"&nbsp;&nbsp;• {a}", st["Normal"]))
        flow.append(Spacer(1, 6))
    flow.append(Spacer(1, 10))
    flow.append(Paragraph(f"<i>{DISCLAIMER_NR01}</i>", st["Italic"]))
    flow += _institution_footer(institution, protocol, st)
    doc.build(flow)
    return out_path
