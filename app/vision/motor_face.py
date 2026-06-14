"""Hipomimia facial (FACS) e estereotipias motoras.

Referências (revistas de alto impacto):
- Bandini et al. "Analysis of facial expressions in Parkinson's disease through
  video-based automatic methods", Journal of Neuroscience Methods, 2017.
  (hipomimia = redução da dinâmica de Action Units)
- Ekman & Friesen. Facial Action Coding System (FACS), 1978.
- Baltrušaitis et al. "OpenFace 2.0: Facial Behavior Analysis Toolkit", IEEE FG 2018.
- Goodwin et al. "Automated detection of stereotypical motor movements",
  Journal of Autism and Developmental Disorders, 2011. (estereotipias por padrão
  repetitivo do sinal de movimento)
"""

from __future__ import annotations

import numpy as np


def hypomimia_index(au_channels: list[np.ndarray]) -> float:
    """Índice de hipomimia 0..1: 1 = face praticamente imóvel (em máscara).

    Mede a redução da dinâmica das Action Units (variabilidade temporal média).
    Em Parkinson, a dinâmica facial é reduzida (Bandini et al., 2017).
    """
    if not au_channels:
        return 0.0
    dyn = []
    for s in au_channels:
        s = np.asarray(s, dtype=float)
        if s.size > 1:
            dyn.append(float(np.mean(np.abs(np.diff(s)))))
    if not dyn:
        return 0.0
    mean_dyn = float(np.mean(dyn))
    # Mapeia dinâmica baixa -> índice alto (escala empírica, normalizada por IOD).
    return float(max(0.0, min(1.0, 1.0 - mean_dyn / 0.01)))


def stereotypy_index(motion, fps: float) -> float:
    """Índice de estereotipia 0..1 via autocorrelação do sinal de movimento.

    Movimentos repetitivos (estereotipias) produzem um pico de autocorrelação em
    lag não-nulo (Goodwin et al., 2011). Retorna a força desse pico.
    """
    x = np.asarray(motion, dtype=float)
    if x.size < int(fps) + 4 or fps <= 0:
        return 0.0
    x = x - x.mean()
    if x.std() < 1e-9:
        return 0.0
    ac = np.correlate(x, x, mode="full")[x.size - 1:]
    ac = ac / ac[0]
    lo = max(int(fps * 0.3), 2)        # ignora lag ~0; busca período 0.3–3 s
    hi = min(int(fps * 3.0), ac.size - 1)
    if hi <= lo:
        return 0.0
    return float(max(0.0, min(1.0, ac[lo:hi].max())))
