"""Módulo Ocupacional — NR-01 (riscos psicossociais), Lei 14.457/2022 e ESG.

Mapeia os biomarcadores de bem-estar (estresse, ansiedade, fadiga, VFC) em
**indicadores de risco psicossocial** e gera um **plano de ação** alinhado à
NR-01 (Gerenciamento de Riscos Ocupacionais — GRO/PGR), ao programa de prevenção
ao assédio (Lei 14.457/2022) e a práticas de ESG/ética/antifraude.

GUARDRAILS (obrigatórios):
- É uma ferramenta de **apoio e conscientização de bem-estar**, NÃO um exame médico
  nem base para decisão disciplinar, demissão ou punição individual.
- Uso deve ser **voluntário e com consentimento informado** (LGPD, Lei 13.709/2018:
  dado de saúde/biométrico é sensível). Recomenda-se uso **agregado/anonimizado**.
- A conformidade com a NR-01 exige avaliação ORGANIZACIONAL (inventário de riscos,
  questionários validados, escuta ativa) — este indicador é complementar, não substitui.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.clinical.conditions import _band, _clamp, _level
from app.vision.features import BiomarkerFeatures

DISCLAIMER_NR01 = (
    "USO OCUPACIONAL: ferramenta voluntária de apoio ao bem-estar, com consentimento "
    "informado (LGPD). NÃO é exame médico nem base para decisões disciplinares. "
    "Recomenda-se uso agregado/anonimizado. Não substitui a avaliação organizacional "
    "de riscos psicossociais exigida pela NR-01."
)


@dataclass
class PsychoIndicator:
    key: str
    name: str
    score: float
    level: str
    factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"key": self.key, "name": self.name, "score": round(self.score, 3),
                "level": self.level, "factors": self.factors}


def _eval_estresse(f: BiomarkerFeatures):
    micro = _band(f.microexpression_rate, 6.0, 20.0)
    blink = _band(f.blink_rate_per_min, 25.0, 50.0)
    hrv_gate = _band(f.rppg_quality, 0.3, 0.7)
    low_hrv = _band(40.0 - f.hrv_sdnn_ms, 0.0, 40.0) * hrv_gate
    score = _clamp(0.4 * micro + 0.3 * blink + 0.3 * low_hrv)
    fac = []
    if micro > 0.3: fac.append("microexpressões frequentes")
    if low_hrv > 0.3: fac.append(f"VFC reduzida (SDNN {f.hrv_sdnn_ms:.0f} ms)")
    if blink > 0.3: fac.append("piscar acelerado")
    return score, fac


def _eval_fadiga(f: BiomarkerFeatures):
    low_blink = _band(10.0 - f.blink_rate_per_min, 0.0, 8.0)
    still = _band(0.03 - f.body_movement_index, 0.0, 0.03)
    score = _clamp(0.6 * low_blink + 0.4 * still)
    fac = []
    if low_blink > 0.3: fac.append("sinais de sonolência (piscar reduzido)")
    if still > 0.3: fac.append("baixa movimentação")
    return score, fac


def _eval_sobrecarga(f: BiomarkerFeatures):
    # Sobrecarga/burnout: estresse alto + fadiga + VFC baixa.
    est, _ = _eval_estresse(f)
    fad, _ = _eval_fadiga(f)
    hrv = _band(35.0 - f.hrv_sdnn_ms, 0.0, 35.0) * _band(f.rppg_quality, 0.3, 0.7)
    score = _clamp(0.45 * est + 0.35 * fad + 0.2 * hrv)
    fac = []
    if score > 0.5: fac.append("combinação de estresse, fadiga e desregulação autonômica")
    return score, fac


def _eval_afeto(f: BiomarkerFeatures):
    # Afeto reduzido/desengajamento: hipomimia + poucas microexpressões.
    low_micro = _band(4.0 - f.microexpression_rate, 0.0, 4.0)
    score = _clamp(0.6 * max(low_micro, f.hypomimia_index) + 0.4 * low_micro)
    fac = []
    if score > 0.4: fac.append("expressividade emocional reduzida")
    return score, fac


PSYCH_PANEL = [
    ("estresse", "Estresse ocupacional", _eval_estresse),
    ("fadiga", "Fadiga / cansaço", _eval_fadiga),
    ("sobrecarga", "Sobrecarga / risco de burnout", _eval_sobrecarga),
    ("afeto", "Desengajamento / afeto reduzido", _eval_afeto),
]


def assess_psychosocial(f: BiomarkerFeatures) -> list[PsychoIndicator]:
    """Avalia os fatores psicossociais a partir dos biomarcadores."""
    if f.frames < 10:
        return [PsychoIndicator(k, n, 0.0, "indeterminado") for k, n, _ in PSYCH_PANEL]
    out = []
    for key, name, fn in PSYCH_PANEL:
        score, fac = fn(f)
        out.append(PsychoIndicator(key, name, score, _level(score), fac))
    out.sort(key=lambda i: i.score, reverse=True)
    return out


def overall_risk(indicators: list[PsychoIndicator]) -> str:
    order = {"indeterminado": -1, "baixo": 0, "moderado": 1, "alto": 2}
    return max((i.level for i in indicators),
               key=lambda lv: order.get(lv, -1), default="indeterminado")


# -- Plano de ação NR-01 --------------------------------------------------------

def action_plan(indicators: list[PsychoIndicator]) -> list[dict]:
    """Gera um plano de ação NR-01 (fases do GRO/PGR) + ações tailored ao risco."""
    risk = overall_risk(indicators)
    high = [i.name for i in indicators if i.level == "alto"]
    plan = [
        {"fase": "1. Identificação", "prazo": "0–30 dias",
         "acoes": [
             "Inventariar riscos psicossociais por setor/função (NR-01, item GRO).",
             "Aplicar instrumento validado (COPSOQ, HSE-IT ou Karasek/JCQ) com escuta ativa.",
             "Coletar indicadores de bem-estar (esta ferramenta) de forma VOLUNTÁRIA e anonimizada."]},
        {"fase": "2. Avaliação", "prazo": "30–45 dias",
         "acoes": [
             "Classificar cada risco por probabilidade × severidade (matriz de risco).",
             "Priorizar fatores com nível alto: " + (", ".join(high) if high else "—") + "."]},
        {"fase": "3. Controle (medidas)", "prazo": "45–120 dias",
         "acoes": [
             "Medidas ORGANIZACIONAIS primeiro: carga/ritmo de trabalho, jornada, autonomia, pausas.",
             "Canal de denúncia independente e política de não-retaliação (combate a assédio e fraude).",
             "Programa de prevenção ao assédio (Lei 14.457/2022 — CIPAA) e código de ética.",
             "Treinamento anti-assédio e de gestão respeitosa para lideranças.",
             "Apoio psicológico / EAP e encaminhamento clínico quando indicado."]},
        {"fase": "4. Monitoramento", "prazo": "contínuo / revisão anual",
         "acoes": [
             "Reavaliar indicadores periodicamente; medir eficácia das medidas.",
             "Registrar tudo no PGR e atualizar o GRO (auditável; evita multas e passivos).",
             "Reporte ESG: indicadores de saúde mental, clima e cultura de ética."]},
    ]
    if risk == "alto":
        plan.insert(0, {"fase": "0. Ação imediata", "prazo": "0–7 dias",
                        "acoes": ["Risco psicossocial ALTO detectado: acionar SESMT/RH, reforçar "
                                  "apoio psicológico e revisar fatores organizacionais agudos."]})
    return plan
