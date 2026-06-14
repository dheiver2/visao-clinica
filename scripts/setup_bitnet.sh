#!/usr/bin/env bash
# Clona e compila o bitnet.cpp oficial e converte o modelo
# microsoft/bitnet-b1.58-2B-4T para GGUF i2_s (inferência nativa 1,58-bit).
#
# Uso:
#   bash scripts/setup_bitnet.sh
#
# Ao final, exporte (ou adicione ao seu shell):
#   export BITNET_CPP_BIN=<repo>/build/bin/llama-cli
#   export BITNET_MODEL_GGUF=<repo>/models/bitnet-b1.58-2B-4T/ggml-model-i2_s.gguf
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR_DIR="${ROOT_DIR}/vendor"
BITNET_DIR="${VENDOR_DIR}/BitNet"
MODEL_HF="microsoft/BitNet-b1.58-2B-4T-gguf"   # repo com GGUF oficial
MODEL_DIR="${BITNET_DIR}/models/BitNet-b1.58-2B-4T"

echo ">> Verificando dependências (git, cmake, python3)..."
for bin in git cmake python3; do
  command -v "$bin" >/dev/null 2>&1 || { echo "ERRO: '$bin' não encontrado."; exit 1; }
done

mkdir -p "${VENDOR_DIR}"

if [ ! -d "${BITNET_DIR}/.git" ]; then
  echo ">> Clonando bitnet.cpp..."
  git clone --recursive https://github.com/microsoft/BitNet.git "${BITNET_DIR}"
else
  echo ">> bitnet.cpp já presente; atualizando..."
  git -C "${BITNET_DIR}" pull --ff-only || true
  git -C "${BITNET_DIR}" submodule update --init --recursive
fi

echo ">> Instalando requisitos Python do bitnet.cpp..."
python3 -m pip install -q -r "${BITNET_DIR}/requirements.txt" || true
python3 -m pip install -q huggingface_hub

echo ">> Baixando o modelo GGUF oficial (${MODEL_HF})..."
python3 - <<PY
from huggingface_hub import snapshot_download
snapshot_download(repo_id="${MODEL_HF}", local_dir="${MODEL_DIR}")
print("Modelo em: ${MODEL_DIR}")
PY

echo ">> Configurando o ambiente (setup_env.py: compila e prepara o GGUF i2_s)..."
# O script oficial compila o llama.cpp/bitnet e gera o GGUF quantizado i2_s.
python3 "${BITNET_DIR}/setup_env.py" \
  -md "${MODEL_DIR}" \
  -q i2_s || {
    echo ">> setup_env.py falhou; tentando build manual via cmake...";
    cmake -S "${BITNET_DIR}" -B "${BITNET_DIR}/build" -DCMAKE_BUILD_TYPE=Release;
    cmake --build "${BITNET_DIR}/build" --config Release -j;
  }

GGUF="$(find "${MODEL_DIR}" -name '*i2_s*.gguf' | head -n1 || true)"
BIN="$(find "${BITNET_DIR}/build" -name 'llama-cli' -type f 2>/dev/null | head -n1 || true)"

echo
echo "========================================================================"
echo " Setup concluído. Adicione ao seu shell:"
echo
[ -n "${BIN}" ]  && echo "   export BITNET_CPP_BIN=${BIN}"   || echo "   export BITNET_CPP_BIN=<repo>/build/bin/llama-cli   # ajuste o caminho"
[ -n "${GGUF}" ] && echo "   export BITNET_MODEL_GGUF=${GGUF}" || echo "   export BITNET_MODEL_GGUF=${MODEL_DIR}/ggml-model-i2_s.gguf  # ajuste"
echo "========================================================================"
