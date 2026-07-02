# Política de Segurança

## Versões suportadas

Este projeto está em desenvolvimento ativo (pré-1.0). Apenas a branch `main`
recebe correções de segurança.

## Reportando uma vulnerabilidade

**Não abra uma issue pública para vulnerabilidades de segurança.**

Dado que este software processa dados biométricos e de saúde (mesmo que
localmente, sem envio a servidores), leve a sério qualquer falha que possa:

- expor dados de sessão/relatórios armazenados em `data/*.db`;
- permitir execução de código arbitrário via entrada da webcam, PDF exportado
  ou modelo GGUF carregado;
- comprometer o isolamento "100% local/offline" do app (ex: exfiltração de
  dados via dependência comprometida).

Reporte de forma privada:

1. Envie um e-mail para o mantenedor (ver perfil do GitHub do autor) com o
   assunto `[SECURITY] visao-clinica: <resumo curto>`.
2. Inclua passos de reprodução, versão/commit afetado e impacto potencial.
3. Você receberá uma confirmação em até 5 dias úteis.

Pedimos um período de *responsible disclosure* de 90 dias antes de divulgação
pública, para que uma correção possa ser lançada.

## Escopo

Dentro do escopo: o código-fonte deste repositório (`app/`, `scripts/`,
empacotamento do `.app`).

Fora do escopo: vulnerabilidades em dependências de terceiros (PySide6,
OpenCV, MediaPipe, bitnet.cpp, transformers) — reporte-as diretamente ao
projeto upstream. Vulnerabilidades conhecidas em dependências são monitoradas
via Dependabot (veja `.github/dependabot.yml`).
