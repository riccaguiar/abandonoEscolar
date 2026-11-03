# Como usar

Guia prático para rodar a Etapa zero. Para entender o que acontece por
dentro, veja `COMO_FUNCIONA.md`.

## 1. Pré-requisitos

- Python 3.12 ou mais novo (testado com 3.14).
- Conta Google com acesso ao projeto `abandonoescolar1` (faturamento do
  BigQuery ativo e API do BigQuery habilitada).
- Acesso à internet.

## 2. Instalação (uma vez)

PowerShell, na pasta do projeto:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

O `.env` já aponta para `abandonoescolar1`. Ele não vai para o git.

## 3. Estrutura de pastas

As pastas já existem. Para recriar em outra máquina:

```powershell
New-Item -ItemType Directory -Force sql\verificacao, sql\indicadores, sql\futuro, src, tests, notebooks, dados\cache, dados\processado, dados\externo, dados\metadados, docs\fontes
```

Ou, em Bash:

```bash
mkdir -p sql/{verificacao,indicadores,futuro} src tests notebooks dados/{cache,processado,externo,metadados} docs/fontes
```

## 4. Rodar a Etapa zero

```powershell
python -m src.extracao_bd
```

Na primeira vez o navegador abre pedindo login no Google. Autorize com
a conta que tem acesso ao projeto.

Opções:

| Opção | Padrão | Para quê |
|---|---|---|
| `--uf` | `RR` | Estado. |
| `--ano-inicio` / `--ano-fim` | `2019` / `2025` | Período. |
| `--formato` | `parquet` | `parquet` ou `csv`. |
| `--billing-project` | `abandonoescolar1` | Outro projeto de faturamento. |

Exemplo: `python -m src.extracao_bd --uf RR --ano-inicio 2021 --formato csv`

## 5. Ler o resultado

- Na tela: uma linha por ano, com `n_linhas`, `n_escolas`,
  `n_duplicadas` e `nn_<coluna>` (valores não nulos de cada coluna de
  rendimento), seguida de **GATE APROVADO** ou **GATE REPROVADO** com os
  motivos.
- Arquivo: `dados/cache/check_tx_rend_<data>.parquet`.
- Registro: `dados/metadados/snapshots.csv`.

Para abrir o snapshot:

```python
import pandas as pd
pd.read_parquet("dados/cache/check_tx_rend_20261103T180000Z.parquet")
```

## 6. Gráfico da série de abandono

```powershell
python -m src.grafico_abandono --uf RR
```

Gera `docs/figuras/abandono_rr.html` (abre em qualquer navegador, sem
internet) e salva o snapshot da consulta. Anos com dado inconsistente
aparecem hachurados, sem linha.

## 7. Se algo falhar

| Mensagem | O que fazer |
|---|---|
| "Credenciais do Google ausentes ou expiradas" | Rode de novo e refaça o login no navegador. |
| "Acesso negado (403)" | Confirme faturamento ativo e API do BigQuery habilitada no projeto `abandonoescolar1`; confirme que sua conta tem permissão. |
| "Tabela ou dataset não encontrado" / "não existe ou não tem colunas" | O nome da tabela em `src/config.py` está errado (a atual, `escola`, já foi confirmada). Procure o correto em https://basedosdados.org/. |
| "Colunas obrigatórias ausentes" | A tabela mudou de schema. Compare com `COLUNAS_OBRIGATORIAS` em `src/extracao_bd.py` e ajuste os SQL. |
| "Falha temporária ... Nova tentativa" | Normal. O programa repete sozinho (até 4 vezes). |
| Saída com código 2 | Não é bug: a Base dos Dados não passou no gate. Registre em `06_DECISOES_PROBLEMAS_PERGUNTAS.md`. |

## 8. Testes

Não usam rede nem credenciais:

```powershell
python -m pytest -q
```

## 9. Cuidados

- Não coloque senhas, tokens ou arquivos de credencial no repositório.
- Consultas gastam cota do BigQuery. A Etapa zero é leve (filtra UF e
  anos), mas não remova o filtro de UF em consultas futuras.
- Use sempre o snapshot, não a consulta viva, como entrada dos
  experimentos, e registre o `snapshot_id` nos resultados.
