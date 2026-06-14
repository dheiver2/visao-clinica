"""Gera docs/assets/face_mesh.png — rosto realista com malha de landmarks no app."""
import numpy as np
from scipy.spatial import Delaunay
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (QImage, QPainter, QColor, QPen, QBrush, QRadialGradient,
    QLinearGradient, QFont, QPainterPath, QPolygonF)
from PySide6.QtWidgets import QApplication

app = QApplication([])
W, H = 960, 600
img = QImage(W, H, QImage.Format_ARGB32); img.fill(0)
p = QPainter(img); p.setRenderHint(QPainter.Antialiasing)

def pen(color, w, cap=Qt.SquareCap):
    return QPen(QColor(color), w, Qt.SolidLine, cap)

# moldura do app
g = QLinearGradient(0, 0, 0, H); g.setColorAt(0, QColor('#0c0f15')); g.setColorAt(1, QColor('#05070b'))
p.fillRect(0, 0, W, H, g)
p.setPen(pen('#2a2e37', 2)); p.setBrush(Qt.NoBrush)
p.drawRoundedRect(QRectF(8, 8, W - 16, H - 16), 14, 14)

cx, cy, fw, fh = 380, 300, 150, 195

# pescoço/ombros (atrás)
p.setPen(Qt.NoPen)
p.setBrush(QColor('#1b2230'))
path = QPainterPath(); path.moveTo(cx - 220, H - 20); path.quadTo(cx, cy + 150, cx + 220, H - 20); path.closeSubpath()
p.drawPath(path)
p.setBrush(QColor('#b07e63')); p.drawRoundedRect(QRectF(cx - 55, cy + 150, 110, 90), 20, 20)

# pele
skin = QRadialGradient(cx, cy - 20, 230)
skin.setColorAt(0, QColor('#e7b89a')); skin.setColorAt(0.7, QColor('#cf9c7e')); skin.setColorAt(1, QColor('#9c6f55'))
p.setBrush(QBrush(skin)); p.drawEllipse(QPointF(cx, cy), fw, fh)

# cabelo
p.setBrush(QColor('#2a2118'))
hair = QPainterPath(); hair.moveTo(cx - fw - 6, cy - 30)
hair.quadTo(cx - fw - 20, cy - fh - 40, cx, cy - fh - 30); hair.quadTo(cx + fw + 20, cy - fh - 40, cx + fw + 6, cy - 30)
hair.quadTo(cx + fw - 30, cy - fh + 40, cx, cy - fh + 30); hair.quadTo(cx - fw + 30, cy - fh + 40, cx - fw - 6, cy - 30)
p.drawPath(hair)

# sobrancelhas
p.setPen(pen('#3a2c1d', 7, Qt.RoundCap))
p.drawLine(cx - 78, cy - 58, cx - 26, cy - 66); p.drawLine(cx + 26, cy - 66, cx + 78, cy - 58)
# olhos
for ex in (cx - 50, cx + 50):
    p.setPen(Qt.NoPen); p.setBrush(QColor('#f4f1ec')); p.drawEllipse(QPointF(ex, cy - 34), 26, 15)
    p.setBrush(QColor('#5a3d2b')); p.drawEllipse(QPointF(ex, cy - 34), 11, 11)
    p.setBrush(QColor('#1a120c')); p.drawEllipse(QPointF(ex, cy - 34), 5, 5)
    p.setBrush(QColor('#ffffff')); p.drawEllipse(QPointF(ex + 3, cy - 37), 2.4, 2.4)
# nariz
p.setPen(pen('#a67457', 4, Qt.RoundCap)); p.setBrush(Qt.NoBrush)
p.drawLine(cx, cy - 20, cx - 12, cy + 34); p.drawLine(cx - 12, cy + 34, cx + 12, cy + 34)
# boca
p.setPen(pen('#9c5b50', 3)); p.setBrush(QColor('#b9726a'))
mp = QPainterPath(); mp.moveTo(cx - 40, cy + 86); mp.quadTo(cx, cy + 104, cx + 40, cy + 86); mp.quadTo(cx, cy + 96, cx - 40, cy + 86)
p.drawPath(mp)

# malha Delaunay
rng = np.random.default_rng(7); pts = []
for a in np.linspace(0, 2 * np.pi, 46, endpoint=False):
    pts.append((cx + fw * np.cos(a) * 0.98, cy + fh * np.sin(a) * 0.98))
