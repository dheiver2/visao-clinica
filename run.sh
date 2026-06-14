#!/usr/bin/env bash
# Launcher único — usa SEMPRE o Python do .venv do projeto, sem depender de
# `source .venv/bin/activate` nem do `python` global. Resolve o "não inicia".
#
# Uso:
#   ./run.sh                      # GUI (modo Pesquisa)
#   ./run.sh --mode triagem       # GUI simplificada
#   ./run.sh --cli --duration 30  # linha de comando
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${DIR}/.venv/bin/python"

if [ ! -x "${PY}" ]; then
  echo "ERRO: ambiente não encontrado em ${DIR}/.venv"
  echo "Crie com:  python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

export TOKENIZERS_PARALLELISM=false   # silencia avisos de fork do tokenizer
cd "${DIR}"
exec "${PY}" -m app.main "$@"
