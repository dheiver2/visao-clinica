"""Testes do ClinicalReasoningEngine usando um backend LLM falso (offline)."""

from app.clinical.reasoning_engine import ClinicalReasoningEngine
from app.vision.features import BiomarkerFeatures


class FakeBackend:
    name = "fake"

    def generate(self, prompt, max_tokens=512, temperature=0.7):
        return (
            '{"summary": "ok", "hypotheses": ["h1"], '
            '"influential_variables": ["tremor_hand_hz"], "risk_level": "moderado"}'
        )


def _engine():
    eng = ClinicalReasoningEngine()
    eng._backend = FakeBackend()  # injeta backend sem carregar modelo real
    return eng


def test_analyze_parses_json():
    eng = _engine()
    feats = BiomarkerFeatures(tremor_hand_hz=5.2, facial_asymmetry=0.3)
    analysis = eng.analyze_features(feats)
    assert analysis.risk_level == "moderado"
    assert analysis.hypotheses == ["h1"]
    assert "tremor_hand_hz" in analysis.influential_variables


def test_explain_decision():
    eng = _engine()
    eng.analyze_features(BiomarkerFeatures(tremor_hand_hz=5.2))
    assert isinstance(eng.explain_decision(), str)


def test_features_summary_excludes_series():
    feats = BiomarkerFeatures(time_series={"hand_x": [1.0, 2.0]})
    assert "time_series" not in feats.summary_text()
