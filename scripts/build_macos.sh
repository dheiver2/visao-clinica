#!/usr/bin/env bash
# Build do "Visão Clínica.app" NATIVO (Swift/SwiftUI) — sem Python.
#
#   bash scripts/build_macos.sh
#
# Saída:
#   dist/Visão Clínica.app   — app nativo autocontido (arm64)
#
# Assinatura ad-hoc SEM entitlements (evita "launch error 163" em apps SwiftPM
# não sandboxados). A permissão de câmera vem do NSCameraUsageDescription.
set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Visão Clínica"
BIN="VisaoClinica"
cd "$PROJ"

echo ">> Compilando (release)..."
swift build -c release

BIN_PATH="$(swift build -c release --show-bin-path)/$BIN"
[ -x "$BIN_PATH" ] || { echo "ERRO: binário não encontrado em $BIN_PATH"; exit 1; }

echo ">> Rodando self-test..."
"$BIN_PATH" --selftest

echo ">> Montando o .app..."
APP="dist/${APP_NAME}.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN_PATH" "$APP/Contents/MacOS/$BIN"
cp Resources/Info.plist "$APP/Contents/Info.plist"
[ -f Resources/AppIcon.icns ] && cp Resources/AppIcon.icns "$APP/Contents/Resources/"

echo ">> Assinando (ad-hoc, sem entitlements)..."
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

echo ""
echo "OK ✓"
echo "  App: $APP"
du -sh "$APP"
echo ""
echo "Abrir:  open \"$APP\"   (na 1ª vez o macOS pedirá acesso à câmera)"
echo "NOTA: distribuir fora desta máquina exige assinatura/notarização (Developer ID)."
