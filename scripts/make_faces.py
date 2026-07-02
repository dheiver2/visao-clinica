"""Gera galeria de rostos diversos + GIF animado da malha de landmarks.

Saídas: docs/assets/face_var{1,2,3}.png e docs/assets/face_scan.gif
"""
import numpy as np
from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication
from scipy.spatial import Delaunay

app = QApplication([])


def pen(color, w, cap=Qt.SquareCap):
    return QPen(QColor(color), w, Qt.SolidLine, cap)


def _mesh_points(cx, cy, fw, fh, seed, jitter=0.0):
    rng = np.random.default_rng(seed)
    pts = []
    for a in np.linspace(0, 2 * np.pi, 46, endpoint=False):
        pts.append((cx + fw * np.cos(a) * 0.98, cy + fh * np.sin(a) * 0.98))
    for _ in range(150):
        x = rng.uniform(cx - fw, cx + fw); y = rng.uniform(cy - fh, cy + fh)
        if ((x - cx) / fw) ** 2 + ((y - cy) / fh) ** 2 < 0.92:
            pts.append((x, y))
    for ex in (cx - fw * 0.33, cx + fw * 0.33):
        for a in np.linspace(0, 2 * np.pi, 9, endpoint=False):
            pts.append((ex + fw * 0.17 * np.cos(a), cy - fh * 0.17 + fh * 0.08 * np.sin(a)))
    P = np.array(pts)
    if jitter:
        P = P + rng.normal(0, jitter, P.shape)
    return P


def draw_face(p, cx, cy, fw, fh, skin, hair, lip, seed=7, jitter=0.0,
              mesh_alpha=90, dot_alpha=230, with_hair=True):
    # pele
    sk = QRadialGradient(cx, cy - 20, fh * 1.2)
    sk.setColorAt(0, QColor(skin[0])); sk.setColorAt(0.7, QColor(skin[1])); sk.setColorAt(1, QColor(skin[2]))
    p.setPen(Qt.NoPen); p.setBrush(QBrush(sk)); p.drawEllipse(QPointF(cx, cy), fw, fh)
    # cabelo
    if with_hair:
        p.setBrush(QColor(hair))
        h = QPainterPath(); h.moveTo(cx - fw - 4, cy - fh * 0.15)
        h.quadTo(cx - fw - 14, cy - fh - 28, cx, cy - fh - 20)
        h.quadTo(cx + fw + 14, cy - fh - 28, cx + fw + 4, cy - fh * 0.15)
        h.quadTo(cx + fw - 22, cy - fh + 28, cx, cy - fh + 22)
        h.quadTo(cx - fw + 22, cy - fh + 28, cx - fw - 4, cy - fh * 0.15)
        p.drawPath(h)
    # sobrancelhas
    p.setPen(pen(hair, max(fh * 0.035, 4), Qt.RoundCap))
    p.drawLine(int(cx - fw * 0.52), int(cy - fh * 0.30), int(cx - fw * 0.17), int(cy - fh * 0.34))
    p.drawLine(int(cx + fw * 0.17), int(cy - fh * 0.34), int(cx + fw * 0.52), int(cy - fh * 0.30))
    # olhos
    for ex in (cx - fw * 0.33, cx + fw * 0.33):
        p.setPen(Qt.NoPen); p.setBrush(QColor('#f4f1ec')); p.drawEllipse(QPointF(ex, cy - fh * 0.17), fw * 0.17, fh * 0.08)
        p.setBrush(QColor('#5a3d2b')); p.drawEllipse(QPointF(ex, cy - fh * 0.17), fw * 0.07, fw * 0.07)
        p.setBrush(QColor('#1a120c')); p.drawEllipse(QPointF(ex, cy - fh * 0.17), fw * 0.033, fw * 0.033)
    # nariz
    p.setPen(pen(skin[2], max(fw * 0.026, 3), Qt.RoundCap)); p.setBrush(Qt.NoBrush)
    p.drawLine(int(cx), int(cy - fh * 0.1), int(cx - fw * 0.08), int(cy + fh * 0.17))
    p.drawLine(int(cx - fw * 0.08), int(cy + fh * 0.17), int(cx + fw * 0.08), int(cy + fh * 0.17))
    # boca
    p.setPen(pen('#9c5b50', 2)); p.setBrush(QColor(lip))
    m = QPainterPath(); m.moveTo(cx - fw * 0.27, cy + fh * 0.44)
    m.quadTo(cx, cy + fh * 0.54, cx + fw * 0.27, cy + fh * 0.44)
    m.quadTo(cx, cy + fh * 0.49, cx - fw * 0.27, cy + fh * 0.44)
    p.drawPath(m)
    # malha
    P = _mesh_points(cx, cy, fw, fh, seed, jitter)
    tri = Delaunay(P)
    p.setBrush(Qt.NoBrush); p.setPen(pen(QColor(62, 207, 142, mesh_alpha), 0.7))
    for s in tri.simplices:
        p.drawPolygon(QPolygonF([QPointF(*P[i]) for i in s]))
    p.setPen(Qt.NoPen); p.setBrush(QColor(62, 207, 142, dot_alpha))
    for x, y in P:
        p.drawEllipse(QPointF(x, y), 1.3, 1.3)
    return P


