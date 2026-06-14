"""Testa as métricas de olhar e microexpressões com séries sintéticas (sem webcam)."""

import numpy as np

from app.vision.extractor import FeatureExtractor


def _extractor_with_series(series):
    ext = FeatureExtractor.__new__(FeatureExtractor)  # sem abrir webcam
    ext._series = {k: list(v) for k, v in series.items()}
    return ext


def test_saccade_detection():
    fps = 30.0
    # olhar fixo por 1s, salto rápido, fixo de novo -> ~1 saccade
    gx = [0.0] * 30 + [0.8] * 30
    gy = [0.0] * 60
    ext = _extractor_with_series({"gaze_x": gx, "gaze_y": gy})
    disp, rate = ext._gaze_metrics(fps, duration_s=2.0)
    assert rate > 0
    assert disp > 0


def test_no_saccade_when_still():
    ext = _extractor_with_series({"gaze_x": [0.0] * 60, "gaze_y": [0.0] * 60})
    disp, rate = ext._gaze_metrics(30.0, duration_s=2.0)
    assert rate == 0.0


def test_microexpression_transient_detected():
    fps = 30.0
    s = np.zeros(90)
    s[30:33] = 1.0  # pico breve de ~100 ms
    ext = _extractor_with_series({"fa_brow_raise": list(s)})
    rate, intensity = ext._microexpression_metrics(fps, duration_s=3.0)
    assert rate > 0
    assert intensity > 0


def test_sustained_expression_not_microexpression():
    # ativação longa (2s) não conta como microexpressão
    s = [0.0] * 30 + [1.0] * 60
    ext = _extractor_with_series({"fa_mouth_open": s})
    rate, _ = ext._microexpression_metrics(30.0, duration_s=3.0)
    assert rate == 0.0
