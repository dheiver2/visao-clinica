"""Testa os biomarcadores derivados de blendshapes (Action Units)."""

import numpy as np

from app.vision import blendshape_features as bf


def test_blink_rate_counts_closures():
    fps = 30.0
    # 3 piscadas: AU sobe acima de 0.5 três vezes
    s = np.zeros(300)
    for c in (50, 150, 250):
        s[c:c + 4] = 0.9
    bs = {"eyeBlinkLeft": list(s), "eyeBlinkRight": list(s)}
    rate = bf.blink_rate(bs, fps, duration_s=10.0)
    assert 15 < rate < 21          # 3 piscadas em 10s -> 18/min


def test_facial_asymmetry_from_blendshapes():
    n = 100
    sym = {"mouthSmileLeft": [0.5] * n, "mouthSmileRight": [0.5] * n}
    asym = {"mouthSmileLeft": [0.8] * n, "mouthSmileRight": [0.1] * n}
    assert bf.facial_asymmetry(sym) < bf.facial_asymmetry(asym)


def test_mouth_open_ratio():
    bs = {"jawOpen": [0.0] * 50 + [0.6] * 50}
    assert abs(bf.mouth_open_ratio(bs) - 0.5) < 0.01


def test_hypomimia_high_for_static_aus():
    static = {k: [0.5] * 120 for k in ("browInnerUp", "mouthSmileLeft", "jawOpen")}
    t = np.linspace(0, 20, 120)
    dynamic = {k: list(0.5 + 0.1 * np.sin(t)) for k in ("browInnerUp", "mouthSmileLeft", "jawOpen")}
    assert bf.hypomimia_index(static) > bf.hypomimia_index(dynamic)


def test_microexpression_detects_transient():
    s = np.zeros(120); s[40:43] = 0.6
    bs = {"browInnerUp": list(s)}
    rate, inten = bf.microexpression(bs, fps=30.0, duration_s=4.0)
    assert rate > 0 and inten > 0


def test_gaze_series_direction():
    n = 60
    bs = {"eyeLookOutLeft": [0.8] * n, "eyeLookOutRight": [0.8] * n,
          "eyeLookInLeft": [0.0] * n, "eyeLookInRight": [0.0] * n,
          "eyeLookUpLeft": [0.0] * n, "eyeLookUpRight": [0.0] * n,
          "eyeLookDownLeft": [0.0] * n, "eyeLookDownRight": [0.0] * n}
    gx, gy = bf.gaze_series(bs)
    assert gx.size == n and gx.mean() > 0.5
