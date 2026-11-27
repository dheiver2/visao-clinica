# Visão Clínica — Computer-Vision Screening (native macOS)

[![CI](https://github.com/dheiver2/visao-clinica/actions/workflows/ci.yml/badge.svg)](https://github.com/dheiver2/visao-clinica/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Swift 5.9+](https://img.shields.io/badge/swift-5.9%2B-orange.svg)](Package.swift)
[![Platform: macOS 13+](https://img.shields.io/badge/platform-macOS%2013%2B-lightgrey.svg)](#requirements)

A **100% native macOS (Swift/SwiftUI)** and **100% local/offline** app that extracts
biomarkers and **contactless vital signs** from the webcam, with **deterministic**
clinical screening. Zero Python — Apple native frameworks only.

> **Screening and research-support tool.** Not a medical diagnosis
> and not a substitute for professional evaluation. Data: see [PRIVACY.md](PRIVACY.md) (LGPD).

## Architecture (100% native frameworks)

```
Webcam (AVFoundation) → Vision (landmarks) → Biomarkers + skin ROI
   → Accelerate/DSP (rPPG POS, FFT, HRV) → Deterministic clinical engine
   → SwiftUI (dashboard + vitals) · SQLite (sessions/audit) · CryptoKit (access)
```

| Layer | Before (Python) | Now (native Swift) |
|---|---|---|
| UI | PySide6 | **SwiftUI** — `Views/` |
| Webcam | OpenCV | **AVFoundation** — `Camera/CameraController.swift` |
| Landmarks | MediaPipe | **Vision** — `Vision/FaceBiomarkers.swift` |
| DSP (rPPG/FFT/HRV) | NumPy/SciPy | **Swift/Accelerate** — `Signal/DSP.swift`, `Vitals/Vitals.swift` |
| Clinical engine | Python | **Swift** — `Clinical/Clinical.swift` |
| Persistence | sqlite3 (py) | **SQLite3** — `Storage/Database.swift` |
| Password/access | hashlib | **CommonCrypto (PBKDF2)** — `Security/Crypto.swift` |

## Requirements

- **macOS 13+** (Apple Silicon)
- **Swift 5.9+** (via Xcode or Command Line Tools — `xcode-select --install`)

## Build & run

```bash
# native app (self-contained .app, ad-hoc signed)
bash scripts/build_macos.sh
open "dist/Visão Clínica.app"      # macOS asks for camera access on first launch

# development
swift build && swift run VisaoClinica

# core validation (no Xcode needed — runs with Command Line Tools)
swift run VisaoClinica --selftest
```

On first use the app asks you to create an **administrator user** (access
control) and to give **camera consent** (LGPD).

## Features (native version)

- **Guided capture** in real time (position, distance and lighting) with a **live
  pulse wave** (Canvas) over the preview.
- **Contactless vital signs** via rPPG (POS method): heart rate,
  respiration (RIIV), HRV (SDNN/RMSSD/pNN50), LF/HF balance and Baevsky stress index.
- **Wellness score (0–100)** — deterministic synthesis.
- **Deterministic clinical dashboard** per condition (stress/anxiety, drowsiness,
  facial asymmetry) with risk level and rationale.
- **History & trends** with **Swift Charts** (wellness and HR evolution).
- **Role-based access control** (administrator/professional/researcher) with
  PBKDF2 and an **audit trail (LGPD)** in SQLite.
- Native polish: **custom icon**, **⌘ menus/shortcuts** (⌘R analyze,
  ⇧⌘H history), **SF Symbols**, **camera permission** UX and **universal binary**.

## Parity roadmap (porting from the legacy Python app)

Items being migrated to native: the **NR-01** occupational module, **PDF** export
(PDFKit) with institutional branding, **full management** of users/audit in the
UI, **eMAG accessibility** (font/high contrast), **backup/restore**, the full set of
**12 indicators** and the optional **local LLM** (MLX) narrative.

## Tests

The native self-test validates the deterministic core (rPPG, HRV, wellness, conditions,
access control) without depending on Xcode:

```bash
swift run VisaoClinica --selftest
```

CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs `swift build` +
the self-test on `macos-14` on every push/PR.
