#!/usr/bin/env bash
# Cria o app executável "Visão Clínica.app" na Área de Trabalho (macOS).
# Gera o ícone, monta o bundle com permissão de câmera e registra no Finder.
#
# Uso:  bash scripts/make_app_bundle.sh
set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$HOME/Desktop/Visão Clínica.app"
PY="$PROJ/.venv/bin/python"

echo ">> Gerando ícone..."
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
# contorno de rosto + malha de landmarks (identidade do produto)
p.setPen(QPen(QColor('#4c8dff'), 18)); p.setBrush(Qt.NoBrush)
p.drawEllipse(QPointF(cx, cy+10), 250, 310)
rng = np.random.default_rng(7)
pts = []
for _ in range(80):
    a = rng.uniform(0, 2*math.pi); r = rng.uniform(0.2, 0.95)
    pts.append((cx + 250*r*math.cos(a), cy+10 + 310*r*math.sin(a)))
# arestas da malha
p.setPen(QPen(QColor(62, 207, 142, 150), 3))
for i in range(0, len(pts)-1, 1):
    if rng.random() < 0.5:
        j = rng.integers(0, len(pts))
        p.drawLine(int(pts[i][0]), int(pts[i][1]), int(pts[j][0]), int(pts[j][1]))
p.setPen(Qt.NoPen); p.setBrush(QColor('#3ecf8e'))
for x, y in pts:
    p.drawEllipse(QPointF(x, y), 8, 8)
# olhos
p.setBrush(QColor('#4c8dff'))
p.drawEllipse(QPointF(cx-95, cy-40), 26, 26); p.drawEllipse(QPointF(cx+95, cy-40), 26, 26)
p.end(); img.save('/tmp/icon_1024.png')
PYEOF

echo ">> Convertendo para .icns..."
rm -rf /tmp/Icon.iconset && mkdir /tmp/Icon.iconset
for sz in 16 32 64 128 256 512; do
  sips -z $sz $sz /tmp/icon_1024.png --out /tmp/Icon.iconset/icon_${sz}x${sz}.png >/dev/null
  d=$((sz*2)); sips -z $d $d /tmp/icon_1024.png --out /tmp/Icon.iconset/icon_${sz}x${sz}@2x.png >/dev/null
done
iconutil -c icns /tmp/Icon.iconset -o /tmp/VisaoClinica.icns

echo ">> Montando o bundle..."
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp /tmp/VisaoClinica.icns "$APP/Contents/Resources/icon.icns"

cat > "$APP/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>Visão Clínica</string>
  <key>CFBundleDisplayName</key><string>Visão Clínica</string>
  <key>CFBundleIdentifier</key><string>br.com.visaoclinica.app</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>run</string>
  <key>CFBundleIconFile</key><string>icon</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSCameraUsageDescription</key>
  <string>O Visão Clínica usa a câmera para a triagem por visão computacional, processada 100% localmente.</string>
</dict>
</plist>
PLIST

cat > "$APP/Contents/MacOS/run" <<'SH'
#!/bin/bash
PROJ="$HOME/Downloads/Projetos/visao-clinica"
PY="$PROJ/.venv/bin/python"
export TOKENIZERS_PARALLELISM=false
cd "$PROJ" || exit 1
if [ ! -x "$PY" ]; then
  osascript -e 'display alert "Visão Clínica" message "Ambiente não encontrado em ~/Downloads/Projetos/visao-clinica/.venv"'
  exit 1
fi
exec "$PY" -m app.main "$@"
SH
chmod +x "$APP/Contents/MacOS/run"

echo ">> Registrando no Finder..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$APP" 2>/dev/null || true
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
touch "$APP"
echo "OK: $APP"