for _ in range(160):
    x = rng.uniform(cx - fw, cx + fw); y = rng.uniform(cy - fh, cy + fh)
    if ((x - cx) / fw) ** 2 + ((y - cy) / fh) ** 2 < 0.92:
        pts.append((x, y))
for ex in (cx - 50, cx + 50):
    for a in np.linspace(0, 2 * np.pi, 10, endpoint=False):
        pts.append((ex + 26 * np.cos(a), cy - 34 + 15 * np.sin(a)))
for a in np.linspace(0, 2 * np.pi, 14, endpoint=False):
    pts.append((cx + 40 * np.cos(a), cy + 90 + 10 * np.sin(a)))
P = np.array(pts); tri = Delaunay(P)
p.setBrush(Qt.NoBrush); p.setPen(pen(QColor(62, 207, 142, 90), 0.7))
for s in tri.simplices:
    p.drawPolygon(QPolygonF([QPointF(*P[i]) for i in s]))
p.setPen(Qt.NoPen); p.setBrush(QColor(62, 207, 142, 230))
for x, y in P:
    p.drawEllipse(QPointF(x, y), 1.5, 1.5)

# HUD bounding box
p.setPen(pen('#4c8dff', 2)); p.setBrush(Qt.NoBrush)
bx, by, bw, bh = cx - fw - 18, cy - fh - 18, 2 * fw + 36, 2 * fh + 60
p.drawRect(QRectF(bx, by, bw, bh))
p.setPen(pen('#4c8dff', 4))
for (qx, qy, dx, dy) in [(bx, by, 1, 1), (bx + bw, by, -1, 1), (bx, by + bh, 1, -1), (bx + bw, by + bh, -1, -1)]:
    p.drawLine(int(qx), int(qy), int(qx + 18 * dx), int(qy)); p.drawLine(int(qx), int(qy), int(qx), int(qy + 18 * dy))
fnt = QFont('Arial'); fnt.setPointSize(10); fnt.setBold(True); p.setFont(fnt)
p.setPen(QColor('#4c8dff')); p.drawText(QRectF(bx, by - 22, bw, 18), Qt.AlignLeft, 'ROSTO DETECTADO · 478 landmarks')

# HUD lateral
px = 660
p.setPen(Qt.NoPen); p.setBrush(QColor('#14161b')); p.drawRoundedRect(QRectF(px, 70, 250, 470), 12, 12)
p.setPen(QColor('#8b909b')); f2 = QFont('Arial'); f2.setPointSize(9); f2.setBold(True); p.setFont(f2)
p.drawText(QRectF(px + 16, 86, 220, 16), Qt.AlignLeft, 'INDICADORES CLÍNICOS')
rows = [('Tremor parkinsoniano', '#ff5c5c', 0.85), ('Sinais de TEA (autismo)', '#ff5c5c', 0.80),
        ('Tipo Alzheimer', '#ffb020', 0.6), ('Assimetria facial', '#ffb020', 0.55),
        ('Estresse / ansiedade', '#3ecf8e', 0.25), ('Sonolência', '#3ecf8e', 0.15)]
y = 116; f3 = QFont('Arial'); f3.setPointSize(9); p.setFont(f3)
for name, col, val in rows:
    p.setBrush(QColor('#1b1e25')); p.setPen(Qt.NoPen); p.drawRoundedRect(QRectF(px + 14, y, 222, 46), 8, 8)
    p.setPen(QColor('#e6e8ec')); p.drawText(QRectF(px + 24, y + 8, 200, 14), Qt.AlignLeft, name)
    p.setBrush(QColor('#0a0b0e')); p.setPen(Qt.NoPen); p.drawRoundedRect(QRectF(px + 24, y + 28, 200, 6), 3, 3)
    p.setBrush(QColor(col)); p.drawRoundedRect(QRectF(px + 24, y + 28, 200 * val, 6), 3, 3)
    y += 56
p.setPen(QColor('#ff5c5c')); fc = QFont('Arial'); fc.setPointSize(13); fc.setBold(True); p.setFont(fc)
p.drawText(QRectF(px + 14, y + 6, 222, 20), Qt.AlignLeft, '♥ FC 76 bpm · VFC 38 ms')
p.end()
img.save('docs/assets/face_mesh.png')
print('OK face_mesh.png', img.width(), 'x', img.height())
