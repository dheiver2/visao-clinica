# Requisitos do MVP — Visão Clínica

Triagem de saúde por **visão computacional 100% local** (webcam), com raciocínio
clínico determinístico e narrativa opcional por LLM local (BitNet b1.58 2B4T).

> **Aviso:** produto de **apoio e pesquisa**. NÃO é dispositivo médico, não
> fornece diagnóstico e não substitui avaliação profissional. Ver `PRIVACY.md`.

---

## 1. Objetivo do MVP

Entregar um app **desktop macOS nativo**, offline, que a partir de ~12 s de
webcam:

1. extrai biomarcadores por visão computacional (face, olhar, tremor, pele);
2. estima **sinais vitais sem contato** (FC, respiração, VFC, estresse);
3. apresenta **indicadores clínicos de triagem** por condição, com nível de risco;
4. calcula um **score de bem-estar (0–100)**;
5. registra as sessões para **acompanhar tendências** ao longo do tempo.

Tudo processado localmente — nenhum dado sai da máquina.

## 2. Personas

- **Pesquisador/profissional de saúde** — modo *Pesquisa*: painel completo com
  scores, acurácia e racional.
- **Usuário final (bem-estar)** — modo *Triagem*: apenas indicadores relevantes.
- **SST / RH (ocupacional)** — modo *NR-01*: triagem psicossocial voluntária e
  relatório agregado anonimizado por setor.

## 3. Escopo do MVP (incluído)

Plataforma **macOS 12+ (Apple Silicon)**, app nativo `.app` + instalador `.dmg`.

---

## 4. Requisitos funcionais (RF)

### Captura e visão computacional
- **RF-01** — Abrir a webcam com preview contínuo e sobreposição da malha facial.
- **RF-02** — **Captura guiada em tempo real**: orientar posição, distância e
  iluminação do rosto antes/durante a análise (banner no preview).
- **RF-03** — Disparar uma janela de análise de ~12 s, repetível sem reabrir a câmera.
- **RF-04** — Extrair biomarcadores: tremor (mão/cabeça), microexpressões, piscar,
  olhar/saccades, simetria facial, movimento corporal, hipomimia, estereotipia.

### Sinais vitais (rPPG)
- **RF-05** — Estimar **frequência cardíaca** sem contato (rPPG, método POS).
- **RF-06** — Estimar **frequência respiratória** (rpm).
- **RF-07** — Calcular **VFC**: SDNN, RMSSD, pNN50 e balanço autonômico **LF/HF**.
- **RF-08** — Calcular **índice de estresse** (Baevsky) e nível de estresse (%).
- **RF-09** — Exibir os vitais como faixa de destaque no painel.

### Análise clínica
- **RF-10** — Avaliação **determinística e instantânea** por condição, com nível
  (baixo/moderado/alto) e barra de score.
- **RF-11** — Exibir apenas indicadores com **acurácia média/alta** (gating de confiança).
- **RF-12** — Calcular e exibir **score de bem-estar 0–100** com rótulo.
- **RF-13** — *(Opcional)* Narrativa clínica curta via **BitNet local**, em background,
  sem bloquear o resultado determinístico.

### Modo ocupacional (NR-01)
- **RF-14** — Triagem psicossocial voluntária com **consentimento LGPD** por sessão.
- **RF-15** — Gerar **plano de ação** (PDF) e **relatório agregado por setor** anonimizado.

### Histórico e relatórios
- **RF-16** — Persistir cada sessão **offline (SQLite)** — apenas métricas, nunca vídeo.
- **RF-17** — **Histórico & tendências**: gráficos de evolução (bem-estar, FC, estresse)
  e tabela das sessões.
- **RF-18** — Exportar relatório em **PDF** e dados em **CSV**.

### Conformidade para licitação (editais)
- **RF-19** — **Controle de acesso** com perfis (administrador/profissional/
  pesquisador), senha com hash e **timeout de sessão** por inatividade.
- **RF-20** — **Trilha de auditoria (LGPD)** append-only com usuário + data/hora,
  visualizável e exportável em CSV.
