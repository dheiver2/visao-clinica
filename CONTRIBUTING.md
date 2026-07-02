# Contribuindo com o Visão Clínica

Obrigado pelo interesse em contribuir! Este é um projeto de pesquisa/triagem
em visão computacional aplicada à saúde — contribuições passam por um nível
extra de cuidado por causa disso.

## Antes de abrir um PR

1. Abra uma issue descrevendo o problema ou a proposta antes de codar
   mudanças grandes (novos biomarcadores, novos indicadores clínicos, mudança
   de arquitetura do backend LLM).
2. Para mudanças pequenas (bugfix, docs, testes), pode ir direto ao PR.

## Ambiente de desenvolvimento

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov ruff pre-commit
pre-commit install
```

## Rodando os testes

```bash
pytest -q --cov=app --cov-report=term-missing
```

Todo PR que altera `app/` deve manter ou aumentar a cobertura de testes dos
módulos tocados. Módulos com saída clínica (`app/clinical/`,
`app/vision/`) exigem testes cobrindo casos de sinal ruim/baixa confiança,
não só o caminho feliz.

## Lint e formatação

```bash
ruff check .
ruff format .
```

O `pre-commit` roda isso automaticamente antes de cada commit.

## Diretrizes específicas do domínio clínico

- **Nunca** transforme um indicador probabilístico de triagem em linguagem de
  diagnóstico definitivo (evite "detecta X", prefira "sinais compatíveis com
  X"). Veja `DISCLAIMER` em `app/__init__.py` e `app/clinical/reasoning_engine.py`.
- Novos biomarcadores/indicadores devem citar a referência científica em
  `REFERENCES.md`.
- Mudanças em limiares heurísticos (`app/clinical/conditions.py`) devem
  explicar a motivação no PR — eles não são calibrados em dataset clínico
  real, então mudanças silenciosas de sensibilidade são especialmente
  arriscadas.
- Não adicione nenhuma chamada de rede fora do fluxo já existente de download
  do modelo (`app/ai/bootstrap.py`). O app é 100% local/offline por design —
  veja `PRIVACY.md`.

## Estilo de commit

Mensagens curtas e descritivas, no imperativo (ex: `Adiciona indicador de
piscar reduzido ao painel de triagem`). PRs pequenos e focados são
preferíveis a PRs grandes que misturam refactor + feature.

## Código de conduta

Este projeto segue o [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
