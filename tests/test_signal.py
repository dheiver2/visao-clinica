"""Testa o processamento de sinal avançado (precisão dos biomarcadores)."""

import numpy as np

from app.vision import signal


def test_dominant_freq_recovers_known_tone():
    fps = 30.0
    t = np.arange(0, 6, 1 / fps)
    x = np.sin(2 * np.pi * 5.0 * t)            # tremor sintético de 5 Hz
    f, amp, snr = signal.dominant_freq(x, fps, band=(3.0, 8.0))
    assert abs(f - 5.0) < 0.6
    assert snr > 5.0                            # tom puro -> SNR alto


def test_dominant_freq_noise_low_snr():
    fps = 30.0
    rng = np.random.default_rng(0)
    x = rng.standard_normal(180)               # ruído branco
    f, amp, snr = signal.dominant_freq(x, fps, band=(3.0, 8.0))
    assert snr < 5.0                            # sem pico claro


def test_hampel_removes_spike():
    x = np.ones(50)
    x[25] = 100.0
    out = signal.hampel(x)
    assert abs(out[25] - 1.0) < 1e-6


def test_one_euro_reduces_jitter():
    fps = 30.0
    rng = np.random.default_rng(1)
    base = np.linspace(0, 1, 150)
    noisy = base + rng.normal(0, 0.05, 150)
    sm = signal.one_euro(noisy, fps, min_cutoff=0.5, beta=0.0)
    assert np.std(np.diff(sm)) < np.std(np.diff(noisy))


def test_quality_from_brightness():
    assert signal.quality_from_brightness([120] * 10) == 1.0
    assert signal.quality_from_brightness([5] * 10) == 0.0
