"""Bootstrap encapsulado do BitNet — executado pelo próprio software.

Ao iniciar, o app resolve sozinho tudo que o LLM local precisa, sem exigir do
usuário scripts externos ou variáveis de ambiente:

1. localiza (ou baixa) o modelo GGUF i2_s oficial em ``models/``;
2. localiza (ou compila) o binário do ``bitnet.cpp`` em ``vendor/``;
3. se o passo nativo não for possível, sinaliza fallback para ``transformers``.

Tudo fica cacheado localmente: após o primeiro uso, funciona 100% offline.
Os caminhos descobertos são resolvidos em runtime — nenhum export manual.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from app.paths import bundled_models_dir, models_dir, user_data_dir

# Downloads e build vão para a área gravável do usuário (o bundle é read-only).
MODELS_DIR = models_dir()
BUNDLED_MODELS_DIR = bundled_models_dir()   # assets .gguf embutidos (se houver)
VENDOR_DIR = user_data_dir() / "vendor"
BITNET_DIR = VENDOR_DIR / "BitNet"

MODEL_GGUF_REPO = "microsoft/BitNet-b1.58-2B-4T-gguf"
BITNET_GIT = "https://github.com/microsoft/BitNet.git"

ProgressFn = Callable[[str], None]


@dataclass
class BitnetPaths:
    """Resultado do bootstrap: o que está disponível para inferência."""
    gguf: Path | None = None
    binary: Path | None = None

    @property
    def native_ready(self) -> bool:
        return bool(self.gguf and self.binary and self.gguf.exists() and self.binary.exists())


def _log(progress: ProgressFn | None, msg: str) -> None:
    if progress:
        progress(msg)
    else:
        print(f"[bootstrap] {msg}")


# -- modelo GGUF ----------------------------------------------------------------

def _find_local_gguf() -> Path | None:
    # 1) override explícito por env (opcional, não obrigatório)
    env = os.environ.get("BITNET_MODEL_GGUF")
    if env and Path(env).exists():
        return Path(env)
    # 2) qualquer GGUF i2_s já presente (bundle ou área do usuário)
    for base in (BUNDLED_MODELS_DIR, MODELS_DIR, BITNET_DIR):
        if base.exists():
            for p in base.rglob("*.gguf"):
                if "i2_s" in p.name.lower():
                    return p
    # 3) qualquer GGUF como último recurso
    for base in (BUNDLED_MODELS_DIR, MODELS_DIR, BITNET_DIR):
        if base.exists():
            hits = list(base.rglob("*.gguf"))
            if hits:
                return hits[0]
    return None


def ensure_model(progress: ProgressFn | None = None,
                 allow_download: bool = True) -> Path | None:
    """Garante o GGUF localmente; baixa do Hugging Face na 1ª vez, se permitido."""
    local = _find_local_gguf()
    if local:
        _log(progress, f"Modelo encontrado: {local.name}")
        return local
    if not allow_download:
        _log(progress, "Modelo ausente e download desabilitado.")
        return None
    try:
        from huggingface_hub import snapshot_download
    except Exception:
        _log(progress, "huggingface_hub indisponível — instale com "
                        "'pip install huggingface_hub' para permitir o "
                        "download automático do modelo (ou baixe manualmente "
                        f"'{MODEL_GGUF_REPO}' para {MODELS_DIR}).")
        return None
    _log(progress, f"Baixando modelo GGUF oficial ({MODEL_GGUF_REPO})…")
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target = MODELS_DIR / "BitNet-b1.58-2B-4T"
    try:
        snapshot_download(repo_id=MODEL_GGUF_REPO, local_dir=str(target),
                          allow_patterns=["*i2_s*.gguf", "*.gguf"])
    except Exception as e:  # noqa: BLE001
        hint = _download_failure_hint(e)
        _log(progress, f"Falha ao baixar o modelo: {e}{hint}")
        return None
    return _find_local_gguf()


def _download_failure_hint(exc: Exception) -> str:
    """Traduz erros comuns de download em orientação acionável para o usuário."""
    msg = str(exc).lower()
    if "connection" in msg or "network" in msg or "timeout" in msg or "resolve" in msg:
        return (" — verifique sua conexão com a internet. O download só é "
                "necessário na primeira execução; o app funciona offline depois.")
    if "disk" in msg or "space" in msg or "errno 28" in msg:
        return (f" — verifique espaço em disco livre em {MODELS_DIR} "
                "(o modelo GGUF ocupa alguns GB).")
    if "401" in msg or "403" in msg or "unauthorized" in msg or "gated" in msg:
        return (" — o repositório pode exigir aceite de termos no Hugging Face; "
                f"acesse https://huggingface.co/{MODEL_GGUF_REPO} logado e aceite, "
                "ou faça login local com 'huggingface-cli login'.")
    return " — tente novamente; se persistir, baixe o modelo manualmente (veja README.md)."


# -- binário bitnet.cpp ---------------------------------------------------------

def _find_local_binary() -> Path | None:
    env = os.environ.get("BITNET_CPP_BIN")
    if env and Path(env).exists():
        return Path(env)
    which = shutil.which("llama-cli")
    if which:
        return Path(which)
    if BITNET_DIR.exists():
        for name in ("llama-cli", "main"):
            hits = list(BITNET_DIR.rglob(name))
            hits = [h for h in hits if h.is_file() and os.access(h, os.X_OK)]
            if hits:
                return hits[0]
    return None


def ensure_binary(progress: ProgressFn | None = None,
                  allow_build: bool = True) -> Path | None:
    """Garante o binário do bitnet.cpp; clona+compila na 1ª vez, se permitido.

    A compilação é pesada e pode falhar (sem toolchain). Em caso de falha,
    retorna None e o sistema usa o fallback transformers — sem interromper o app.
    """
    found = _find_local_binary()
    if found:
        _log(progress, f"bitnet.cpp encontrado: {found}")
        return found
    if not allow_build:
        return None
    for tool in ("git", "cmake"):
        if not shutil.which(tool):
            _log(progress, f"'{tool}' ausente — pulando build nativo do bitnet.cpp "
                            f"(instale com 'brew install {tool}' para habilitar o backend "
                            "nativo, mais rápido; o app segue funcional via fallback "
                            "transformers, mais lento).")
            return None
    try:
        if not (BITNET_DIR / ".git").exists():
            _log(progress, "Clonando bitnet.cpp…")
            VENDOR_DIR.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "clone", "--recursive", BITNET_GIT, str(BITNET_DIR)],
                           check=True, capture_output=True, text=True, timeout=900)
        _log(progress, "Compilando bitnet.cpp (pode demorar)…")
        build = BITNET_DIR / "build"
        subprocess.run(["cmake", "-S", str(BITNET_DIR), "-B", str(build),
                        "-DCMAKE_BUILD_TYPE=Release"],
                       check=True, capture_output=True, text=True, timeout=1800)
        subprocess.run(["cmake", "--build", str(build), "--config", "Release", "-j"],
                       check=True, capture_output=True, text=True, timeout=3600)
    except Exception as e:  # noqa: BLE001
        _log(progress, f"Build nativo falhou ({e}); usará fallback transformers.")
        return None
    return _find_local_binary()


# -- orquestração ---------------------------------------------------------------

def bootstrap(progress: ProgressFn | None = None,
              allow_download: bool = True,
              allow_build: bool = True) -> BitnetPaths:
    """Resolve modelo + binário de forma encapsulada. Nunca lança: degrada para fallback."""
    gguf = ensure_model(progress, allow_download=allow_download)
    binary = ensure_binary(progress, allow_build=allow_build) if gguf else None
    paths = BitnetPaths(gguf=gguf, binary=binary)
    if paths.native_ready:
        _log(progress, "BitNet nativo (bitnet.cpp) pronto.")
    elif gguf:
        _log(progress, "GGUF pronto, sem binário nativo → fallback transformers.")
    else:
        _log(progress, "Sem GGUF local → fallback transformers (baixa o modelo).")
    return paths
