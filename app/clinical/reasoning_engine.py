"""ClinicalReasoningEngine — cérebro clínico do sistema (BitNet b1.58 2B4T).

Encapsula toda a interação com o LLM local. Não realiza chamadas externas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app import DISCLAIMER
from app.ai.bitnet_backend import LLMBackend, build_backend
from app.vision.features import BiomarkerFeatures


@dataclass
class ClinicalAnalysis:
    summary: str = ""
    hypotheses: list[str] = field(default_factory=list)
    influential_variables: list[str] = field(default_factory=list)
    risk_level: str = "indeterminado"  # baixo | moderado | alto | indeterminado
    raw: str = ""

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["disclaimer"] = DISCLAIMER
        return d


_SYSTEM = (
    "Você é um motor de raciocínio clínico de apoio à pesquisa. Analisa biomarcadores "
    "extraídos por visão computacional (tremores, microexpressões, eye tracking, simetria "
    "facial, movimentos corporais). Produz hipóteses PROBABILÍSTICAS, nunca diagnósticos. "
    "Responda SEMPRE em português do Brasil e em JSON válido."
)


class ClinicalReasoningEngine:
    """Carrega e opera o BitNet localmente; interpreta features e gera relatórios."""

    def __init__(self, model_gguf: str | None = None):
        self._model_gguf = model_gguf
        self._backend: LLMBackend | None = None
        self._last: ClinicalAnalysis | None = None

    # -- ciclo de vida -----------------------------------------------------------

    def load_model(self, progress=None) -> None:
        """Carrega o BitNet b1.58 2B4T de forma encapsulada (auto-bootstrap).

        O próprio software resolve modelo e binário do bitnet.cpp; cai para
        transformers apenas se o caminho nativo não for possível. ``progress`` é
        uma função opcional callback(str) para reportar o andamento na UI/CLI.
        """
        if self._backend is None:
            self._backend = build_backend(self._model_gguf, progress=progress)

    @property
    def backend_name(self) -> str:
        return self._backend.name if self._backend else "não carregado"

    # -- análise -----------------------------------------------------------------

    def analyze_features(self, features: BiomarkerFeatures) -> ClinicalAnalysis:
        """Interpreta os biomarcadores e gera hipóteses clínicas probabilísticas."""
        if self._backend is None:
            self.load_model()
        prompt = (
            f"{_SYSTEM}\n\nBiomarcadores da sessão:\n{features.summary_text()}\n\n"
            "Correlacione os padrões motores, faciais e oculares e devolva um JSON com as "
            "chaves: summary (string), hypotheses (lista de strings), "
            "influential_variables (lista das variáveis mais determinantes), "
            "risk_level (baixo|moderado|alto|indeterminado)."
        )
        raw = self._backend.generate(prompt, max_tokens=768, temperature=0.4)
        analysis = self._parse(raw)
        self._last = analysis
        return analysis

    def generate_report(self, analysis: ClinicalAnalysis) -> str:
        """Gera relatório técnico textual a partir da análise."""
        if self._backend is None:
            self.load_model()
        prompt = (
            f"{_SYSTEM}\n\nEscreva um relatório técnico em texto corrido (não JSON) para "
            "pesquisadores e profissionais de saúde, a partir desta análise:\n"
            f"{json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2)}\n\n"
            "Inclua: contexto, achados, hipóteses probabilísticas, variáveis determinantes "
            "e limitações. Finalize com o aviso de não-diagnóstico."
        )
        body = self._backend.generate(prompt, max_tokens=900, temperature=0.5)
        return f"{body}\n\n---\n{DISCLAIMER}"

    def explain_decision(self) -> str:
        """Explica quais variáveis mais influenciaram o último resultado."""
        if not self._last:
            return "Nenhuma análise realizada ainda."
        if self._backend is None:
            self.load_model()
        prompt = (
            f"{_SYSTEM}\n\nExplique, em linguagem clara, por que estas variáveis foram as "
            f"mais influentes no resultado (risco: {self._last.risk_level}):\n"
            f"{', '.join(self._last.influential_variables) or 'não especificadas'}.\n"
            "Responda em texto corrido."
        )
        return self._backend.generate(prompt, max_tokens=512, temperature=0.5)

    # -- helpers -----------------------------------------------------------------

    @staticmethod
    def _parse(raw: str) -> ClinicalAnalysis:
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            try:
                data = json.loads(raw[start:end + 1])
                return ClinicalAnalysis(
                    summary=str(data.get("summary", "")),
                    hypotheses=list(data.get("hypotheses", [])),
                    influential_variables=list(data.get("influential_variables", [])),
                    risk_level=str(data.get("risk_level", "indeterminado")),
                    raw=raw,
                )
            except json.JSONDecodeError:
                pass
        return ClinicalAnalysis(summary=raw.strip(), raw=raw)
