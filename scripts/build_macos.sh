#!/usr/bin/env bash
# Build do "Visão Clínica.app" autocontido + .dmg de distribuição (macOS).
#
#   bash scripts/build_macos.sh
#
# Saídas:
#   dist/Visão Clínica.app   — bundle autocontido (não depende do .venv)
#   dist/VisaoClinica-1.0.dmg — instalador (arrastar para Applications)
#
# Flags por ambiente:
#   BUNDLE_GGUF=1   embute o modelo BitNet (~1.1 GB) no app
set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$PROJ/.venv/bin/python"
APP_NAME="Visão Clínica"
VERSION="1.0"
cd "$PROJ"

[ -x "$PY" ] || { echo "ERRO: .venv não encontrado. Rode: python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt"; exit 1; }

echo ">> Garantindo PyInstaller..."
"$PY" -m pip install --quiet --upgrade "pyinstaller>=6.3" pillow

echo ">> Gerando ícone (.icns)..."
PYTHONPATH="$PROJ" QT_QPA_PLATFORM=offscreen "$PY" - <<'PYEOF'
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QImage, QPainter, QColor, QPen, QLinearGradient, QBrush
from PySide6.QtWidgets import QApplication
import numpy as np, math
app = QApplication([])
S = 1024
img = QImage(S, S, QImage.Format_ARGB32); img.fill(0)
p = QPainter(img); p.setRenderHint(QPainter.Antialiasing)
g = QLinearGradient(0, 0, S, S); g.setColorAt(0, QColor('#0c0f15')); g.setColorAt(1, QColor('#05070b'))
p.setBrush(QBrush(g)); p.setPen(Qt.NoPen); p.drawRoundedRect(QRectF(40, 40, S-80, S-80), 200, 200)
cx, cy = S/2, S/2
p.setPen(QPen(QColor('#4c8dff'), 18)); p.setBrush(Qt.NoBrush)
p.drawEllipse(QPointF(cx, cy+10), 250, 310)
rng = np.random.default_rng(7); pts = []
for _ in range(80):
    a = rng.uniform(0, 2*math.pi); r = rng.uniform(0.2, 0.95)
    pts.append((cx + 250*r*math.cos(a), cy+10 + 310*r*math.sin(a)))
p.setPen(QPen(QColor(62, 207, 142, 150), 3))
for i in range(len(pts)-1):
    if rng.random() < 0.5:
        j = rng.integers(0, len(pts)); p.drawLine(int(pts[i][0]), int(pts[i][1]), int(pts[j][0]), int(pts[j][1]))
p.setPen(Qt.NoPen); p.setBrush(QColor('#3ecf8e'))
for x, y in pts: p.drawEllipse(QPointF(x, y), 8, 8)
p.setBrush(QColor('#4c8dff'))
p.drawEllipse(QPointF(cx-95, cy-40), 26, 26); p.drawEllipse(QPointF(cx+95, cy-40), 26, 26)
p.end(); img.save('/tmp/icon_1024.png')
PYEOF
rm -rf /tmp/Icon.iconset && mkdir /tmp/Icon.iconset
for sz in 16 32 64 128 256 512; do
  sips -z $sz $sz /tmp/icon_1024.png --out /tmp/Icon.iconset/icon_${sz}x${sz}.png >/dev/null
  d=$((sz*2)); sips -z $d $d /tmp/icon_1024.png --out /tmp/Icon.iconset/icon_${sz}x${sz}@2x.png >/dev/null
done
iconutil -c icns /tmp/Icon.iconset -o /tmp/VisaoClinica.icns

echo ">> Limpando builds anteriores..."
rm -rf build dist

echo ">> Empacotando com PyInstaller (pode demorar alguns minutos)..."
"$PY" -m PyInstaller VisaoClinica.spec --noconfirm

APP_PATH="dist/${APP_NAME}.app"
[ -d "$APP_PATH" ] || { echo "ERRO: bundle não gerado em $APP_PATH"; exit 1; }

# remove quarentena local (distribuição real exige assinatura/notarização)
xattr -dr com.apple.quarantine "$APP_PATH" 2>/dev/null || true

echo ">> Montando o .dmg..."
DMG="dist/VisaoClinica-${VERSION}.dmg"
STAGE="$(mktemp -d)"
cp -R "$APP_PATH" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
rm -f "$DMG"
hdiutil create -volname "$APP_NAME" -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
rm -rf "$STAGE"

echo ""
echo "OK ✓"
echo "  App: $APP_PATH"
echo "  DMG: $DMG"
du -sh "$APP_PATH" "$DMG"
echo ""
echo "NOTA: para distribuir fora da sua máquina é preciso assinar e notarizar"
echo "      (Apple Developer ID). Sem isso o macOS bloqueia em outros Macs."
