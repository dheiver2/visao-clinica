"""Exportação de relatórios em PDF (ReportLab) e CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from app import DISCLAIMER
from app.clinical.reasoning_engine import ClinicalAnalysis
from app.vision.features import BiomarkerFeatures


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
               out_path: str | Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    out_path = Path(out_path)
    doc = SimpleDocTemplate(str(out_path), pagesize=A4)
    styles = getSampleStyleSheet()
    flow = [
        Paragraph("Relatório Técnico — Triagem por Visão Computacional", styles["Title"]),
        Paragraph(f"Nível de risco global: <b>{analysis.risk_level}</b>", styles["Normal"]),
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
    doc.build(flow)
    return out_path


def export_nr01_pdf(indicators, plan, out_path, risk_level="indeterminado"):
    """Gera o relatório PDF do plano de ação NR-01 (riscos psicossociais)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    from app.clinical.nr01 import DISCLAIMER_NR01

    out_path = Path(out_path)
    doc = SimpleDocTemplate(str(out_path), pagesize=A4)
    st = getSampleStyleSheet()
    flow = [
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
    doc.build(flow)
    return out_path
