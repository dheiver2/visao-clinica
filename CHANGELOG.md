# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Este projeto segue [SemVer](https://semver.org/lang/pt-BR/) a partir da v0.1.0.

## [Não lançado]

### Adicionado
- Preparação para publicação pública: LICENSE (MIT), `PRIVACY.md`,
  `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `RELEASING.md`.
- CI (GitHub Actions) rodando `pytest` + `ruff` a cada push/PR.
- Dependabot para dependências pip e GitHub Actions.
- Templates de issue (bug, feature, acurácia clínica) e de PR.
- Empacotamento formal via `pyproject.toml` e configuração de `ruff`/`pre-commit`.
- Configuração de cobertura de testes (`pytest-cov`).
- Disclaimer de não-diagnóstico exibido no primeiro uso da UI.
- Consentimento explícito (LGPD) antes da captura em todos os módulos clínicos.
- Tratamento de erro mais claro em `app/ai/bootstrap.py` para falhas de
  download/compilação do backend BitNet.

## [0.1.0] — desenvolvimento inicial

### Adicionado
- Scaffold inicial: extração de biomarcadores por webcam (OpenCV + MediaPipe)
  e raciocínio clínico via BitNet b1.58 2B4T local.
- Autoconfiguração encapsulada do backend BitNet (`bitnet.cpp` nativo com
  fallback `transformers`), sem exigir configuração manual.
- Painel clínico com 12 indicadores de triagem determinísticos e instantâneos
  (TEA, perfil parkinsoniano, sinais tipo Alzheimer, Síndrome de Down, e mais
  8 indicadores de base).
- Biomarcadores avançados fundamentados em literatura (rPPG/POS, BCEA +
  main-sequence de saccades, hipomimia via FACS, estereotipias por
  autocorrelação) — referências em `REFERENCES.md`.
- Técnicas de precisão de sinal: One-Euro filter, Hampel, Butterworth +
  Welch PSD com SNR-gate, gating de qualidade e confiança por condição.
- Face Landmarker de alta precisão (478 landmarks + 52 blendshapes/AUs).
- Módulo Ocupacional NR-01: riscos psicossociais (8 fatores), plano de ação e
  relatório agregado por setor, com consentimento informado por sessão.
- UI desktop (PySide6) com preview contínuo da webcam, malha de landmarks
  ao vivo, modos Pesquisa e Triagem, e tema dark premium.
- Geração de relatórios em PDF e exportação CSV.
- Empacotamento como app desktop macOS (`scripts/make_app_bundle.sh`).
- GitHub Page de apresentação (`docs/`).
- Suíte de testes cobrindo engine clínica, validação, métricas, blendshapes,
  biomarcadores avançados, condições, NR-01 e processamento de sinal.
