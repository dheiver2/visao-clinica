# Visão Clínica — Triagem por Visão Computacional + IA Local (BitNet b1.58 2B4T)

Aplicação **desktop 100% local/offline** que extrai biomarcadores por webcam
(OpenCV + MediaPipe) e usa o **BitNet b1.58 2B4T** como LLM local nativo para
interpretação multimodal, raciocínio clínico probabilístico e geração de relatórios.

> **Ferramenta de triagem e apoio à pesquisa.** Não constitui diagnóstico médico
> e não substitui avaliação profissional. Veja [PROMPT.md](PROMPT.md) para a especificação completa.

## Arquitetura

```
Webcam → OpenCV + MediaPipe (Face Mesh/Pose/Hands) → Extração de Features
       → BitNet b1.58 2B4T (bitnet.cpp) → Motor de Inferência Clínica
       → Dashboard + Relatório PDF + Exportação CSV
```

| Camada | Arquivo |
|--------|---------|
| Features (dataclass) | `app/vision/features.py` |
| Extração CV | `app/vision/extractor.py` |
| Backend LLM (bitnet.cpp / fallback) | `app/ai/bitnet_backend.py` |
| `ClinicalReasoningEngine` | `app/clinical/reasoning_engine.py` |
| Persistência SQLite | `app/storage/db.py` |
| Relatórios PDF/CSV | `app/report/exporter.py` |
| UI PySide6 | `app/ui/main_window.py` |

## Instalação

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Backend do LLM

O **backend primário é o `bitnet.cpp`** (inferência nativa 1,58-bit — máxima eficiência).
Compile o `bitnet.cpp` oficial, converta o modelo `microsoft/bitnet-b1.58-2B-4T` para
GGUF i2_s e aponte:

```bash
export BITNET_CPP_BIN=/caminho/bitnet.cpp/build/bin/llama-cli
export BITNET_MODEL_GGUF=/caminho/models/bitnet-b1.58-2B-4T.i2_s.gguf
```

Sem essas variáveis, o sistema cai para o **fallback `transformers`** (menos eficiente),
com aviso explícito.

## Execução

```bash
python -m app.main                 # GUI (modo Pesquisa)
python -m app.main --mode triagem  # GUI simplificada
python -m app.main --cli --duration 30
```

## Modos
- **Pesquisa:** todas as métricas, hipóteses, variáveis influentes e relatório completo.
- **Triagem:** interface simplificada, apenas indicadores de risco.

## Testes

```bash
pip install pytest
pytest -q
```
