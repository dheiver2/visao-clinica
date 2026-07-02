"""Testa a validação de sessão e o gating por acurácia (média/alta)."""

from app.clinical.reasoning_engine import ClinicalReasoningEngine
from app.clinical.validation import accuracy_band, is_displayable, validate_session
from app.vision.features import BiomarkerFeatures


def test_accuracy_bands():
    assert accuracy_band(0.9) == "alta"
    assert accuracy_band(0.5) == "média"
    assert accuracy_band(0.2) == "baixa"
    assert is_displayable(0.5) and not is_displayable(0.2)


def test_good_session_is_valid():
    f = BiomarkerFeatures(frames=360, fps=30.0, face_detection_rate=0.95,
                          signal_quality=0.9)
    v = validate_session(f)
    assert v.ok and not v.messages


def test_bad_session_invalid_with_messages():
    f = BiomarkerFeatures(frames=20, fps=4.0, face_detection_rate=0.3,
                          signal_quality=0.1)
    v = validate_session(f)
    assert not v.ok and len(v.messages) >= 3


def test_low_quality_hides_all_conditions():
    # Sinal ruim -> confiança baixa -> nada exibível.
    f = BiomarkerFeatures(frames=360, fps=30.0, facial_asymmetry=0.4,
                          signal_quality=0.15, face_detection_rate=0.4)
    analysis = ClinicalReasoningEngine().screen(f)
    assert analysis.displayable_conditions == []


def test_good_quality_shows_conditions():
    f = BiomarkerFeatures(frames=360, fps=30.0, facial_asymmetry=0.4,
                          signal_quality=0.9, face_detection_rate=0.95)
    analysis = ClinicalReasoningEngine().screen(f)
    assert analysis.displayable_conditions
    assert all(c.confidence >= 0.4 for c in analysis.displayable_conditions)
