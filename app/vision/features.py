"""Estruturas de dados dos biomarcadores extraídos pela visão computacional."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class BiomarkerFeatures:
    """Conjunto de biomarcadores extraídos de uma sessão de captura.

    Os campos resumem as séries temporais coletadas frame a frame em métricas
    agregadas que alimentam o ClinicalReasoningEngine (BitNet).
    """

    duration_s: float = 0.0
    frames: int = 0
    fps: float = 0.0

    # Tremores (mãos/cabeça) — frequência dominante e amplitude
    tremor_hand_hz: float = 0.0
    tremor_hand_amplitude: float = 0.0
    tremor_head_hz: float = 0.0

    # Microexpressões — taxa de eventos e intensidade média
    microexpression_rate: float = 0.0
    microexpression_intensity: float = 0.0

    # Eye tracking
    blink_rate_per_min: float = 0.0
    gaze_dispersion: float = 0.0
    saccade_rate: float = 0.0

    # Simetria facial (0 = perfeitamente simétrico, 1 = muito assimétrico)
    facial_asymmetry: float = 0.0

    # Movimentos corporais
    body_movement_index: float = 0.0
    postural_sway: float = 0.0

    # Marcadores compostos (TEA, Parkinson, Alzheimer, Down)
    gaze_center_ratio: float = 0.0       # fração do tempo com olhar ao centro (contato visual)
    expression_amplitude: float = 0.0    # amplitude média de ativação facial (expressividade)
    movement_periodicity: float = 0.0    # força de periodicidade do movimento (repetitivo/estereotipia)
    mouth_open_ratio: float = 0.0        # fração do tempo com boca entreaberta (hipotonia)

    # Séries temporais brutas para processamento paralelo (Dask)
    time_series: dict[str, list[float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # Não serializar as séries longas no resumo textual enviado ao LLM
        d.pop("time_series", None)
        return d

    def summary_text(self) -> str:
        """Resumo legível dos biomarcadores para o prompt do LLM."""
        d = self.to_dict()
        lines = [f"- {k}: {v:.4f}" if isinstance(v, float) else f"- {k}: {v}"
                 for k, v in d.items()]
        return "\n".join(lines)
