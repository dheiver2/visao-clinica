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

### Backend do LLM — autoconfiguração encapsulada

**Nada precisa ser configurado manualmente.** Ao executar, o próprio software
(`app/ai/bootstrap.py`) resolve o LLM local sozinho:

1. localiza ou **baixa** o modelo GGUF i2_s oficial em `models/` (1ª vez, online);
2. localiza ou **compila** o `bitnet.cpp` em `vendor/` (1ª vez, se houver `git`+`cmake`);
3. usa o **backend nativo `bitnet.cpp`** quando disponível (máxima eficiência);
4. caso o passo nativo não seja possível, cai para o **fallback `transformers`**
   automaticamente, com aviso — o app nunca interrompe por isso.

Tudo fica **cacheado localmente**; após o primeiro uso, roda 100% offline.

> Opcional: `export BITNET_CPP_BIN=...` e `export BITNET_MODEL_GGUF=...` apenas
> sobrescrevem os caminhos autodetectados. O script `scripts/setup_bitnet.sh`
> existe para pré-provisionar o backend, mas **não é obrigatório**.

## Execução

Use o launcher (usa sempre o Python do `.venv`, sem precisar ativar nada):

```bash
./run.sh                      # GUI (modo Pesquisa)
./run.sh --mode triagem       # GUI simplificada
./run.sh --cli --duration 30  # linha de comando
```

> Se rodar manualmente com `python -m app.main`, **ative o venv antes**
> (`source .venv/bin/activate`) — fora dele o comando `python` pode não existir.

## Modos
- **Pesquisa:** todas as métricas, hipóteses, variáveis influentes e relatório completo.
- **Triagem:** interface simplificada, apenas indicadores de risco.

## Painel clínico (12 indicadores de triagem)

Saída **determinística e instantânea** por condição (não depende do LLM). Inclui
indicadores compostos para os transtornos-alvo:

| Transtorno | Biomarcadores combinados |
|---|---|
| Sinais compatíveis com **TEA (autismo)** | contato visual reduzido, baixa expressividade, movimentos repetitivos |
| **Perfil parkinsoniano** | tremor de repouso 4–6 Hz + hipomimia + piscar reduzido + bradicinesia |
| Sinais tipo **Alzheimer** (comprometimento cognitivo) | instabilidade oculomotora, fixação prejudicada, saccades erráticas |
| Sinais compatíveis com **Síndrome de Down** | hipotonia: boca entreaberta, baixa amplitude facial, movimento reduzido |

Mais 8 indicadores de base (tremor, paralisia facial, oculomotor, piscar,
sonolência, estresse, hipomimia, discinesia).

### Biomarcadores avançados fundamentados em literatura

Técnicas validadas em revistas de alto impacto (citações em [REFERENCES.md](REFERENCES.md)):

| Técnica | Módulo | Referência-chave |
|---|---|---|
| **rPPG** (FC + VFC sem contato, método POS) | `vision/rppg.py` | Wang et al., *IEEE TBME* 2017 |
| **BCEA + main-sequence** de saccades | `vision/oculomotor.py` | Anderson & MacAskill, *Nat Rev Neurol* 2013 |
| **Hipomimia por Action Units (FACS)** | `vision/motor_face.py` | Bandini et al., *J Neurosci Methods* 2017 |
| **Estereotipias por autocorrelação** | `vision/motor_face.py` | Goodwin et al., *JADD* 2011 |

Esses marcadores alimentam os indicadores: Parkinson usa hipomimia FACS; Alzheimer
usa instabilidade de fixação (BCEA); autismo usa estereotipia; estresse usa VFC.

### Técnicas avançadas de precisão (`app/vision/signal.py`)

- **One-Euro filter** — suavização adaptativa dos landmarks (reduz jitter sem
  atrasar movimentos rápidos como saccades/tremor).
- **Hampel** — rejeição robusta de outliers (picos espúrios de detecção).
- **Butterworth bandpass + Welch PSD** — estimativa espectral robusta da frequência
  de tremor na banda fisiológica 3–8 Hz, com **SNR** que separa tremor real de ruído.
- **SNR-gate** — oscilação só conta como tremor se o pico se destacar do ruído.
- **Gating de qualidade** — detecção de face × iluminação → `signal_quality`.
- **Confiança por condição** — cada indicador reporta uma confiança derivada da
  qualidade do sinal e da quantidade de dados; a ordenação pondera score × confiança.

> **Limitações importantes:** são indicadores probabilísticos de **triagem/pesquisa**,
> com limiares **heurísticos não calibrados** em dataset clínico. Síndrome de Down e
> autismo dependem de avaliação especializada (morfologia craniofacial, genética,
> avaliação comportamental) — o indicador dinâmico é **apenas auxiliar**.

## Testes

```bash
pip install pytest
pytest -q
```