VARIANTS = [
    dict(skin=('#f2cdaf', '#e0b291', '#b98a6c'), hair='#3a2c1d', lip='#c47f78', seed=3),  # clara
    dict(skin=('#caa078', '#a87a54', '#7c5638'), hair='#1c140d', lip='#a86a5e', seed=11), # média
    dict(skin=('#8a6248', '#6b4a34', '#4a3122'), hair='#120d08', lip='#7d4f44', seed=23), # escura
]


def render_tile(v, out):
    W, H = 320, 360
    img = QImage(W, H, QImage.Format_ARGB32); img.fill(0)
    p = QPainter(img); p.setRenderHint(QPainter.Antialiasing)
    p.setPen(pen('#2a2e37', 1)); p.setBrush(QColor('#14161b'))
    p.drawRoundedRect(QRectF(4, 4, W - 8, H - 8), 14, 14)
    draw_face(p, W / 2, H / 2 - 6, 96, 124, v['skin'], v['hair'], v['lip'], v['seed'])
    # mini bbox
    p.setPen(pen('#4c8dff', 1.5)); p.setBrush(Qt.NoBrush)
    p.drawRect(QRectF(W / 2 - 110, H / 2 - 140, 220, 270))
    p.end(); img.save(out)
    print('OK', out)


def qimage_to_pil(img):
    img = img.convertToFormat(QImage.Format_RGBA8888)
    buf = QBuffer(); buf.open(QIODevice.ReadWrite); img.save(buf, 'PNG')
    from io import BytesIO
    return Image.open(BytesIO(bytes(buf.data()))).convert('RGB')


def render_gif(out, n=14):
    W, H = 520, 440
    v = VARIANTS[1]
    frames = []
    for k in range(n):
        img = QImage(W, H, QImage.Format_ARGB32); img.fill(0)
        p = QPainter(img); p.setRenderHint(QPainter.Antialiasing)
        g = QLinearGradient(0, 0, 0, H); g.setColorAt(0, QColor('#0c0f15')); g.setColorAt(1, QColor('#05070b'))
        p.fillRect(0, 0, W, H, g)
        jit = 0.8 + 0.6 * np.sin(k / n * 2 * np.pi)
        draw_face(p, W / 2, H / 2, 110, 142, v['skin'], v['hair'], v['lip'], seed=11, jitter=jit)
        # bounding box pulsante
        pulse = int(180 + 60 * np.sin(k / n * 2 * np.pi))
        p.setPen(pen(QColor(76, 141, 255, pulse), 2)); p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(W / 2 - 128, H / 2 - 160, 256, 320))
        # linha de varredura
        sy = H / 2 - 160 + (320) * (k / (n - 1))
        p.setPen(pen(QColor(62, 207, 142, 200), 2)); p.drawLine(int(W / 2 - 128), int(sy), int(W / 2 + 128), int(sy))
        p.setPen(QColor('#4c8dff')); fnt = QFont('Arial'); fnt.setPointSize(10); fnt.setBold(True); p.setFont(fnt)
        p.drawText(QRectF(W / 2 - 128, H / 2 - 184, 256, 16), Qt.AlignLeft, 'RASTREANDO · 478 landmarks')
        p.end()
        frames.append(qimage_to_pil(img))
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=90, loop=0, optimize=True)
    print('OK', out, len(frames), 'frames')


for i, v in enumerate(VARIANTS, 1):
    render_tile(v, f'docs/assets/face_var{i}.png')
render_gif('docs/assets/face_scan.gif')
