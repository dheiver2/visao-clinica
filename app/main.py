"""Ponto de entrada.

Uso:
    python -m app.main                # GUI (PySide6) — modo Pesquisa por padrão
    python -m app.main --cli          # pipeline em linha de comando
    python -m app.main --mode triagem # interface/saída simplificada

Variáveis de ambiente:
    BITNET_MODEL_GGUF  caminho do modelo GGUF i2_s (ativa bitnet.cpp)
    BITNET_CPP_BIN     caminho do binário de inferência do bitnet.cpp
"""

from __future__ import annotations

import argparse
import sys

from app import DISCLAIMER


def run_cli(mode: str, duration: float, use_llm: bool = False) -> int:
    from app.clinical.reasoning_engine import ClinicalReasoningEngine
    from app.report.exporter import export_csv, export_pdf
    from app.storage.db import SessionStore
    from app.vision.extractor import FeatureExtractor

    print(DISCLAIMER, "\n")
    extractor = FeatureExtractor()
    if not extractor.available():
        print("OpenCV/MediaPipe indisponíveis — instale as dependências.")
        return 1

    print(f"Capturando {duration:.0f}s pela webcam...")
    features = extractor.capture(duration_s=duration)

    engine = ClinicalReasoningEngine()
    # Resultado clínico instantâneo (determinístico). Narrativa do LLM é opt-in.
    analysis = engine.screen(features)
    if use_llm:
        print("Gerando narrativa do BitNet (pode demorar em CPU)...")
        engine.load_model(progress=lambda m: print(f"  · {m}"))
        engine.enrich_with_llm(analysis, features)

    from app.clinical.validation import accuracy_band, validate_session
    val = validate_session(features)
    print(f"\nNível de risco global: {analysis.risk_level.upper()}")
    print(f"Qualidade do sinal: {features.signal_quality:.0%} "
          f"(face {features.face_detection_rate:.0%})")

    displayable = analysis.displayable_conditions
    if not val.ok or not displayable:
        print("\n⚠ Acurácia insuficiente para exibir indicadores confiáveis:")
        for m in (val.messages or ["Refaça a captura."]):
            print(f"  • {m}")
    else:
        print("\n--- Indicadores clínicos (acurácia média/alta) ---")
        for c in displayable:
            marca = {"alto": "!!", "moderado": " ·", "baixo": "  "}
            print(f" [{marca.get(c.level, '  ')}] {c.name}: {c.level} "
                  f"(score {c.score:.2f} · acurácia {accuracy_band(c.confidence)})")
            if mode != "triagem" and c.factors:
                print(f"        ↳ {c.rationale}")

    if mode != "triagem":
        print("\n--- Biomarcadores ---")
        print(features.summary_text())
        print("\nHipóteses:", analysis.hypotheses)
        # Relatório: usa a narrativa do LLM se gerada, senão um resumo do painel.
        if use_llm and analysis.summary:
            report = analysis.summary
        else:
            report = "Triagem por indicadores determinísticos:\n" + "\n".join(
                f"- {c.name}: {c.level} (score {c.score:.2f})"
                for c in analysis.conditions)
        from app.paths import data_path
        pdf_out = data_path("data", "relatorio.pdf")
        csv_out = data_path("data", "relatorio.csv")
        export_pdf(report, analysis, str(pdf_out))
        export_csv(features, analysis, str(csv_out))
        print(f"Relatórios salvos em {pdf_out} e {csv_out}")

    SessionStore().save(mode, features.to_dict(), analysis.to_dict())
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Triagem por Visão Computacional + BitNet")
    p.add_argument("--cli", action="store_true", help="executa em linha de comando")
    p.add_argument("--mode", choices=["pesquisa", "triagem"], default="pesquisa")
    p.add_argument("--duration", type=float, default=12.0)
    p.add_argument("--narrativa", action="store_true",
                   help="gera a narrativa do BitNet (mais lento)")
    args = p.parse_args(argv)

    if args.cli:
        return run_cli(args.mode, args.duration, use_llm=args.narrativa)

    try:
        from app.ui.main_window import launch_gui
    except Exception as e:  # noqa: BLE001
        print(f"GUI indisponível ({e}). Use --cli.")
        return 1
    return launch_gui(default_mode=args.mode)


if __name__ == "__main__":
    sys.exit(main())
