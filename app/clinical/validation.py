"""Validação da sessão e faixas de acurácia.

Garante que só sejam exibidos indicadores em que se pode confiar: classifica a
confiança em faixas (baixa/média/alta) e valida a qualidade da captura antes de
apresentar qualquer resultado.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.vision.features import BiomarkerFeatures

# Limiares de acurácia (sobre a confiança 0..1 de cada condição)
ACC_HIGH = 0.66
ACC_MED = 0.40


def accuracy_band(confidence: float) -> str:
    """Classifica a confiança em 'alta' | 'média' | 'baixa'."""
    if confidence >= ACC_HIGH:
        return "alta"
    if confidence >= ACC_MED:
        return "média"
    return "baixa"


def is_displayable(confidence: float) -> bool:
    """Só exibe indicadores com acurácia média ou alta."""
    return confidence >= ACC_MED


@dataclass
class SessionValidation:
    ok: bool
    quality: float
    messages: list[str] = field(default_factory=list)


def validate_session(f: BiomarkerFeatures) -> SessionValidation:
    """Valida se a captura tem qualidade para gerar indicadores confiáveis."""
    msgs: list[str] = []
    if f.frames < 60:
        msgs.append("Captura muito curta — grave por mais tempo.")
    if f.fps < 10:
        msgs.append("Taxa de quadros baixa — feche outros apps / melhore a câmera.")
    if f.face_detection_rate < 0.6:
        msgs.append("Rosto pouco detectado — centralize o rosto na câmera.")
    if f.signal_quality < ACC_MED:
        msgs.append("Qualidade do sinal baixa — melhore a iluminação e o enquadramento.")
    ok = (f.frames >= 60 and f.fps >= 10
          and f.face_detection_rate >= 0.6 and f.signal_quality >= ACC_MED)
    return SessionValidation(ok=ok, quality=f.signal_quality, messages=msgs)
