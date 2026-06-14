"""Painel de condições rastreáveis por visão computacional.

Camada **determinística** que garante uma saída clínica de triagem para CADA
condição do painel, a partir dos biomarcadores — independente do LLM. O BitNet
acrescenta o raciocínio narrativo por cima destes indicadores.

IMPORTANTE: são indicadores PROBABILÍSTICOS de triagem/pesquisa, não diagnósticos.
Cada condição declara explicitamente os biomarcadores que a sustentam.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.vision.features import BiomarkerFeatures


@dataclass
class ConditionResult:
    key: str
    name: str
    score: float                      # 0..1 (probabilidade relativa de triagem)
    level: str                        # baixo | moderado | alto | indeterminado
    factors: list[str] = field(default_factory=list)   # biomarcadores que contribuíram
    rationale: str = ""               # explicação curta e legível

    def to_dict(self) -> dict:
        return {
            "key": self.key, "name": self.name, "score": round(self.score, 3),
            "level": self.level, "factors": self.factors, "rationale": self.rationale,
        }


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _band(x: float, lo: float, hi: float) -> float:
    """Normaliza x para 0..1 dentro da faixa [lo, hi] (resposta linear saturada)."""
    if hi <= lo:
        return 0.0
    return _clamp((x - lo) / (hi - lo))


def _bell(x: float, center: float, width: float) -> float:
    """Resposta tipo sino: 1 no centro, caindo conforme |x-center| cresce."""
    if width <= 0:
        return 0.0
    return _clamp(1.0 - abs(x - center) / width)


def _level(score: float) -> str:
    if score >= 0.66:
        return "alto"
    if score >= 0.33:
        return "moderado"
    return "baixo"


# -- definição do painel --------------------------------------------------------
# Cada avaliador recebe BiomarkerFeatures e retorna (score, factors).

def _eval_parkinsonian_tremor(f: BiomarkerFeatures):
    # Tremor de repouso parkinsoniano: 4–6 Hz com amplitude perceptível.
    freq = _bell(f.tremor_hand_hz, center=5.0, width=2.5)
    amp = _band(f.tremor_hand_amplitude, 0.004, 0.03)
    head = _bell(f.tremor_head_hz, center=5.0, width=3.0) * 0.5
    score = _clamp(0.6 * freq * amp + 0.4 * max(freq * amp, head))
    factors = []
    if freq > 0.3:
        factors.append(f"tremor de mão ~{f.tremor_hand_hz:.1f} Hz (faixa 4–6 Hz)")
    if amp > 0.3:
        factors.append("amplitude de tremor elevada")
    return score, factors


def _eval_facial_palsy(f: BiomarkerFeatures):
    # Assimetria facial sustentada (paralisia facial / sequela de AVC).
    score = _band(f.facial_asymmetry, 0.12, 0.45)
    factors = []
    if score > 0.2:
        factors.append(f"assimetria facial {f.facial_asymmetry:.2f}")
    return score, factors


def _eval_oculomotor(f: BiomarkerFeatures):
    # Disfunção oculomotora: saccades excessivas e/ou dispersão do olhar alta.
    sacc = _band(f.saccade_rate, 90.0, 220.0)
    disp = _band(f.gaze_dispersion, 0.12, 0.4)
    score = _clamp(0.6 * sacc + 0.4 * disp)
    factors = []
    if sacc > 0.3:
        factors.append(f"saccades {f.saccade_rate:.0f}/min")
    if disp > 0.3:
        factors.append(f"dispersão do olhar {f.gaze_dispersion:.2f}")
    return score, factors


def _eval_blink_disorder(f: BiomarkerFeatures):
    # Distúrbio do piscar: blefaroespasmo (taxa alta) ou hipomotricidade (taxa baixa).
    high = _band(f.blink_rate_per_min, 28.0, 60.0)
    low = _band(12.0 - f.blink_rate_per_min, 0.0, 8.0)  # < ~12/min
    score = _clamp(max(high, low))
    factors = []
    if high > 0.3:
        factors.append(f"piscar acelerado {f.blink_rate_per_min:.0f}/min")
    elif low > 0.3:
        factors.append(f"piscar reduzido {f.blink_rate_per_min:.0f}/min")
    return score, factors


def _eval_drowsiness(f: BiomarkerFeatures):
    # Sonolência/fadiga: piscar reduzido + baixa movimentação corporal.
    low_blink = _band(10.0 - f.blink_rate_per_min, 0.0, 8.0)
    still = _band(0.03 - f.body_movement_index, 0.0, 0.03)
    score = _clamp(0.6 * low_blink + 0.4 * still)
    factors = []
    if low_blink > 0.3:
        factors.append("piscar reduzido")
    if still > 0.3:
        factors.append("baixa movimentação corporal")
    return score, factors


def _eval_stress_anxiety(f: BiomarkerFeatures):
    # Estresse/ansiedade: microexpressões frequentes + piscar acelerado.
    micro = _band(f.microexpression_rate, 6.0, 20.0)
    blink = _band(f.blink_rate_per_min, 25.0, 50.0)
    score = _clamp(0.6 * micro + 0.4 * blink)
    factors = []
    if micro > 0.3:
        factors.append(f"microexpressões {f.microexpression_rate:.0f}/min")
    if blink > 0.3:
        factors.append("piscar acelerado")
    return score, factors


def _eval_hypomimia(f: BiomarkerFeatures):
    # Hipomimia / afeto reduzido (Parkinson, depressão): poucas microexpressões
    # e baixa movimentação — "face em máscara".
    low_micro = _band(4.0 - f.microexpression_rate, 0.0, 4.0)
    still = _band(0.03 - f.body_movement_index, 0.0, 0.03)
    score = _clamp(0.6 * low_micro + 0.4 * still)
    factors = []
    if low_micro > 0.3:
        factors.append("microexpressões escassas (hipomimia)")
    if still > 0.3:
        factors.append("baixa movimentação")
    return score, factors


def _eval_dyskinesia(f: BiomarkerFeatures):
    # Movimentos involuntários/discinesia: movimentação corporal e sway elevados.
    body = _band(f.body_movement_index, 0.08, 0.3)
    sway = _band(f.postural_sway, 0.08, 0.3)
    score = _clamp(0.6 * body + 0.4 * sway)
    factors = []
    if body > 0.3:
        factors.append("movimentação corporal aumentada")
    if sway > 0.3:
        factors.append("instabilidade postural")
    return score, factors


# (key, nome clínico, avaliador)
PANEL = [
    ("parkinsonian_tremor", "Tremor parkinsoniano (repouso 4–6 Hz)", _eval_parkinsonian_tremor),
    ("facial_palsy", "Assimetria facial / paralisia (Bell, AVC)", _eval_facial_palsy),
    ("oculomotor", "Disfunção oculomotora", _eval_oculomotor),
    ("blink_disorder", "Distúrbio do piscar (blefaroespasmo)", _eval_blink_disorder),
    ("drowsiness", "Sonolência / fadiga", _eval_drowsiness),
    ("stress_anxiety", "Estresse / ansiedade", _eval_stress_anxiety),
    ("hypomimia", "Hipomimia / afeto reduzido", _eval_hypomimia),
    ("dyskinesia", "Movimentos involuntários / discinesia", _eval_dyskinesia),
]


def evaluate_conditions(f: BiomarkerFeatures) -> list[ConditionResult]:
    """Avalia TODAS as condições do painel; garante uma saída por doença."""
    insufficient = f.frames < 10
    results: list[ConditionResult] = []
    for key, name, fn in PANEL:
        if insufficient:
            results.append(ConditionResult(
                key=key, name=name, score=0.0, level="indeterminado",
                rationale="Dados insuficientes (captura muito curta)."))
            continue
        score, factors = fn(f)
        level = _level(score)
        if factors:
            rationale = "Sustentado por: " + "; ".join(factors) + "."
        else:
            rationale = "Sem sinais relevantes nos biomarcadores observados."
        results.append(ConditionResult(key=key, name=name, score=score,
                                        level=level, factors=factors,
                                        rationale=rationale))
    results.sort(key=lambda r: r.score, reverse=True)
    return results
