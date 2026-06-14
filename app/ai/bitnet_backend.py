"""Backends de inferência local para o BitNet b1.58 2B4T.

Backend primário : bitnet.cpp (inferência nativa 1,58-bit — máxima eficiência).
Backend fallback : transformers + torch (com aviso de menor eficiência).

Ambos operam 100% localmente/offline, sem chamadas a serviços externos.
A própria documentação do modelo informa que o uso APENAS via transformers não
entrega todos os ganhos de velocidade/energia da arquitetura nativa; por isso
bitnet.cpp é sempre tentado primeiro.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

MODEL_REPO = "microsoft/bitnet-b1.58-2B-4T"


class LLMBackend(ABC):
    name = "abstract"

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 512,
                 temperature: float = 0.7) -> str: ...


class BitnetCppBackend(LLMBackend):
    """Backend primário usando a CLI/biblioteca oficial bitnet.cpp.

    Espera um binário de inferência (ex.: `llama-cli` compilado em bitnet.cpp)
    e um modelo GGUF i2_s convertido a partir do checkpoint oficial.
    """

    name = "bitnet.cpp"

    def __init__(self, model_path: str | os.PathLike, binary: str | None = None):
        self.model_path = Path(model_path)
        self.binary = binary or os.environ.get("BITNET_CPP_BIN") or shutil.which("llama-cli")
        if not self.binary:
            raise RuntimeError("Binário do bitnet.cpp não encontrado (defina BITNET_CPP_BIN).")
        if not self.model_path.exists():
            raise RuntimeError(f"Modelo GGUF não encontrado: {self.model_path}")

    def generate(self, prompt: str, max_tokens: int = 512,
                 temperature: float = 0.7) -> str:
        cmd = [
            self.binary,
            "-m", str(self.model_path),
            "-p", prompt,
            "-n", str(max_tokens),
            "--temp", str(temperature),
            "-t", str(os.cpu_count() or 4),
            "--no-display-prompt",
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if out.returncode != 0:
            raise RuntimeError(f"bitnet.cpp falhou: {out.stderr[:500]}")
        return out.stdout.strip()


class TransformersBackend(LLMBackend):
    """Backend de fallback. Menos eficiente que bitnet.cpp — usar só se necessário."""

    name = "transformers (fallback)"

    def __init__(self, model_id: str = MODEL_REPO, device: str | None = None):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        # Em GPU usa bfloat16; em CPU o BitNet faz "weight unpacking" e exige float32.
        dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        # transformers <5 usa torch_dtype; >=5 usa dtype. Tenta o moderno e cai p/ legado.
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id, dtype=dtype).to(self.device)
        except TypeError:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id, torch_dtype=dtype).to(self.device)

    def generate(self, prompt: str, max_tokens: int = 512,
                 temperature: float = 0.7) -> str:
        messages = [{"role": "user", "content": prompt}]
        enc = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_tensors="pt",
            return_dict=True)
        # transformers >=5 retorna BatchEncoding (dict); versões antigas, um tensor.
        if hasattr(enc, "to"):
            enc = enc.to(self.device)
        if isinstance(enc, dict) or hasattr(enc, "input_ids"):
            input_ids = enc["input_ids"]
            gen_kwargs = {k: v for k, v in dict(enc).items()}
        else:
            input_ids = enc.to(self.device)
            gen_kwargs = {"input_ids": input_ids}
        prompt_len = input_ids.shape[1]
        with self._torch.no_grad():
            out = self.model.generate(
                **gen_kwargs, max_new_tokens=max_tokens, temperature=temperature,
                do_sample=temperature > 0)
        text = self.tokenizer.decode(out[0][prompt_len:], skip_special_tokens=True)
        return text.strip()


def build_backend(model_gguf: str | os.PathLike | None = None,
                  progress=None,
                  allow_download: bool = True,
                  allow_build: bool = True) -> LLMBackend:
    """Constrói o backend de forma encapsulada (auto-bootstrap), priorizando bitnet.cpp.

    O próprio software localiza/baixa o modelo e localiza/compila o bitnet.cpp via
    ``bootstrap``; só cai para ``transformers`` se o caminho nativo não for possível.
    Nenhuma configuração manual (env/scripts) é exigida do usuário.
    """
    # Caminho explícito tem prioridade; senão, deixa o bootstrap resolver tudo.
    gguf = model_gguf or os.environ.get("BITNET_MODEL_GGUF")
    binary = os.environ.get("BITNET_CPP_BIN")

    if not (gguf and binary):
        from app.ai.bootstrap import bootstrap
        paths = bootstrap(progress=progress, allow_download=allow_download,
                          allow_build=allow_build)
        gguf = gguf or (str(paths.gguf) if paths.gguf else None)
        binary = binary or (str(paths.binary) if paths.binary else None)

    if gguf and binary:
        try:
            return BitnetCppBackend(gguf, binary=binary)
        except Exception as e:  # noqa: BLE001 - fallback intencional com aviso
            print(f"[AVISO] bitnet.cpp indisponível ({e}). "
                  f"Usando fallback transformers (menor eficiência).")
    else:
        print("[AVISO] Backend nativo bitnet.cpp não disponível; usando fallback "
              "transformers (menor eficiência).")
    return TransformersBackend()
