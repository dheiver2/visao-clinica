#!/usr/bin/env bash
# Build do "Visão Clínica.app" NATIVO (Swift/SwiftUI) — sem Python.
#
#   bash scripts/build_macos.sh
#
# Saída:
#   dist/Visão Clínica.app   — app nativo autocontido (universal, quando possível)
#
# Assinatura ad-hoc SEM entitlements (evita "launch error 163" em apps SwiftPM
# não sandboxados). A permissão de câmera vem do NSCameraUsageDescription.
set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Visão Clínica"
BIN="VisaoClinica"
cd "$PROJ"

# Tenta binário universal (arm64 + x86_64); cai para nativo se indisponível.
echo ">> Compilando (release)..."
ARCH_FLAGS="--arch arm64 --arch x86_64"
if swift build -c release $ARCH_FLAGS 2>/dev/null; then
  BIN_PATH="$(swift build -c release $ARCH_FLAGS --show-bin-path)/$BIN"
  echo "   binário universal (arm64 + x86_64)"
else
  echo "   universal indisponível — compilando nativo"
  swift build -c release
  BIN_PATH="$(swift build -c release --show-bin-path)/$BIN"
fi
[ -x "$BIN_PATH" ] || { echo "ERRO: binário não encontrado em $BIN_PATH"; exit 1; }

echo ">> Rodando self-test..."
"$BIN_PATH" --selftest

echo ">> Gerando ícone (.icns)..."
"$BIN_PATH" --make-icon /tmp/vc_icon_1024.png >/dev/null
ICONSET="/tmp/VisaoClinica.iconset"
rm -rf "$ICONSET"; mkdir -p "$ICONSET"
for sz in 16 32 64 128 256 512; do
  sips -z $sz $sz /tmp/vc_icon_1024.png --out "$ICONSET/icon_${sz}x${sz}.png" >/dev/null
  d=$((sz * 2)); sips -z $d $d /tmp/vc_icon_1024.png --out "$ICONSET/icon_${sz}x${sz}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o Resources/AppIcon.icns

echo ">> Montando o .app..."
APP="dist/${APP_NAME}.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN_PATH" "$APP/Contents/MacOS/$BIN"
cp Resources/Info.plist "$APP/Contents/Info.plist"
cp Resources/AppIcon.icns "$APP/Contents/Resources/"

echo ">> Assinando (ad-hoc, sem entitlements)..."
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

echo ""
echo "OK ✓"
echo "  App: $APP"
file "$APP/Contents/MacOS/$BIN" | sed 's/^/  /'
du -sh "$APP"
echo ""
echo "Abrir:  open \"$APP\"   (na 1ª vez o macOS pedirá acesso à câmera)"
echo "NOTA: distribuir fora desta máquina exige assinatura/notarização (Developer ID)."
