"""rPPG — fotopletismografia remota (frequência cardíaca e VFC sem contato).

Estima a frequência cardíaca (FC) e um proxy de variabilidade (VFC/SDNN) a partir
das variações sutis de cor da pele do rosto ao longo do vídeo.

Referências (revistas de alto impacto):
- Wang, den Brinker, Stuijk, de Haan. "Algorithmic Principles of Remote PPG",
  IEEE Transactions on Biomedical Engineering, 2017. (método POS, implementado aqui)
- de Haan & Jeanne. "Robust pulse rate from chrominance-based rPPG",
  IEEE TBME, 2013. (CHROM)
- Poh, McDuff, Picard. "Non-contact, automated cardiac pulse measurements using
  video imaging and blind source separation", Optics Express, 2010.

A FC/VFC autonômica é relevante para estresse/ansiedade e há literatura de
disregulação autonômica em TEA e em neurodegeneração.
"""

from __future__ import annotations

import numpy as np

try:
    from scipy.signal import find_peaks
    _SCIPY = True
except Exception:  # pragma: no cover
    _SCIPY = False

from . import signal as _sig


def pos_pulse(rgb: np.ndarray, fps: float) -> np.ndarray:
    """Sinal de pulso pelo método POS (Plane-Orthogonal-to-Skin), Wang et al. 2017.

    rgb: array (N, 3) com a cor média da ROI de pele por frame.
    """
    rgb = np.asarray(rgb, dtype=float)
    if rgb.ndim != 2 or rgb.shape[0] < 16:
        return np.zeros(max(rgb.shape[0], 0))
    n = rgb.shape[0]
    win_len = max(int(fps * 1.6), 8)  # janela ~1.6 s (Wang et al.)
    h = np.zeros(n)
    proj = np.array([[0.0, 1.0, -1.0], [-2.0, 1.0, 1.0]])
    for m in range(0, n - win_len):
        win = rgb[m:m + win_len]
        mu = win.mean(axis=0)
        mu[mu == 0] = 1e-9
        cn = win / mu                 # normalização temporal
        s = proj @ cn.T               # projeção ortogonal à pele (2 x win_len)
        std1 = s[1].std() or 1e-9
        p = s[0] + (s[0].std() / std1) * s[1]
        p = p - p.mean()
        h[m:m + win_len] += p         # overlap-add
    return h


def estimate(rgb: np.ndarray, fps: float):
    """Retorna (hr_bpm, hrv_sdnn_ms, quality 0..1) a partir da ROI de pele."""
    rgb = np.asarray(rgb, dtype=float)
    if rgb.ndim != 2 or rgb.shape[0] < int(fps * 4) or fps <= 0:
        return 0.0, 0.0, 0.0          # < ~4 s não é confiável

    pulse = pos_pulse(rgb, fps)
    pulse = _sig.bandpass(pulse, fps, 0.7, 4.0)   # 42–240 bpm
    if pulse.std() < 1e-8:
        return 0.0, 0.0, 0.0

    # FC pela frequência dominante via FFT com zero-padding (resolução fina,
    # ~1 bpm — o Welch teria bins grossos demais para FC).
    x = pulse - pulse.mean()
    nfft = max(2048, 1 << int(np.ceil(np.log2(x.size))))
    spec = np.abs(np.fft.rfft(x * np.hanning(x.size), n=nfft)) ** 2
    freqs = np.fft.rfftfreq(nfft, d=1.0 / fps)
    band = (freqs >= 0.7) & (freqs <= 4.0)
    p_band = np.where(band, spec, 0.0)
    idx = int(np.argmax(p_band))
    hr_bpm = float(freqs[idx] * 60.0)
    med = float(np.median(spec[freqs > 0])) or 1e-12
    snr = float(spec[idx] / med)
    quality = float(max(0.0, min(1.0, (snr - 2.0) / 8.0)))

    # VFC: SDNN dos intervalos entre batimentos (peak-to-peak).
    hrv = 0.0
    if _SCIPY and quality > 0.2:
        min_dist = max(int(fps * 60.0 / 200.0), 1)   # FC máx ~200 bpm
        peaks, _ = find_peaks(pulse, distance=min_dist)
        if peaks.size >= 3:
            ibi_ms = np.diff(peaks) / fps * 1000.0
            ibi_ms = ibi_ms[(ibi_ms > 300) & (ibi_ms < 1500)]
            if ibi_ms.size >= 2:
                hrv = float(np.std(ibi_ms))
    return float(hr_bpm), hrv, quality
