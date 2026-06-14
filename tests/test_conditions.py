"""Testa o painel clínico determinístico (saída garantida por doença)."""

from app.clinical.conditions import PANEL, evaluate_conditions
from app.vision.features import BiomarkerFeatures


def test_always_one_result_per_condition():
    f = BiomarkerFeatures(frames=900, fps=30.0)
    results = evaluate_conditions(f)
    assert len(results) == len(PANEL)
    keys = {r.key for r in results}
    assert keys == {k for k, _, _ in PANEL}


def test_insufficient_data_is_indeterminate():
    f = BiomarkerFeatures(frames=3)
    results = evaluate_conditions(f)
    assert all(r.level == "indeterminado" for r in results)


def test_parkinsonian_tremor_detected():
    f = BiomarkerFeatures(frames=900, fps=30.0,
                          tremor_hand_hz=5.0, tremor_hand_amplitude=0.025)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["parkinsonian_tremor"].level in ("moderado", "alto")
    assert res["parkinsonian_tremor"].factors


def test_facial_palsy_detected():
    f = BiomarkerFeatures(frames=900, fps=30.0, facial_asymmetry=0.4)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["facial_palsy"].level in ("moderado", "alto")


def test_low_signal_is_low_risk():
    f = BiomarkerFeatures(frames=900, fps=30.0, blink_rate_per_min=16.0,
                          microexpression_rate=4.0, body_movement_index=0.05)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["parkinsonian_tremor"].level == "baixo"


def test_scores_sorted_desc():
    f = BiomarkerFeatures(frames=900, fps=30.0, facial_asymmetry=0.4)
    results = evaluate_conditions(f)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
