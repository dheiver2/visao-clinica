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
    confidence: float = 1.0           # 0..1 (qualidade do sinal que sustenta o score)

    def to_dict(self) -> dict:
        return {
            "key": self.key, "name": self.name, "score": round(self.score, 3),
            "level": self.level, "factors": self.factors, "rationale": self.rationale,
            "confidence": round(self.confidence, 3),
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

def _snr_gate(f: BiomarkerFeatures) -> float:
    # Oscilação só conta como tremor real se o pico espectral se destacar do ruído.
    return _band(f.tremor_snr, 3.0, 12.0)


def _eval_parkinsonian_tremor(f: BiomarkerFeatures):
    # Tremor de repouso parkinsoniano: 4–6 Hz com amplitude perceptível e SNR alto.
    freq = _bell(f.tremor_hand_hz, center=5.0, width=2.5)
    amp = _band(f.tremor_hand_amplitude, 0.004, 0.03)
    head = _bell(f.tremor_head_hz, center=5.0, width=3.0) * 0.5
    gate = _snr_gate(f)
    score = _clamp((0.6 * freq * amp + 0.4 * max(freq * amp, head)) * gate)
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
    # Estresse/ansiedade: microexpressões + piscar acelerado + VFC reduzida.
    # VFC baixa indica disregulação autonômica (rPPG; gated pela qualidade do sinal).
    micro = _band(f.microexpression_rate, 6.0, 20.0)
    blink = _band(f.blink_rate_per_min, 25.0, 50.0)
    hrv_gate = _band(f.rppg_quality, 0.3, 0.7)
    low_hrv = _band(40.0 - f.hrv_sdnn_ms, 0.0, 40.0) * hrv_gate
    score = _clamp(0.45 * micro + 0.3 * blink + 0.25 * low_hrv)
    factors = []
    if micro > 0.3:
        factors.append(f"microexpressões {f.microexpression_rate:.0f}/min")
    if blink > 0.3:
        factors.append("piscar acelerado")
    if low_hrv > 0.3:
        factors.append(f"VFC reduzida (SDNN {f.hrv_sdnn_ms:.0f} ms)")
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


def _eval_autism_signs(f: BiomarkerFeatures):
    # Sinais compatíveis com TEA: contato visual reduzido, baixa expressividade
    # facial e movimentos repetitivos (estereotipias).
    low_eye_contact = _band(0.55 - f.gaze_center_ratio, 0.0, 0.45)
    low_expressivity = _band(6.0 - f.microexpression_rate, 0.0, 6.0)
    # Estereotipias: periodicidade do movimento + autocorrelação (Goodwin 2011).
    repetitive = _clamp(max(
        _band(f.movement_periodicity, 0.15, 0.45) * _band(f.body_movement_index, 0.04, 0.25)
        + 0.4 * _band(f.movement_periodicity, 0.2, 0.5),
        _band(f.stereotypy_index, 0.2, 0.6)))
    atypical_gaze = _band(f.saccade_rate, 120.0, 240.0)
    score = _clamp(0.35 * low_eye_contact + 0.25 * low_expressivity
                   + 0.25 * repetitive + 0.15 * atypical_gaze)
    factors = []
    if low_eye_contact > 0.3:
        factors.append(f"contato visual reduzido (olhar ao centro {f.gaze_center_ratio:.0%})")
    if low_expressivity > 0.3:
        factors.append("expressividade facial reduzida")
    if repetitive > 0.3:
        factors.append("movimentos repetitivos / estereotipias")
    return score, factors


def _eval_parkinson_composite(f: BiomarkerFeatures):
    # Perfil parkinsoniano: tremor de repouso + hipomimia + piscar reduzido +
    # bradicinesia (lentidão/redução de movimento).
    tremor = (_bell(f.tremor_hand_hz, 5.0, 2.5)
              * _band(f.tremor_hand_amplitude, 0.004, 0.03) * _snr_gate(f))
    # Hipomimia: contagem de microexpressões OU índice FACS de dinâmica (Bandini 2017).
    hypomimia = max(_band(4.0 - f.microexpression_rate, 0.0, 4.0), f.hypomimia_index)
    low_blink = _band(10.0 - f.blink_rate_per_min, 0.0, 8.0)
    bradykinesia = _band(0.03 - f.body_movement_index, 0.0, 0.03)
    score = _clamp(0.35 * tremor + 0.25 * hypomimia + 0.2 * low_blink + 0.2 * bradykinesia)
    factors = []
    if tremor > 0.3:
        factors.append(f"tremor de repouso ~{f.tremor_hand_hz:.1f} Hz")
    if hypomimia > 0.3:
        factors.append("hipomimia (face em máscara)")
    if low_blink > 0.3:
        factors.append("piscar reduzido")
    if bradykinesia > 0.3:
        factors.append("bradicinesia (movimento reduzido)")
    return score, factors


def _eval_alzheimer_signs(f: BiomarkerFeatures):
    # Comprometimento cognitivo (tipo Alzheimer): instabilidade oculomotora,
    # fixação prejudicada e expressividade reduzida. Marcadores oculares são dos
    # mais estudados em demências.
    # Instabilidade de fixação: dispersão + BCEA (Anderson & MacAskill 2013).
    gaze_instability = _clamp(max(_band(f.gaze_dispersion, 0.14, 0.4),
                                  _band(f.fixation_bcea, 0.05, 0.5)))
    poor_fixation = _band(0.5 - f.gaze_center_ratio, 0.0, 0.4)
    erratic_saccade = _band(f.saccade_rate, 120.0, 240.0)
    low_expressivity = _band(4.0 - f.microexpression_rate, 0.0, 4.0)
    score = _clamp(0.35 * gaze_instability + 0.25 * poor_fixation
                   + 0.25 * erratic_saccade + 0.15 * low_expressivity)
    factors = []
    if gaze_instability > 0.3:
        factors.append("instabilidade do olhar / fixação")
    if erratic_saccade > 0.3:
        factors.append(f"saccades erráticas {f.saccade_rate:.0f}/min")
    if low_expressivity > 0.3:
        factors.append("expressividade reduzida")
    return score, factors


def _eval_down_signs(f: BiomarkerFeatures):
    # Sinais compatíveis com Síndrome de Down a partir de marcadores dinâmicos de
    # HIPOTONIA (tônus reduzido): boca frequentemente entreaberta, baixa amplitude
    # de expressão e movimento reduzido. ATENÇÃO: o diagnóstico depende de morfologia
    # craniofacial e confirmação genética — este indicador dinâmico é apenas auxiliar.
    mouth_open = _band(f.mouth_open_ratio, 0.25, 0.7)
    low_tone = _band(0.015 - f.expression_amplitude, 0.0, 0.015)
    low_movement = _band(0.025 - f.body_movement_index, 0.0, 0.025)
    score = _clamp(0.5 * mouth_open + 0.3 * low_tone + 0.2 * low_movement)
    factors = []
    if mouth_open > 0.3:
        factors.append(f"boca entreaberta {f.mouth_open_ratio:.0%} do tempo (hipotonia)")
    if low_tone > 0.3:
        factors.append("baixa amplitude de expressão facial")
    return score, factors


# (key, nome clínico, avaliador)
PANEL = [
    ("autism_signs", "Sinais compatíveis com TEA (autismo)", _eval_autism_signs),
    ("parkinson_composite", "Perfil parkinsoniano (composto)", _eval_parkinson_composite),
    ("alzheimer_signs", "Sinais de comprometimento cognitivo (tipo Alzheimer)", _eval_alzheimer_signs),
    ("down_signs", "Sinais compatíveis com Síndrome de Down", _eval_down_signs),
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
    """Avalia TODAS as condições do painel; garante uma saída por doença.

    Cada resultado carrega uma CONFIANÇA derivada da qualidade do sinal (detecção
    de face × iluminação) e da quantidade de dados — para distinguir um achado
    bem-sustentado de um obtido em condições ruins.
    """
    insufficient = f.frames < 10
    # Confiança base: qualidade do sinal modulada pela duração efetiva da captura.
    data_factor = _clamp(f.frames / 200.0)        # ~7s @30fps para confiança plena
    base_conf = _clamp(f.signal_quality * (0.5 + 0.5 * data_factor))
    results: list[ConditionResult] = []
    for key, name, fn in PANEL:
        if insufficient:
            results.append(ConditionResult(
                key=key, name=name, score=0.0, level="indeterminado",
                rationale="Dados insuficientes (captura muito curta).",
                confidence=0.0))
            continue
        score, factors = fn(f)
        level = _level(score)
        if factors:
            rationale = "Sustentado por: " + "; ".join(factors) + "."
        else:
            rationale = "Sem sinais relevantes nos biomarcadores observados."
        conf = base_conf
        if base_conf < 0.5:
            rationale += " (confiança reduzida pela qualidade do sinal)"
        results.append(ConditionResult(key=key, name=name, score=score,
                                        level=level, factors=factors,
                                        rationale=rationale, confidence=conf))
    # Ordena por relevância clínica: score ponderado pela confiança.
    results.sort(key=lambda r: r.score * (0.5 + 0.5 * r.confidence), reverse=True)
    return results
