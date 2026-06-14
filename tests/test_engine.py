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


def test_analyze_enriches_with_llm_and_panel():
    eng = _engine()
    feats = BiomarkerFeatures(frames=900, fps=30.0,
                              tremor_hand_hz=5.0, tremor_hand_amplitude=0.025,
                              facial_asymmetry=0.3)
    analysis = eng.analyze_features(feats)
    # painel clínico SEMPRE presente e risco derivado dele (instantâneo)
    assert analysis.conditions
    assert analysis.risk_level in ("baixo", "moderado", "alto")
    # hipóteses derivam do painel; narrativa do LLM preenche o summary
    assert analysis.hypotheses
    assert analysis.summary  # FakeBackend forneceu texto


def test_screen_is_llm_free():
    eng = ClinicalReasoningEngine()  # sem backend carregado
    feats = BiomarkerFeatures(frames=900, fps=30.0, facial_asymmetry=0.4)
    analysis = eng.screen(feats)
    assert analysis.conditions and analysis.risk_level in ("moderado", "alto")
    assert eng._backend is None  # screen() nunca carrega o modelo


def test_analyze_without_llm_still_returns_panel():
    eng = ClinicalReasoningEngine()  # sem backend
    feats = BiomarkerFeatures(frames=900, fps=30.0, facial_asymmetry=0.4)
    analysis = eng.analyze_features(feats, use_llm=False)
    assert len(analysis.conditions) >= 1
    res = {c.key: c for c in analysis.conditions}
    assert res["facial_palsy"].level in ("moderado", "alto")


def test_explain_decision():
    eng = _engine()
    eng.analyze_features(BiomarkerFeatures(frames=900, fps=30.0, tremor_hand_hz=5.2))
    assert isinstance(eng.explain_decision(), str)


def test_features_summary_excludes_series():
    feats = BiomarkerFeatures(time_series={"hand_x": [1.0, 2.0]})
    assert "time_series" not in feats.summary_text()
