"""Testa o relatório agregado e anonimizado por setor (NR-01)."""

from app.clinical.nr01 import assess_psychosocial
from app.clinical.nr01_aggregate import aggregate
from app.vision.features import BiomarkerFeatures


def _high_stress():
    return assess_psychosocial(BiomarkerFeatures(
        frames=360, fps=30, microexpression_rate=18, blink_rate_per_min=46,
        hrv_sdnn_ms=12, rppg_quality=0.9, body_movement_index=0.005))


def _low():
    return assess_psychosocial(BiomarkerFeatures(
        frames=360, fps=30, microexpression_rate=4, blink_rate_per_min=16,
        hrv_sdnn_ms=60, rppg_quality=0.8, body_movement_index=0.05))


def test_empty_sample():
    rep = aggregate("TI", sessions=[])
    assert rep.n == 0 and rep.by_factor == {}


def test_percentages_sum_per_factor():
    sessions = [_high_stress(), _high_stress(), _low()]
    rep = aggregate("Operações", sessions=sessions)
    assert rep.n == 3
    for _fator, dist in rep.by_factor.items():
        assert abs(sum(dist.values()) - 100.0) < 0.5


def test_overall_distribution_and_priority():
    sessions = [_high_stress(), _high_stress(), _low()]
    rep = aggregate("Vendas", sessions=sessions)
    assert abs(sum(rep.overall_dist.values()) - 100.0) < 0.5
    # estresse aparece como prioritário quando há % alto
    assert any("Estresse" in p for p in rep.priority)


def test_anonymized_only_levels():
    # o agregado não deve conter biometria — só níveis derivados
    rep = aggregate("RH", sessions=[_high_stress()])
    assert set(next(iter(rep.by_factor.values())).keys()) == {"baixo", "moderado", "alto"}
