"""Biomarcadores faciais a partir dos blendshapes (Action Units) do Face Landmarker.

Os blendshapes são intensidades de AUs medidas pela rede (0..1), muito mais
precisas que proxies geométricos. Aqui derivamos: piscar, assimetria facial,
abertura de boca (hipotonia), expressividade, hipomimia, microexpressões e olhar.

Cada série em `bs` é uma lista de valores por frame de um blendshape.
"""

from __future__ import annotations

import numpy as np

# Pares simétricos esquerda/direita (assimetria = diferença média L-R)
SYM_PAIRS = [
    ("mouthSmileLeft", "mouthSmileRight"), ("mouthFrownLeft", "mouthFrownRight"),
    ("browDownLeft", "browDownRight"), ("browOuterUpLeft", "browOuterUpRight"),
    ("cheekSquintLeft", "cheekSquintRight"), ("eyeBlinkLeft", "eyeBlinkRight"),
    ("mouthUpperUpLeft", "mouthUpperUpRight"), ("mouthLowerDownLeft", "mouthLowerDownRight"),
    ("eyeSquintLeft", "eyeSquintRight"), ("noseSneerLeft", "noseSneerRight"),
]

# AUs expressivas (para expressividade, hipomimia, microexpressões)
EXPRESSIVE = [
    "browInnerUp", "browDownLeft", "browDownRight", "browOuterUpLeft", "browOuterUpRight",
    "mouthSmileLeft", "mouthSmileRight", "mouthFrownLeft", "mouthFrownRight",
    "cheekSquintLeft", "cheekSquintRight", "noseSneerLeft", "noseSneerRight",
    "jawOpen", "mouthPucker", "eyeWideLeft", "eyeWideRight",
]


def _arr(bs, key):
    return np.asarray(bs.get(key, []), dtype=float)


def blink_rate(bs, fps, duration_s):
    """Piscadas/min pelos AUs eyeBlinkLeft/Right (limiar 0.5)."""
    l, r = _arr(bs, "eyeBlinkLeft"), _arr(bs, "eyeBlinkRight")
    n = min(l.size, r.size)
    if n < 3 or duration_s <= 0:
        return 0.0
    closed = ((l[:n] + r[:n]) / 2.0 > 0.5).astype(int)
    blinks = int(np.sum(np.diff(closed) == 1))
    return blinks / (duration_s / 60.0)


def facial_asymmetry(bs):
    """Assimetria 0..1: diferença média entre AUs esquerda/direita."""
    diffs = []
    for a, b in SYM_PAIRS:
        sa, sb = _arr(bs, a), _arr(bs, b)
        n = min(sa.size, sb.size)
        if n:
            diffs.append(float(np.mean(np.abs(sa[:n] - sb[:n]))))
    return float(np.clip(np.mean(diffs) * 2.5, 0, 1)) if diffs else 0.0


def mouth_open_ratio(bs):
    """Fração do tempo com a boca aberta (jawOpen > 0.25) — hipotonia."""
    jaw = _arr(bs, "jawOpen")
    return float((jaw > 0.25).mean()) if jaw.size else 0.0


def expression_amplitude(bs):
    """Amplitude média (desvio) das AUs expressivas."""
    stds = [_arr(bs, k).std() for k in EXPRESSIVE if _arr(bs, k).size > 1]
    return float(np.mean(stds)) if stds else 0.0


def hypomimia_index(bs):
    """Hipomimia 0..1: 1 = AUs quase imóveis (face em máscara)."""
    dyn = [float(np.mean(np.abs(np.diff(_arr(bs, k)))))
           for k in EXPRESSIVE if _arr(bs, k).size > 1]
    if not dyn:
        return 0.0
    return float(np.clip(1.0 - np.mean(dyn) / 0.03, 0, 1))


def microexpression(bs, fps, duration_s):
    """Taxa (eventos/min) e intensidade de transientes curtos (<500 ms) nas AUs."""
    if fps <= 0:
        return 0.0, 0.0
    span = max(int(0.5 * fps), 1)
    events, inten = 0, []
    for k in EXPRESSIVE:
        s = _arr(bs, k)
        if s.size < 5:
            continue
        base = float(np.median(s))
        mad = float(np.median(np.abs(s - base))) or 1e-6
        active = (np.abs(s - base) > 4 * mad).astype(int)
        for r in np.where(np.diff(active) == 1)[0]:
            seg = active[r + 1:r + 1 + span]
            if seg.size and seg.sum() <= span:
                events += 1
                peak = r + 1 + int(np.argmax(np.abs(s[r + 1:r + 1 + span] - base)))
                inten.append(abs(s[min(peak, s.size - 1)] - base) / mad)
    rate = events / (duration_s / 60.0) if duration_s else 0.0
    return rate, (float(np.mean(inten)) if inten else 0.0)


def gaze_series(bs):
    """Reconstrói (gaze_x, gaze_y) por frame a partir das AUs de olhar.

    x>0 = olhar à direita; y>0 = olhar para cima. Escala aproximada [-1, 1].
    """
    def comp(*keys):
        arrs = [_arr(bs, k) for k in keys]
        n = min((a.size for a in arrs), default=0)
        return np.sum([a[:n] for a in arrs], axis=0) / max(len(keys), 1) if n else np.array([])

    out = comp("eyeLookOutLeft", "eyeLookOutRight")
    inn = comp("eyeLookInLeft", "eyeLookInRight")
    up = comp("eyeLookUpLeft", "eyeLookUpRight")
    dn = comp("eyeLookDownLeft", "eyeLookDownRight")
    n = min(out.size, inn.size, up.size, dn.size)
    if n == 0:
        return np.array([]), np.array([])
    gx = out[:n] - inn[:n]
    gy = up[:n] - dn[:n]
    return gx, gy
