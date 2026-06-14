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
    f = BiomarkerFeatures(frames=900, fps=30.0, tremor_snr=10.0,
                          tremor_hand_hz=5.0, tremor_hand_amplitude=0.025)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["parkinsonian_tremor"].level in ("moderado", "alto")
    assert res["parkinsonian_tremor"].factors


def test_tremor_rejected_when_low_snr():
    # Mesma frequência/amplitude, mas SNR baixo (ruído) -> não conta como tremor.
    f = BiomarkerFeatures(frames=900, fps=30.0, tremor_snr=1.0,
                          tremor_hand_hz=5.0, tremor_hand_amplitude=0.025)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["parkinsonian_tremor"].level == "baixo"


def test_low_signal_quality_reduces_confidence():
    f = BiomarkerFeatures(frames=900, fps=30.0, facial_asymmetry=0.4,
                          signal_quality=0.2)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["facial_palsy"].confidence < 0.5


def test_facial_palsy_detected():
    f = BiomarkerFeatures(frames=900, fps=30.0, facial_asymmetry=0.4)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["facial_palsy"].level in ("moderado", "alto")


def test_low_signal_is_low_risk():
    f = BiomarkerFeatures(frames=900, fps=30.0, blink_rate_per_min=16.0,
                          microexpression_rate=4.0, body_movement_index=0.05)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["parkinsonian_tremor"].level == "baixo"


def test_panel_includes_target_disorders():
    keys = {k for k, _, _ in PANEL}
    for k in ("autism_signs", "parkinson_composite", "alzheimer_signs", "down_signs"):
        assert k in keys


def test_autism_signs_detected():
    f = BiomarkerFeatures(frames=900, fps=30.0, gaze_center_ratio=0.1,
                          microexpression_rate=1.0, movement_periodicity=0.4,
                          body_movement_index=0.2, saccade_rate=210)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["autism_signs"].level in ("moderado", "alto")
    assert res["autism_signs"].factors


def test_parkinson_composite_detected():
    f = BiomarkerFeatures(frames=900, fps=30.0, tremor_hand_hz=5.0, tremor_snr=10.0,
                          tremor_hand_amplitude=0.025, microexpression_rate=1.0,
                          blink_rate_per_min=6.0, body_movement_index=0.005)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["parkinson_composite"].level in ("moderado", "alto")


def test_alzheimer_signs_detected():
    f = BiomarkerFeatures(frames=900, fps=30.0, gaze_dispersion=0.38,
                          gaze_center_ratio=0.1, saccade_rate=210,
                          microexpression_rate=1.0)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["alzheimer_signs"].level in ("moderado", "alto")


def test_down_signs_detected():
    f = BiomarkerFeatures(frames=900, fps=30.0, mouth_open_ratio=0.6,
                          expression_amplitude=0.002, body_movement_index=0.005)
    res = {r.key: r for r in evaluate_conditions(f)}
    assert res["down_signs"].level in ("moderado", "alto")


def test_healthy_baseline_low_for_disorders():
    # Perfil típico/saudável não deve disparar os transtornos-alvo.
    f = BiomarkerFeatures(frames=900, fps=30.0, gaze_center_ratio=0.8,
                          microexpression_rate=8.0, blink_rate_per_min=16.0,
                          body_movement_index=0.05, gaze_dispersion=0.05,
                          saccade_rate=60, mouth_open_ratio=0.05,
                          expression_amplitude=0.05, movement_periodicity=0.1)
    res = {r.key: r for r in evaluate_conditions(f)}
    for k in ("autism_signs", "parkinson_composite", "alzheimer_signs", "down_signs"):
        assert res[k].level == "baixo"


def test_scores_sorted_desc():
    f = BiomarkerFeatures(frames=900, fps=30.0, facial_asymmetry=0.4)
    results = evaluate_conditions(f)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)
