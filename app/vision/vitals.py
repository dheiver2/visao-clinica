"""Sinais vitais expandidos por rPPG — paridade com apps de vitais por webcam.

Do mesmo sinal de pulso rPPG (POS, ver ``rppg.py``) já usado para a frequência
cardíaca, deriva o conjunto de métricas que produtos comerciais de "vitais por
câmera" (Binah.ai, NuraLogix Anura, MX Labs shen.ai, Vastmindz) destacam:

- Frequência respiratória (rpm) — modulação respiratória lenta da pele (RIIV).
- VFC no domínio do tempo: SDNN, RMSSD, pNN50.
- VFC no domínio da frequência: razão LF/HF (balanço autonômico simpato-vagal).
- Índice de estresse de Baevsky (SI) — sensível a estresse via histograma de
  intervalos entre batimentos.

Tudo determinístico, offline, sem dependências além de numpy/scipy.

Referências (revistas de alto impacto):
- Task Force ESC/NASPE. "Heart rate variability: standards of measurement,
  physiological interpretation and clinical use", Circulation 1996.
  (SDNN, RMSSD, pNN50, LF/HF)
- Baevsky & Chernikova. "Heart rate variability analysis: physiological
  foundations and main methods", Cardiometry 2017. (índice de estresse SI)
- Wang, den Brinker, Stuijk, de Haan. "Algorithmic Principles of Remote PPG",
  IEEE TBME 2017. (sinal de pulso POS, base — ver rppg.py)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from . import rppg
from . import signal as _sig

try:
    from scipy.signal import find_peaks, welch
    _SCIPY = True
except Exception:  # pragma: no cover
    _SCIPY = False


@dataclass
class Vitals:
    """Sinais vitais estimados sem contato numa sessão de captura."""

    heart_rate_bpm: float = 0.0
    respiration_bpm: float = 0.0
    hrv_sdnn_ms: float = 0.0
    hrv_rmssd_ms: float = 0.0
    hrv_pnn50: float = 0.0          # 0..1 (fração de |ΔIBI| > 50 ms)
    lf_hf_ratio: float = 0.0
    stress_index: float = 0.0      # índice de Baevsky (repouso ~50–150)
    quality: float = 0.0           # confiabilidade do sinal rPPG (0..1)


def _ibi_ms(pulse: np.ndarray, fps: float) -> np.ndarray:
    """Intervalos entre batimentos (ms) a partir dos picos do pulso."""
    if not _SCIPY:
        return np.empty(0)
    min_dist = max(int(fps * 60.0 / 200.0), 1)   # FC máx ~200 bpm
    peaks, _ = find_peaks(pulse, distance=min_dist)
    if peaks.size < 3:
        return np.empty(0)
    ibi = np.diff(peaks) / fps * 1000.0
    return ibi[(ibi > 300) & (ibi < 1500)]        # 40–200 bpm plausíveis


def _time_domain(ibi: np.ndarray) -> tuple[float, float, float]:
    """SDNN, RMSSD e pNN50 dos intervalos entre batimentos."""
    if ibi.size < 2:
        return 0.0, 0.0, 0.0
    sdnn = float(np.std(ibi))
    diff = np.diff(ibi)
    if diff.size == 0:
        return sdnn, 0.0, 0.0
    rmssd = float(np.sqrt(np.mean(diff ** 2)))
    pnn50 = float(np.mean(np.abs(diff) > 50.0))
    return sdnn, rmssd, pnn50


def _freq_domain(ibi: np.ndarray) -> float:
    """Razão LF/HF via PSD (Welch) do tacograma reamostrado a 4 Hz.

    LF = 0.04–0.15 Hz (simpático+vagal), HF = 0.15–0.40 Hz (vagal/respiratório).
    A razão é adimensional e independe da escala do PSD.
    """
    if not _SCIPY or ibi.size < 8:
        return 0.0
    t = np.cumsum(ibi) / 1000.0                    # instantes dos batimentos (s)
    fs_i = 4.0
    tt = np.arange(float(t[0]), float(t[-1]), 1.0 / fs_i)
    if tt.size < 16:
        return 0.0
    tach = np.interp(tt, t, ibi)
    tach = tach - tach.mean()
    freqs, psd = welch(tach, fs=fs_i, nperseg=min(len(tach), 128))
    lf = float(psd[(freqs >= 0.04) & (freqs < 0.15)].sum())
    hf = float(psd[(freqs >= 0.15) & (freqs < 0.40)].sum())
    return lf / hf if hf > 1e-9 else 0.0


def _stress_index(ibi: np.ndarray) -> float:
    """Índice de estresse de Baevsky: SI = AMo / (2·Mo·MxDMn).

    Mo (moda dos IBIs) e MxDMn (amplitude de variação) em segundos; AMo é a % de
    IBIs no bin modal (50 ms). Repouso ~50–150; estresse elevado > 500.
    """
    if ibi.size < 5:
        return 0.0
    lo, hi = float(ibi.min()), float(ibi.max())
    if hi - lo < 1e-6:
        return 0.0
    bins = np.arange(lo, hi + 50.0, 50.0)
    if bins.size < 2:
        return 0.0
    hist, edges = np.histogram(ibi, bins=bins)
    k = int(np.argmax(hist))
    mo = (edges[k] + edges[k + 1]) / 2.0 / 1000.0        # s
    amo = 100.0 * hist[k] / ibi.size                     # %
    mxdmn = (hi - lo) / 1000.0                            # s
    if mo <= 0 or mxdmn <= 0:
        return 0.0
    return float(amo / (2.0 * mo * mxdmn))


def _respiration_bpm(roi: np.ndarray, fps: float) -> float:
    """Frequência respiratória (rpm) pela modulação lenta da pele (RIIV).

    Isola a banda 0.1–0.5 Hz (≈6–30 rpm) do canal verde e busca o pico espectral
    dominante por FFT com zero-padding — resolução fina (~0.1 rpm), essencial em
    frequências baixas (o Welch teria bins grossos demais). Repouso: 12–20 rpm.
    """
    if roi.ndim != 2 or roi.shape[0] == 0:
        return 0.0
    g = np.asarray(roi[:, 1], dtype=float)
    if g.size < int(fps * 8):        # < ~8 s não é confiável p/ respiração
        return 0.0
    x = _sig.bandpass(g, fps, 0.1, 0.5)
    x = x - x.mean()
    if x.std() < 1e-9:
        return 0.0
    nfft = max(4096, 1 << int(np.ceil(np.log2(x.size))))
    spec = np.abs(np.fft.rfft(x * np.hanning(x.size), n=nfft)) ** 2
    freqs = np.fft.rfftfreq(nfft, d=1.0 / fps)
    band = (freqs >= 0.1) & (freqs <= 0.5)
    if not np.any(band):
        return 0.0
    idx = int(np.argmax(np.where(band, spec, 0.0)))
    med = float(np.median(spec[freqs > 0])) or 1e-12
    if spec[idx] / med < 3.0:        # exige pico respiratório destacado
        return 0.0
    return float(freqs[idx] * 60.0)


def compute(roi, fps: float) -> Vitals:
    """Estima todos os sinais vitais a partir da série de cor da pele (ROI)."""
    roi = np.asarray(roi, dtype=float)
    v = Vitals()
    if roi.ndim != 2 or roi.shape[0] < int(fps * 4) or fps <= 0:
        return v

    pulse = rppg.pos_pulse(roi, fps)
    pulse = _sig.bandpass(pulse, fps, 0.7, 4.0)   # 42–240 bpm
    if pulse.std() < 1e-8:
        return v

    hr, sdnn0, q = rppg.estimate(roi, fps)        # FC + qualidade (mesma base)
    v.heart_rate_bpm = hr
    v.quality = q

    ibi = _ibi_ms(pulse, fps) if q > 0.2 else np.empty(0)
    v.hrv_sdnn_ms, v.hrv_rmssd_ms, v.hrv_pnn50 = _time_domain(ibi)
    if v.hrv_sdnn_ms == 0.0:
        v.hrv_sdnn_ms = sdnn0                      # cai p/ o SDNN do rppg
    v.lf_hf_ratio = _freq_domain(ibi)
    v.stress_index = _stress_index(ibi)
    v.respiration_bpm = _respiration_bpm(roi, fps)
    return v
