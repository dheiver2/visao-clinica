# Privacidade e Tratamento de Dados (LGPD)

O Visão Clínica processa **dados biométricos e de saúde** (imagens de webcam,
landmarks faciais/corporais e hipóteses clínicas probabilísticas derivadas
deles). Estes são dados sensíveis nos termos do art. 5º, II da LGPD
(Lei 13.709/2018). Este documento descreve como o software os trata.

## 1. Processamento 100% local

- O vídeo da webcam **nunca é enviado para a internet**. Toda a extração de
  biomarcadores (OpenCV + MediaPipe) e a inferência do LLM (BitNet b1.58,
  local via `bitnet.cpp` ou `transformers`) rodam no dispositivo do usuário.
- Não há telemetria, analytics ou chamadas de rede em tempo de uso, exceto o
  download único e opcional do modelo GGUF na primeira execução (ver
  `app/ai/bootstrap.py`), feito diretamente do Hugging Face Hub.
- Não existe backend remoto, API própria ou conta de usuário.

## 2. O que é armazenado e onde

| Dado | Local | Formato |
|---|---|---|
| Sessões e métricas extraídas | `data/*.db` (SQLite) | binário local |
| Relatórios gerados | `data/*.pdf`, `data/*.csv` | arquivo local |
| Modelo de IA (pesos) | `models/*.gguf` | binário local, sem dados do usuário |

Nenhum desses caminhos é sincronizado, enviado ou replicado automaticamente.
Todos estão listados em `.gitignore` para nunca serem versionados/publicados
acidentalmente.

## 3. Consentimento

- O uso ocupacional (módulo NR-01) exige consentimento explícito por sessão,
  apresentado como diálogo antes da captura (ver `app/ui/main_window.py`).
- Os demais módulos clínicos exibem o aviso de não-diagnóstico e a natureza
  sensível da captura antes de habilitar a webcam (ver item de disclaimer no
  primeiro uso).
- O usuário pode encerrar a captura a qualquer momento; nenhum frame de vídeo
  bruto é persistido — apenas features numéricas agregadas.

## 4. Retenção e exclusão

- Os dados ficam no disco do próprio usuário, sob seu controle total.
- Para apagar todo o histórico: remova o arquivo `data/*.db` e os relatórios
  em `data/`. Não há cópia em nenhum outro lugar.

## 5. Base legal (para uso institucional/ocupacional)

Ao usar o módulo NR-01 em contexto corporativo, o **controlador dos dados é
a organização que opera o software**, não os autores do projeto. Cabe à
organização:

- obter consentimento informado dos colaboradores avaliados;
- definir finalidade, retenção e acesso aos relatórios agregados por setor;
- garantir base legal adequada (LGPD art. 7º/11) para tratamento de dado
  sensível de saúde.

## 6. Contato

Dúvidas sobre este documento: abra uma issue no repositório ou veja
`SECURITY.md` para reportes sensíveis.
