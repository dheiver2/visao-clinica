---
name: Falso positivo / falso negativo clínico
about: Reportar um indicador de triagem que pareceu incorreto
title: "[CLÍNICO] "
labels: clinical-accuracy
assignees: ''
---

⚠️ **Não inclua nomes, imagens, vídeos ou qualquer dado que identifique a
pessoa avaliada.** Descreva apenas os números/indicadores exibidos pelo app.

**Indicador reportado**
Qual condição/indicador (ex: "perfil parkinsoniano", "hipomimia")?

**Score e confiança exibidos pelo app**
Ex: score 0.72, confiança "média".

**Por que você acredita que é um falso positivo/negativo**
Ex: avaliação profissional prévia, ausência de qualquer sintoma conhecido,
condição de iluminação/câmera atípica, etc. (sem dados identificáveis).

**Condições da captura**
- Iluminação: [boa / ruim / variável]
- Qualidade de sinal reportada pelo app (`signal_quality`), se souber
- Duração da sessão
- Modo: [Pesquisa / Triagem]

**Isso ajuda a**
Calibrar os limiares heurísticos em `app/clinical/conditions.py` — reportes
concretos (mesmo sem contexto identificável) são muito úteis, já que os
indicadores atuais não são calibrados em dataset clínico real.
