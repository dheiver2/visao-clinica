"""Testa os sinais vitais expandidos (respiração, VFC avançada, estresse) e o
score de bem-estar — paridade com apps de vitais por câmera."""

import numpy as np

from app.clinical.wellness import compute_wellness
from app.vision import vitals
from app.vision.features import BiomarkerFeatures


def _synthetic_roi(hr_bpm, rr_bpm, fps, seconds, seed=0):
    rng = np.random.default_rng(seed)
    n = int(fps * seconds)
    t = np.arange(n) / fps
    pulse = np.sin(2 * np.pi * (hr_bpm / 60.0) * t
                   + 0.1 * np.sin(2 * np.pi * (rr_bpm / 60.0) * t))
    resp = 0.6 * np.sin(2 * np.pi * (rr_bpm / 60.0) * t)
    base = 120 + 8 * pulse + resp * 4
    r = base + 2 + 0.5 * rng.standard_normal(n)
    g = base + 3 * pulse + resp * 6 + 0.5 * rng.standard_normal(n)
    b = base * 0.8 + 0.5 * rng.standard_normal(n)
    return np.column_stack([r, g, b])


def test_vitals_recovers_hr_and_respiration():
    fps = 30.0
    roi = _synthetic_roi(hr_bpm=72.0, rr_bpm=15.0, fps=fps, seconds=15)
    v = vitals.compute(roi, fps)
    assert abs(v.heart_rate_bpm - 72.0) < 8.0
    assert abs(v.respiration_bpm - 15.0) < 4.0
    assert v.hrv_sdnn_ms > 0.0
    assert v.quality > 0.2


def test_vitals_insufficient_data():
    v = vitals.compute(np.empty((0, 3)), 30.0)
    assert v.heart_rate_bpm == 0.0
    assert v.respiration_bpm == 0.0
    assert v.stress_index == 0.0


def test_wellness_score_reliable_range():
    f = BiomarkerFeatures(
        frames=450, fps=30, signal_quality=0.85, rppg_quality=0.8,
        heart_rate_bpm=68, hrv_sdnn_ms=45, hrv_rmssd_ms=55, respiration_bpm=15,
        stress_index=120, microexpression_rate=7, blink_rate_per_min=16)
    w = compute_wellness(f)
    assert w.reliable is True
    assert 0 <= w.score <= 100
    assert 0 <= w.stress <= 100
    assert w.label in ("ótimo", "bom", "moderado", "alerta")


def test_wellness_unreliable_when_signal_poor():
    f = BiomarkerFeatures(frames=60, fps=15, signal_quality=0.2, rppg_quality=0.1)
    w = compute_wellness(f)
    assert w.reliable is False
    assert w.label == "indeterminado"
