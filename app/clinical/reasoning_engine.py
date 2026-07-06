"""ClinicalReasoningEngine — cérebro clínico do sistema (BitNet b1.58 2B4T).

Encapsula toda a interação com o LLM local. Não realiza chamadas externas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app import DISCLAIMER
from app.ai.bitnet_backend import LLMBackend, build_backend
from app.clinical.conditions import ConditionResult, evaluate_conditions
from app.vision.features import BiomarkerFeatures


@dataclass
class ClinicalAnalysis:
    summary: str = ""
    hypotheses: list[str] = field(default_factory=list)
    influential_variables: list[str] = field(default_factory=list)
    risk_level: str = "indeterminado"  # baixo | moderado | alto | indeterminado
    conditions: list[ConditionResult] = field(default_factory=list)
    wellness: dict = field(default_factory=dict)   # score de bem-estar 0–100
    raw: str = ""

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["conditions"] = [c.to_dict() for c in self.conditions]
        d["disclaimer"] = DISCLAIMER
        return d

    @property
    def displayable_conditions(self) -> list[ConditionResult]:
        """Apenas indicadores com acurácia média ou alta (oculta baixa confiança)."""
        from app.clinical.validation import is_displayable
        return [c for c in self.conditions if is_displayable(c.confidence)]

    @property
    def top_conditions(self) -> list[ConditionResult]:
        """Condições exibíveis (acurácia média/alta) com nível ao menos moderado."""
        return [c for c in self.displayable_conditions
                if c.level in ("moderado", "alto")]


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

    def analyze_features(self, features: BiomarkerFeatures,
                         use_llm: bool = True) -> ClinicalAnalysis:
        """Avalia o painel clínico (garantido) e enriquece com o raciocínio do BitNet.

        A avaliação por condição é determinística e SEMPRE preenchida — o LLM só
        acrescenta narrativa/hipóteses. Se o LLM falhar ou for desligado, a análise
        ainda retorna o painel completo de doenças.
        """
        analysis = self.screen(features)          # instantâneo e determinístico
        if use_llm:
            self.enrich_with_llm(analysis, features)
        return analysis

    def screen(self, features: BiomarkerFeatures) -> ClinicalAnalysis:
        """Avaliação clínica INSTANTÂNEA (sem LLM) — preciso e determinístico.

        Esta é a saída clínica primária. Não depende do modelo e roda em ms.
        """
        from dataclasses import asdict

        from app.clinical.wellness import compute_wellness

        conditions = evaluate_conditions(features)
        order = {"indeterminado": -1, "baixo": 0, "moderado": 1, "alto": 2}
        risk = max((c.level for c in conditions),
                   key=lambda lv: order.get(lv, -1), default="indeterminado")
        analysis = ClinicalAnalysis(conditions=conditions, risk_level=risk,
                                    wellness=asdict(compute_wellness(features)))
        # Hipóteses derivadas do painel (garantidas, sem LLM).
        analysis.hypotheses = [
            f"{c.name}: risco {c.level}" for c in analysis.top_conditions]
        analysis.influential_variables = [
            fac for c in analysis.top_conditions for fac in c.factors]
        self._last = analysis
        return analysis

    def enrich_with_llm(self, analysis: ClinicalAnalysis,
                        features: BiomarkerFeatures) -> ClinicalAnalysis:
        """Acrescenta uma narrativa curta do BitNet por cima do painel (opcional).

        Complementar e não-bloqueante por design: deve ser chamado em background.
        Usa orçamento de tokens enxuto para reduzir latência.
        """
        try:
            if self._backend is None:
                self.load_model()
            panel_txt = "\n".join(
                f"- {c.name}: {c.level}" for c in analysis.top_conditions) or "- nenhum"
            prompt = (
                f"{_SYSTEM}\n\nIndicadores de triagem já calculados (mais relevantes):\n"
                f"{panel_txt}\n\nEscreva um resumo clínico de 2–3 frases correlacionando "
                "esses achados. Texto corrido, sem JSON."
            )
            analysis.summary = self._backend.generate(
                prompt, max_tokens=160, temperature=0.4)
        except Exception as e:  # noqa: BLE001 - LLM é complementar, não bloqueia
            analysis.summary = (
                f"[Narrativa do BitNet indisponível: {e}] "
                "Indicadores por condição calculados de forma determinística.")
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
