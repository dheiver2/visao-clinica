"""Testa o módulo ocupacional NR-01 (riscos psicossociais + plano de ação)."""

from app.clinical.nr01 import (
    action_plan, assess_psychosocial, overall_risk, PSYCH_PANEL,
)
from app.vision.features import BiomarkerFeatures


def test_one_indicator_per_factor():
    f = BiomarkerFeatures(frames=360, fps=30.0)
    ind = assess_psychosocial(f)
    assert len(ind) == len(PSYCH_PANEL)


def test_insufficient_data_indeterminate():
    f = BiomarkerFeatures(frames=3)
    ind = assess_psychosocial(f)
    assert all(i.level == "indeterminado" for i in ind)


def test_high_stress_detected():
    f = BiomarkerFeatures(frames=360, fps=30.0, microexpression_rate=18,
                          blink_rate_per_min=46, hrv_sdnn_ms=15, rppg_quality=0.8)
    ind = {i.key: i for i in assess_psychosocial(f)}
    assert ind["estresse"].level in ("moderado", "alto")


def test_panel_has_eight_factors():
    assert len(PSYCH_PANEL) == 8
    keys = {k for k, _, _ in PSYCH_PANEL}
    for k in ("ansiedade", "autonomico", "carga_mental", "agitacao"):
        assert k in keys


def test_ansiedade_detected():
    f = BiomarkerFeatures(frames=360, fps=30.0, blink_rate_per_min=46,
                          gaze_dispersion=0.38, saccade_rate=210)
    ind = {i.key: i for i in assess_psychosocial(f)}
    assert ind["ansiedade"].level in ("moderado", "alto")


def test_autonomico_detected():
    f = BiomarkerFeatures(frames=360, fps=30.0, hrv_sdnn_ms=12,
                          heart_rate_bpm=105, rppg_quality=0.9)
    ind = {i.key: i for i in assess_psychosocial(f)}
    assert ind["autonomico"].level in ("moderado", "alto")


def test_agitacao_detected():
    f = BiomarkerFeatures(frames=360, fps=30.0, body_movement_index=0.28,
                          stereotypy_index=0.55)
    ind = {i.key: i for i in assess_psychosocial(f)}
    assert ind["agitacao"].level in ("moderado", "alto")


def test_action_plan_structure():
    f = BiomarkerFeatures(frames=360, fps=30.0, microexpression_rate=18,
                          blink_rate_per_min=46, hrv_sdnn_ms=12, rppg_quality=0.9,
                          body_movement_index=0.005)
    ind = assess_psychosocial(f)
    plan = action_plan(ind)
    fases = [p["fase"] for p in plan]
    assert any("Identificação" in x for x in fases)
    assert any("Monitoramento" in x for x in fases)
    # com risco alto, há a fase 0 de ação imediata
    if overall_risk(ind) == "alto":
        assert any("imediata" in x.lower() for x in fases)


def test_low_risk_no_immediate_phase():
    f = BiomarkerFeatures(frames=360, fps=30.0, microexpression_rate=4,
                          blink_rate_per_min=16, hrv_sdnn_ms=60, rppg_quality=0.8,
                          body_movement_index=0.05)
    plan = action_plan(assess_psychosocial(f))
    assert not any("imediata" in p["fase"].lower() for p in plan)