- **RF-21** — **Personalização institucional** (nome/CNPJ/logo, responsável técnico)
  com cabeçalho, rodapé e **nº de protocolo** nos relatórios.
- **RF-22** — **Acessibilidade (eMAG/WCAG)**: ajuste de fonte, alto contraste e
  navegação por teclado.
- **RF-23** — **Backup e restauração** de todos os dados locais.

## 5. Requisitos não-funcionais (RNF)

- **RNF-01 (Privacidade)** — 100% offline; **nenhuma** requisição de rede na operação
  clínica. Nenhum frame bruto é salvo — só métricas numéricas agregadas.
- **RNF-02 (Consentimento)** — Aviso de não-diagnóstico + consentimento biométrico
  (LGPD) exibido **antes** de ligar a câmera, em qualquer modo.
- **RNF-03 (Latência)** — Resultado clínico e vitais em **≤ 1 s** após os 12 s de
  captura (determinístico, sem depender do LLM).
- **RNF-04 (Desempenho)** — Captura fluida (≥ ~15 fps) em Mac Apple Silicon sem GPU dedicada.
- **RNF-05 (Robustez)** — Falha do LLM, do PDF ou do histórico **não** interrompe a
  triagem; o painel determinístico é sempre garantido.
- **RNF-06 (Confiabilidade do sinal)** — Bloquear indicadores quando a captura for
  curta, escura ou com pouca detecção de rosto (validação de sessão).
- **RNF-07 (Portabilidade)** — Bundle `.app` autocontido, **sem** depender de Python
  do sistema ou `.venv`; modelo facial embutido (offline na 1ª execução).
- **RNF-08 (Qualidade)** — `pytest` + `ruff` verdes no CI; sem regressões.

## 6. Requisitos técnicos / ambiente

- **Dev:** Python **3.11**, `.venv` do projeto, `./run.sh` (GUI) ou `--cli`.
- **Dependências:** PySide6 ≥ 6.6, OpenCV ≥ 4.9, **MediaPipe == 0.10.14**
  (API `solutions`), NumPy/SciPy; ReportLab (PDF); SQLite (stdlib).
- **LLM (opcional):** BitNet b1.58 2B4T via `bitnet.cpp` (GGUF baixado sob demanda
  para área gravável do usuário); fallback `transformers` 4.x.
- **Build macOS:** `bash scripts/build_macos.sh` → `Visão Clínica.app` (arm64,
  ad-hoc) + `.dmg`. Distribuição externa exige assinatura/notarização (Developer ID).

## 7. Critérios de aceitação do MVP

- [ ] App nativo abre, pede consentimento e ativa a câmera com captura guiada.
- [ ] Uma análise de 12 s retorna painel clínico + faixa de vitais em ≤ 1 s.
- [ ] FC recuperada com erro típico < 8 bpm; respiração < 4 rpm (sinal de boa qualidade).
- [ ] Score de bem-estar exibido quando o sinal é confiável; caso contrário, "sinal insuf.".
- [ ] Sessão salva e visível no Histórico com gráfico de tendência.
- [ ] PDF e CSV gerados com os biomarcadores, vitais e bem-estar.
- [ ] Modo NR-01 exige consentimento e gera plano/relatório.
- [ ] `pytest` (62+) e `ruff` passam.

## 8. Fora de escopo do MVP

- Diagnóstico médico ou certificação como dispositivo médico (ANVISA/FDA).
- SpO₂ e pressão arterial (candidatos ao pós-MVP; exigem validação clínica).
- Versão web/mobile (o produto é **desktop nativo** por decisão de projeto).
- Sincronização em nuvem, multiusuário e telemetria.
- Assinatura/notarização para distribuição fora da máquina de build.

## 9. Roadmap pós-MVP (não exigido agora)

- SpO₂ (ratio-of-ratios) e estimativas cuffless com validação.
- Exportação do histórico e comparação entre períodos.
- Assinatura/notarização + auto-update.
- Empacotamento universal (arm64 + x86_64).
