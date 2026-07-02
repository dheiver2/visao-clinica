# Checklist de Release

## Versionamento

Segue [SemVer](https://semver.org/lang/pt-BR/). Enquanto o projeto estiver
pré-1.0 (`0.x.y`), mudanças que quebram compatibilidade podem ocorrer em
versões minor.

## Passo a passo

1. **Testes e lint limpos**
   ```bash
   pytest -q --cov=app
   ruff check .
   ```
2. **Atualizar `CHANGELOG.md`** com as mudanças da versão (mover itens de
   "Não lançado" para uma nova seção com a versão e data).
3. **Bump de versão** em `pyproject.toml`.
4. **Tag anotada**
   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z"
   git push origin vX.Y.Z
   ```
5. **Build do app macOS**
   ```bash
   bash scripts/make_app_bundle.sh
   ```
6. **Gerar checksum do artefato** antes de anexar ao release (o `.app`/`.dmg`
   não é assinado nem notarizado — usuários verão aviso do Gatekeeper; o
   checksum permite que verifiquem integridade mesmo assim):
   ```bash
   shasum -a 256 "dist/Visão Clínica.app" > dist/CHECKSUMS.txt
   # ou, se empacotado em .dmg:
   shasum -a 256 dist/*.dmg >> dist/CHECKSUMS.txt
   ```
7. **Publicar o GitHub Release** na tag criada, anexando o artefato e o
   `CHECKSUMS.txt`, com:
   - resumo das mudanças (do CHANGELOG);
   - aviso de que o binário não é assinado/notarizado pela Apple — instrução
     de como abrir mesmo assim (`clique com botão direito → Abrir` na
     primeira vez, ou `xattr -d com.apple.quarantine`);
   - lembrete do disclaimer de não-diagnóstico.
8. **Verificar CI verde** na tag antes de anunciar o release publicamente.

## Assinatura de código (futuro)

Notarização/assinatura Apple exige Apple Developer ID (conta paga). Enquanto
isso não existir, todo release deve deixar isso explícito nas notas de
release para não surpreender usuários finais.
