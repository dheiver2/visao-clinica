# Visão Clínica — Triagem por Visão Computacional (nativo macOS)

[![CI](https://github.com/dheiver2/visao-clinica/actions/workflows/ci.yml/badge.svg)](https://github.com/dheiver2/visao-clinica/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Swift 5.9+](https://img.shields.io/badge/swift-5.9%2B-orange.svg)](Package.swift)
[![Plataforma: macOS 13+](https://img.shields.io/badge/plataforma-macOS%2013%2B-lightgrey.svg)](#requisitos)

Aplicação **100% nativa macOS (Swift/SwiftUI)** e **100% local/offline** que extrai
biomarcadores e **sinais vitais sem contato** pela webcam, com triagem clínica
**determinística**. Zero Python — só frameworks nativos da Apple.

> **Ferramenta de triagem e apoio à pesquisa.** Não constitui diagnóstico médico
> e não substitui avaliação profissional. Dados: ver [PRIVACY.md](PRIVACY.md) (LGPD).

## Arquitetura (100% frameworks nativos)

```
Webcam (AVFoundation) → Vision (landmarks) → Biomarcadores + ROI de pele
   → Accelerate/DSP (rPPG POS, FFT, HRV) → Motor clínico determinístico
   → SwiftUI (painel + vitais) · SQLite (sessões/auditoria) · CryptoKit (acesso)
```

| Camada | Antes (Python) | Agora (Swift nativo) |
|---|---|---|
| UI | PySide6 | **SwiftUI** — `Views/` |
| Webcam | OpenCV | **AVFoundation** — `Camera/CameraController.swift` |
| Landmarks | MediaPipe | **Vision** — `Vision/FaceBiomarkers.swift` |
| DSP (rPPG/FFT/HRV) | NumPy/SciPy | **Swift/Accelerate** — `Signal/DSP.swift`, `Vitals/Vitals.swift` |
| Motor clínico | Python | **Swift** — `Clinical/Clinical.swift` |
| Persistência | sqlite3 (py) | **SQLite3** — `Storage/Database.swift` |
| Senha/acesso | hashlib | **CommonCrypto (PBKDF2)** — `Security/Crypto.swift` |

## Requisitos

- **macOS 13+** (Apple Silicon)
- **Swift 5.9+** (via Xcode ou Command Line Tools — `xcode-select --install`)

## Build & execução

```bash
# app nativo (.app autocontido, assinado ad-hoc)
bash scripts/build_macos.sh
open "dist/Visão Clínica.app"      # na 1ª vez o macOS pede acesso à câmera

# desenvolvimento
swift build && swift run VisaoClinica

# validação do núcleo (sem Xcode — roda com Command Line Tools)
swift run VisaoClinica --selftest
```

No primeiro uso o app pede a criação de um **usuário administrador** (controle de
acesso) e o **consentimento de câmera** (LGPD).

## Funcionalidades (versão nativa)

- **Captura guiada** em tempo real (posição, distância e iluminação).
- **Sinais vitais sem contato** por rPPG (método POS): frequência cardíaca,
  respiração (RIIV), VFC (SDNN/RMSSD/pNN50), balanço LF/HF e índice de estresse de Baevsky.
- **Score de bem-estar (0–100)** — síntese determinística.
- **Painel clínico determinístico** por condição (estresse/ansiedade, sonolência,
  assimetria facial) com nível de risco e racional.
- **Controle de acesso por perfil** (administrador/profissional/pesquisador) com
  PBKDF2 e **trilha de auditoria (LGPD)** em SQLite.
- **Histórico** de sessões offline.

## Roadmap de paridade (portando do app Python legado)

Itens em migração para o nativo: módulo ocupacional **NR-01**, exportação **PDF**
(PDFKit) com personalização institucional, **gestão completa** de usuários/auditoria
na UI, **acessibilidade eMAG** (fonte/alto contraste), **backup/restauração**, o
conjunto completo de **12 indicadores** e a narrativa opcional por **LLM local** (MLX).

## Testes

O self-test nativo valida o núcleo determinístico (rPPG, VFC, bem-estar, condições,
controle de acesso) sem depender do Xcode:

```bash
swift run VisaoClinica --selftest
```

O CI ([.github/workflows/ci.yml](.github/workflows/ci.yml)) roda `swift build` +
self-test em `macos-14` a cada push/PR.
