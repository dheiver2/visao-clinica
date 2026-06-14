"""Testa os biomarcadores avançados (rPPG, oculomotor, hipomimia, estereotipia)."""

import numpy as np

from app.vision import motor_face, oculomotor, rppg


def _synthetic_skin(hr_bpm, fps, seconds, seed=0):
    rng = np.random.default_rng(seed)
    n = int(fps * seconds)
    t = np.arange(n) / fps
    pulse = np.sin(2 * np.pi * (hr_bpm / 60.0) * t)
    base = np.array([180.0, 120.0, 100.0])           # cor de pele média
    # pulso modula sobretudo o canal verde (mais sensível ao volume sanguíneo)
    mod = np.outer(pulse, np.array([0.3, 1.0, 0.4]))
    noise = rng.normal(0, 0.2, (n, 3))
    return base + mod + noise


def test_rppg_recovers_heart_rate():
    fps = 30.0
    roi = _synthetic_skin(hr_bpm=72.0, fps=fps, seconds=12)
    hr, hrv, q = rppg.estimate(roi, fps)
    assert abs(hr - 72.0) < 8.0          # dentro de ~8 bpm
    assert q > 0.2


def test_rppg_insufficient_data():
    hr, hrv, q = rppg.estimate(np.empty((0, 3)), 30.0)
    assert hr == 0.0 and q == 0.0


def test_bcea_smaller_for_stable_fixation():
    rng = np.random.default_rng(0)
    stable = (rng.normal(0, 0.02, 200), rng.normal(0, 0.02, 200))
    unstable = (rng.normal(0, 0.2, 200), rng.normal(0, 0.2, 200))
    assert oculomotor.fixation_bcea(*stable) < oculomotor.fixation_bcea(*unstable)


def test_main_sequence_detects_saccades():
    fps = 30.0
    gx = np.concatenate([np.zeros(30), np.linspace(0, 0.8, 3), np.full(30, 0.8)])
    gy = np.zeros(gx.size)
    slope, n = oculomotor.main_sequence_slope(gx, gy, fps)
    assert n >= 1


def test_hypomimia_index_high_for_static_face():
    static = [np.full(120, 0.5)]                     # face imóvel
    dynamic = [0.5 + 0.05 * np.sin(np.linspace(0, 20, 120))]
    assert motor_face.hypomimia_index(static) > motor_face.hypomimia_index(dynamic)


def test_stereotypy_index_high_for_periodic_motion():
    fps = 30.0
    t = np.arange(int(fps * 6)) / fps
    periodic = np.sin(2 * np.pi * 1.0 * t)           # 1 Hz repetitivo
    rng = np.random.default_rng(0)
    random_motion = rng.standard_normal(t.size)
    assert (motor_face.stereotypy_index(periodic, fps)
            > motor_face.stereotypy_index(random_motion, fps))
