## O que este PR faz

## Checklist
- [ ] `pytest -q` passa localmente
- [ ] `ruff check .` sem erros
- [ ] Se mudei limiares clínicos (`app/clinical/conditions.py`), expliquei a motivação acima
- [ ] Se adicionei biomarcador, citei referência em `REFERENCES.md`
- [ ] Nenhuma chamada de rede nova fora do fluxo de download do modelo (`app/ai/bootstrap.py`)
- [ ] Atualizei `CHANGELOG.md`
