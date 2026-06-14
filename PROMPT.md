# Prompt — Sistema de Visão Computacional Clínica com IA Local (BitNet b1.58 2B4T)

> **Aviso científico (deve aparecer no software e em todo relatório):**
> Esta é uma **ferramenta de triagem e apoio à pesquisa**. Os resultados **não constituem
> diagnóstico médico** e **não substituem** a avaliação de profissionais de saúde
> especializados.

---

## Objetivo geral

Desenvolver uma aplicação **desktop 100% local e offline** que capture sinais por webcam,
extraia biomarcadores por visão computacional e utilize uma **LLM local nativa** para
interpretação multimodal, raciocínio clínico probabilístico e geração de relatórios.

A privacidade dos dados médicos é requisito inegociável: **nenhum dado** (imagem, vídeo,
feature ou texto) pode sair da máquina ou depender de APIs/serviços externos em tempo de
execução.

---

## Módulo de Inteligência Artificial Local — BitNet b1.58 2B4T (obrigatório)

O **cérebro** do sistema é o modelo
[`microsoft/bitnet-b1.58-2B-4T`](https://huggingface.co/microsoft/bitnet-b1.58-2B-4T),
uma LLM **nativa de 1,58 bits** projetada para alta eficiência computacional. Ele executa
**localmente, sem dependência de APIs externas**.

### Requisito de runtime (importante)

Para aproveitar de fato a eficiência da arquitetura BitNet (velocidade e consumo energético),
o projeto **deve priorizar a implementação oficial `bitnet.cpp`**. A própria documentação do
modelo informa que o uso **apenas via `transformers` não entrega** todos os ganhos da
arquitetura nativa 1,58-bit. Portanto:

1. **Backend primário (obrigatório):** integração com **`bitnet.cpp`** (inferência nativa
   1,58-bit em CPU; suporte a GPU quando disponível). O modelo deve ser carregado no formato
   recomendado pela implementação oficial (ex.: GGUF i2_s convertido a partir do checkpoint
   oficial).
2. **Backend de fallback (opcional):** `transformers` + PyTorch, apenas para ambientes onde
   `bitnet.cpp` não esteja disponível, com **aviso explícito** ao usuário de que o desempenho
   e a eficiência serão inferiores.
3. O download/conversão do modelo deve ocorrer **uma única vez**, ficar **cacheado localmente**
   e funcionar offline nas execuções seguintes.

### Objetivos do LLM

O BitNet b1.58 2B4T deve:

- Interpretar os biomarcadores extraídos pela visão computacional.
- Correlacionar padrões **motores, faciais e oculares**.
- Gerar **hipóteses clínicas probabilísticas**.
- Produzir **relatórios técnicos** para pesquisadores e profissionais de saúde.
- **Explicar** quais variáveis mais influenciaram cada resultado (interpretabilidade).
- Permitir **interação conversacional** com o usuário e com o pesquisador.

---

## Arquitetura proposta

```
Webcam
    │
    ▼
OpenCV + MediaPipe (Face Mesh + Pose + Hands)
    │
    ▼
Extração de Features
    │
    ├── Tremores
    ├── Microexpressões
    ├── Eye Tracking
    ├── Simetria Facial
    ├── Movimentos Corporais
    └── Séries Temporais
    │
    ▼
BitNet b1.58 2B4T  (via bitnet.cpp — LLM local nativo 1,58-bit)
    │
    ▼
Motor de Inferência Clínica
    │
    ▼
Dashboard + Relatório PDF + Exportação CSV
```

---

## Camada de raciocínio clínico (Python)

O sistema deve possuir a camada `ClinicalReasoningEngine`, que encapsula toda a interação
com o BitNet via `bitnet.cpp`:

```python
class ClinicalReasoningEngine:
    """
    Cérebro clínico do sistema.
    Carrega e opera o BitNet b1.58 2B4T localmente (backend primário: bitnet.cpp;
    fallback opcional: transformers). Não realiza chamadas a serviços externos.
    """

    def load_model(self):
        """
        Carrega o BitNet b1.58 2B4T localmente.
        - Backend primário: bitnet.cpp (modelo GGUF i2_s).
        - Fallback: transformers + torch (com aviso de menor eficiência).
        Deve funcionar 100% offline após o primeiro setup.
        """
        pass

    def analyze_features(self, features):
        """
        Recebe os biomarcadores extraídos pela visão computacional
        (tremores, microexpressões, eye tracking, simetria facial, movimentos
        corporais, séries temporais) e produz uma análise multimodal correlacionada,
        com hipóteses clínicas probabilísticas.
        """
        pass

    def generate_report(self, analysis):
        """
        Gera relatório técnico (texto estruturado) a partir da análise,
        destinado a pesquisadores e profissionais de saúde, sempre incluindo
        o aviso científico de não-diagnóstico.
        """
        pass

    def explain_decision(self):
        """
        Explica quais variáveis/biomarcadores mais influenciaram cada resultado
        (interpretabilidade do raciocínio clínico).
        """
        pass
```

---

## Requisitos técnicos

- **Python 3.12+**
- **PySide6** ou **PyQt6** (interface desktop)
- **OpenCV**
- **MediaPipe** (Face Mesh, Pose, Hands)
- **NumPy**
- **PyTorch** (backend de fallback)
- **Transformers** (backend de fallback)
- **`bitnet.cpp`** — implementação oficial da inferência nativa BitNet (**backend primário**)
- **SQLite** (persistência local de sessões e resultados)
- **ReportLab** (geração de PDF)
- **Dask** (processamento paralelo das séries temporais/features)
- Suporte a **CPU e GPU**

---

## Modos de execução

### Modo Pesquisa
- Exibe **todas** as métricas e biomarcadores.
- Mostra o raciocínio do BitNet e a explicação das variáveis mais influentes.

### Modo Triagem
- Interface **simplificada**.
- Gera apenas **indicadores de risco** (sem expor todas as métricas brutas).

---

## Requisitos não-funcionais

1. **Privacidade / Offline:** operação **100% local**; nenhum dado sai da máquina; nenhuma
   dependência de serviço externo em runtime.
2. **Eficiência:** priorizar `bitnet.cpp` para extrair os ganhos de velocidade e consumo
   energético da arquitetura 1,58-bit.
3. **Interpretabilidade:** toda saída clínica deve ser acompanhada da explicação das variáveis
   determinantes.
4. **Transparência científica:** o aviso de "ferramenta de triagem / não-diagnóstico" deve
   estar visível na UI e em todo relatório (PDF/CSV).
