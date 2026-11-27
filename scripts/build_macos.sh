#!/usr/bin/env bash
# Build of the NATIVE "Visão Clínica.app" (Swift/SwiftUI) — no Python.
#
#   bash scripts/build_macos.sh
#
# Output:
#   dist/Visão Clínica.app   — self-contained native app (universal, when possible)
#
# Ad-hoc signing WITHOUT entitlements (avoids "launch error 163" in non-sandboxed
# SwiftPM apps). Camera permission comes from NSCameraUsageDescription.
set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_NAME="Visão Clínica"
BIN="VisaoClinica"
cd "$PROJ"

# Try a universal binary (arm64 + x86_64); fall back to native if unavailable.
echo ">> Building (release)..."
ARCH_FLAGS="--arch arm64 --arch x86_64"
if swift build -c release $ARCH_FLAGS 2>/dev/null; then
  BIN_PATH="$(swift build -c release $ARCH_FLAGS --show-bin-path)/$BIN"
  echo "   universal binary (arm64 + x86_64)"
else
  echo "   universal unavailable — building native"
  swift build -c release
  BIN_PATH="$(swift build -c release --show-bin-path)/$BIN"
fi
[ -x "$BIN_PATH" ] || { echo "ERROR: binary not found at $BIN_PATH"; exit 1; }

echo ">> Running self-test..."
"$BIN_PATH" --selftest

echo ">> Generating icon (.icns)..."
"$BIN_PATH" --make-icon /tmp/vc_icon_1024.png >/dev/null
ICONSET="/tmp/VisaoClinica.iconset"
rm -rf "$ICONSET"; mkdir -p "$ICONSET"
for sz in 16 32 64 128 256 512; do
  sips -z $sz $sz /tmp/vc_icon_1024.png --out "$ICONSET/icon_${sz}x${sz}.png" >/dev/null
  d=$((sz * 2)); sips -z $d $d /tmp/vc_icon_1024.png --out "$ICONSET/icon_${sz}x${sz}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o Resources/AppIcon.icns

echo ">> Assembling the .app..."
APP="dist/${APP_NAME}.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN_PATH" "$APP/Contents/MacOS/$BIN"
cp Resources/Info.plist "$APP/Contents/Info.plist"
cp Resources/AppIcon.icns "$APP/Contents/Resources/"

echo ">> Signing (ad-hoc, no entitlements)..."
codesign --force --deep --sign - "$APP" >/dev/null 2>&1 || true
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

echo ""
echo "OK ✓"
echo "  App: $APP"
file "$APP/Contents/MacOS/$BIN" | sed 's/^/  /'
du -sh "$APP"
echo ""
echo "Open:  open \"$APP\"   (macOS will ask for camera access on first launch)"
echo "NOTE: distributing outside this machine requires signing/notarization (Developer ID)."
