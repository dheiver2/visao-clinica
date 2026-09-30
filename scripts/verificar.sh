#!/usr/bin/env bash
# Verificacao local (substitui o GitHub Actions): mesmos passos do antigo CI.
# Roda no pre-push (sem os passos lentos) e manualmente: bash scripts/verificar.sh
set -euo pipefail
cd "$(dirname "$0")/.."
passo() { printf '\n▶ %s\n' "$1"; eval "$1"; }
passo 'swift build -c release'
passo '"$(swift build -c release --show-bin-path)/VisaoClinica" --selftest'
printf '\n✅ Tudo certo\n'
