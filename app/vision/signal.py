"""Processamento de sinal avançado para elevar a precisão dos biomarcadores.

Técnicas:
- One-Euro filter: suavização adaptativa de landmarks (reduz jitter sem atrasar
  movimentos rápidos — melhor que média móvel para tremor/saccades).
- Hampel: rejeição robusta de outliers (picos espúrios de detecção).
- Butterworth bandpass: isola a banda fisiológica antes de medir frequência.
- Welch PSD: estimativa espectral robusta da frequência dominante + SNR, muito
  mais estável que uma única FFT (reduz falso-positivo de tremor).

Tudo opera com numpy/scipy; se o scipy faltar, há fallbacks em numpy puro.
"""

from __future__ import annotations

import numpy as np

try:
    from scipy.signal import butter, filtfilt, welch
    _SCIPY = True
except Exception:  # pragma: no cover
    _SCIPY = False


def hampel(x, window: int = 7, n_sigmas: float = 3.0):
    """Substitui outliers (|x-mediana local| > n_sigmas*MAD) pela mediana local."""
    x = np.asarray(x, dtype=float)
    if x.size < window:
        return x.copy()
    k = 1.4826  # MAD -> desvio padrão (gaussiana)
    half = window // 2
    out = x.copy()
    for i in range(x.size):
        lo, hi = max(0, i - half), min(x.size, i + half + 1)
        seg = x[lo:hi]
        med = np.median(seg)
        mad = k * np.median(np.abs(seg - med)) or 1e-9
        if abs(x[i] - med) > n_sigmas * mad:
            out[i] = med
    return out


def one_euro(x, fps: float, min_cutoff: float = 1.0, beta: float = 0.3):
    """One-Euro filter — suavização adaptativa à velocidade do sinal."""
    x = np.asarray(x, dtype=float)
    if x.size == 0 or fps <= 0:
        return x.copy()
    dt = 1.0 / fps

    def alpha(cutoff):
        tau = 1.0 / (2 * np.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    out = np.empty_like(x)
    x_prev = x[0]
    dx_prev = 0.0
    out[0] = x[0]
    for i in range(1, x.size):
        dx = (x[i] - x_prev) * fps
        a_d = alpha(1.0)
        dx_hat = a_d * dx + (1 - a_d) * dx_prev
        cutoff = min_cutoff + beta * abs(dx_hat)
        a = alpha(cutoff)
        out[i] = a * x[i] + (1 - a) * out[i - 1]
        x_prev, dx_prev = x[i], dx_hat
    return out


def detrend(x):
    """Remove tendência linear (deriva lenta de pose/iluminação)."""
    x = np.asarray(x, dtype=float)
    if x.size < 2:
        return x - x.mean() if x.size else x
    t = np.arange(x.size)
    a, b = np.polyfit(t, x, 1)
    return x - (a * t + b)


def bandpass(x, fps: float, lo: float, hi: float):
    """Filtro Butterworth passa-banda (ordem 2, zero-phase). Fallback: detrend."""
    x = np.asarray(x, dtype=float)
    nyq = fps / 2.0
    if not _SCIPY or x.size < 18 or hi >= nyq or lo <= 0:
        return detrend(x)
    b, a = butter(2, [lo / nyq, hi / nyq], btype="band")
    return filtfilt(b, a, x, padlen=min(len(x) - 1, 3 * max(len(a), len(b))))


def dominant_freq(x, fps: float, band: tuple[float, float] | None = None):
    """Frequência dominante (Hz), amplitude e SNR, via Welch (ou FFT no fallback).

    band: restringe a busca a uma faixa fisiológica (ex.: tremor 3–8 Hz).
    SNR = potência do pico / potência mediana — alto = oscilação real e limpa.
    """
    x = np.asarray(x, dtype=float)
    if x.size < 16 or fps <= 0:
        return 0.0, 0.0, 0.0
    x = detrend(x)
    if _SCIPY:
        nper = min(len(x), max(32, int(fps * 2)))
        freqs, psd = welch(x, fs=fps, nperseg=nper)
    else:
        spec = np.abs(np.fft.rfft(x)) ** 2
        freqs = np.fft.rfftfreq(x.size, d=1.0 / fps)
        psd = spec
    mask = freqs > 0
    if band:
        mask &= (freqs >= band[0]) & (freqs <= band[1])
    if not np.any(mask):
        return 0.0, 0.0, 0.0
    f_sel, p_sel = freqs[mask], psd[mask]
    idx = int(np.argmax(p_sel))
    peak_f = float(f_sel[idx])
    peak_p = float(p_sel[idx])
    med = float(np.median(psd[freqs > 0])) or 1e-12
    snr = peak_p / med
    amplitude = float(np.sqrt(peak_p))
    return peak_f, amplitude, snr


def quality_from_brightness(lum, lo: float = 55.0, hi: float = 210.0) -> float:
    """Fração de frames com luminância numa faixa adequada (0..1)."""
    lum = np.asarray(lum, dtype=float)
    if lum.size == 0:
        return 0.0
    return float(((lum >= lo) & (lum <= hi)).mean())
