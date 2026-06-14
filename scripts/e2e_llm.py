"""E2E do LLM real: bootstrap -> carga do BitNet -> análise -> relatório.

Usa biomarcadores sintéticos para não depender da webcam. Exercita o caminho
real de inferência (bitnet.cpp se disponível; senão transformers).
"""
import time

from app.clinical.reasoning_engine import ClinicalReasoningEngine
from app.vision.features import BiomarkerFeatures

feats = BiomarkerFeatures(
    duration_s=30.0, frames=900, fps=30.0,
    tremor_hand_hz=5.4, tremor_hand_amplitude=0.012, tremor_head_hz=1.1,
    microexpression_rate=8.0, microexpression_intensity=6.2,
    blink_rate_per_min=22.0, gaze_dispersion=0.18, saccade_rate=140.0,
    facial_asymmetry=0.21, body_movement_index=0.05, postural_sway=0.05,
)

eng = ClinicalReasoningEngine()
t0 = time.monotonic()
print(">> Carregando modelo (bootstrap encapsulado)...")
eng.load_model(progress=lambda m: print("  ·", m))
print(">> Backend:", eng.backend_name)

print(">> Analisando biomarcadores...")
analysis = eng.analyze_features(feats)
print("   risk_level:", analysis.risk_level)
print("   hipoteses:", analysis.hypotheses[:3])
print("   variaveis influentes:", analysis.influential_variables[:5])

print(">> Explicação:")
print("  ", eng.explain_decision()[:400])

print(f">> Concluído em {time.monotonic()-t0:.0f}s")
