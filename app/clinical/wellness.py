"""Score de bem-estar / estresse (0–100) — índice-síntese estilo apps de vitais.

Combina, de forma determinística, sinais vitais (FC, VFC, respiração, índice de
Baevsky) e faciais (microexpressões, piscar) numa pontuação única de 0 (alerta) a
100 (ótimo), como o "wellness score" / "stress level" que os apps comerciais de
vitais por câmera usam como métrica de destaque.

Não é diagnóstico — é um indicador agregado de apoio, gated pela qualidade do sinal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.vision.features import BiomarkerFeatures


@dataclass
class Wellness:
    score: int = 0                    # 0..100 (maior = melhor)
    label: str = "indeterminado"      # ótimo | bom | moderado | alerta | indeterminado
    stress: int = 0                   # 0..100 (maior = mais estresse)
    components: dict[str, float] = field(default_factory=dict)  # subscores 0..1
    reliable: bool = False


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _ramp(x: float, lo: float, hi: float) -> float:
    """0 abaixo de lo, 1 acima de hi, linear no meio."""
    if hi <= lo:
        return 0.0
    return _clamp((x - lo) / (hi - lo))


def _hr_normalcy(hr: float) -> float | None:
    """Proximidade de uma FC de repouso saudável (60–75 bpm ótimo)."""
    if hr <= 0:
        return None
    if 60.0 <= hr <= 75.0:
        return 1.0
    if hr < 60.0:
        return _clamp(1.0 - (60.0 - hr) / 25.0)
    return _clamp(1.0 - (hr - 75.0) / 45.0)


def compute_wellness(f: BiomarkerFeatures) -> Wellness:
    """Índice de bem-estar 0–100 a partir dos biomarcadores da sessão."""
    reliable = (f.rppg_quality >= 0.3 and f.signal_quality >= 0.40)
    comp: dict[str, float] = {}

    hr = _hr_normalcy(f.heart_rate_bpm)
    if hr is not None:
        comp["cardíaco"] = hr

    # Autonômico: VFC maior é melhor (RMSSD 20–70 ms saudável em janelas curtas).
    if f.hrv_rmssd_ms > 0:
        comp["autonômico"] = _clamp(f.hrv_rmssd_ms / 60.0)
    elif f.hrv_sdnn_ms > 0:
        comp["autonômico"] = _clamp(f.hrv_sdnn_ms / 60.0)

    # Respiratório: 12–20 rpm é ótimo; penaliza afastamento de 16 rpm.
    if f.respiration_bpm > 0:
        rr = f.respiration_bpm
        comp["respiratório"] = 1.0 if 12.0 <= rr <= 20.0 else _clamp(1.0 - abs(rr - 16.0) / 16.0)

    # Estresse (0..1, maior = mais estresse): Baevsky + assinatura facial.
    facial = _clamp(0.5 * _ramp(f.microexpression_rate, 6.0, 20.0)
                    + 0.5 * _ramp(f.blink_rate_per_min, 25.0, 55.0))
    if f.stress_index > 0:
        stress01 = _clamp(0.6 * _ramp(f.stress_index, 80.0, 500.0) + 0.4 * facial)
    else:
        stress01 = facial
    comp["calma"] = 1.0 - stress01

    if not comp:
        return Wellness(reliable=False)

    score = int(round(100.0 * sum(comp.values()) / len(comp)))
    stress = int(round(100.0 * stress01))
    label = ("ótimo" if score >= 80 else
             "bom" if score >= 65 else
             "moderado" if score >= 45 else "alerta")
    if not reliable:
        label = "indeterminado"
    return Wellness(score=score, label=label, stress=stress,
                    components={k: round(v, 3) for k, v in comp.items()},
                    reliable=reliable)
