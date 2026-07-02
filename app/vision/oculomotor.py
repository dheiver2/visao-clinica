"""Métricas oculomotoras avançadas (neurodegeneração e TEA).

Referências (revistas de alto impacto):
- Anderson & MacAskill. "Eye movements in patients with neurodegenerative
  disorders", Nature Reviews Neurology, 2013.
- Bahill, Clark, Stark. "The main sequence, a tool for studying human eye
  movements", Mathematical Biosciences, 1975. (main sequence)
- Crawford et al. "Inhibitory control of saccadic eye movements and cognitive
  impairment in Alzheimer's disease", Biological Psychiatry, 2005.
- BCEA (Bivariate Contour Ellipse Area): Steinman 1965; Castet & Crossland 2012
  — padrão de estabilidade de fixação.
"""

from __future__ import annotations

import numpy as np


def fixation_bcea(gx, gy, p: float = 0.68) -> float:
    """Bivariate Contour Ellipse Area — área que contém p% das fixações.

    Menor BCEA = fixação mais estável. Instabilidade está associada a
    comprometimento cognitivo (Anderson & MacAskill, 2013).
    """
    gx = np.asarray(gx, dtype=float)
    gy = np.asarray(gy, dtype=float)
    if gx.size < 8:
        return 0.0
    sx, sy = gx.std(), gy.std()
    rho = float(np.corrcoef(gx, gy)[0, 1]) if sx > 0 and sy > 0 else 0.0
    rho = 0.0 if np.isnan(rho) else rho
    k = -np.log(1.0 - p)              # fator para a fração p (dist. qui-quadrado, 2 g.l.)
    return float(2.0 * k * np.pi * sx * sy * np.sqrt(max(1e-9, 1.0 - rho ** 2)))


def main_sequence_slope(gx, gy, fps: float, vel_thresh: float = 2.0):
    """Inclinação da 'main sequence' (pico de velocidade × amplitude de saccade).

    Saccades mais lentas para a mesma amplitude (slope menor) ocorrem em
    distúrbios do movimento e neurodegeneração (Bahill et al., 1975;
    Anderson & MacAskill, 2013). Retorna (slope, n_saccades).
    """
    gx = np.asarray(gx, dtype=float)
    gy = np.asarray(gy, dtype=float)
    if gx.size < 8 or fps <= 0:
        return 0.0, 0
    vel = np.hypot(np.diff(gx), np.diff(gy)) * fps
    active = vel > vel_thresh
    amps, peaks = [], []
    i, n = 0, active.size
    while i < n:
        if active[i]:
            j = i
            while j < n and active[j]:
                j += 1
            amp = float(np.hypot(gx[i:j + 1][-1] - gx[i:j + 1][0],
                                 gy[i:j + 1][-1] - gy[i:j + 1][0]))
            pv = float(vel[i:j].max()) if j > i else 0.0
            if amp > 1e-3:
                amps.append(amp)
                peaks.append(pv)
            i = j + 1
        else:
            i += 1
    if len(amps) < 2:
        return 0.0, len(amps)
    slope = float(np.polyfit(amps, peaks, 1)[0])
    return slope, len(amps)
