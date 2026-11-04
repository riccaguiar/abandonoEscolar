# Como o programa funciona

Este documento explica a arquitetura do pipeline de extração. Para
rodar, veja `COMO_USAR.md`. Contexto científico e regras de dados estão
em `01_PROJETO.md`, `02_DADOS.md` e `03_METODOLOGIA.md`.

## Ideia central

Os dados não são baixados. Eles ficam no BigQuery, dentro da Base dos
Dados, e o projeto os **consulta por SQL**. Só o resultado (pequeno) vem
para o computador, e é guardado como **snapshot** datado.

```text
sql/*.sql  ──► src/consultas.py ──► src/extracao_bd.py ──► BigQuery (Base dos Dados)
 (template)    (valida e preenche)    (executa, repete        │
                                       em falha, salva)       ▼
                                                     dados/cache/*.parquet
                                                     dados/metadados/snapshots.csv
```

## Os arquivos

| Arquivo | Função |
|---|---|
| `src/config.py` | Caminhos, projeto de faturamento (`abandonoescolar1`), tabela e período padrão. |
| `src/consultas.py` | Valida UF, anos e nomes de colunas e preenche os placeholders `{{...}}` dos `.sql`. Impede SQL montado com texto livre. |
| `src/extracao_bd.py` | Programa principal da "Etapa zero". Executa, trata erros, salva snapshot, avalia o gate. |
| `sql/verificacao/00_colunas_indicadores_escola.sql` | Lista as colunas da tabela (só metadados, custo ~zero). |
| `sql/verificacao/01_presenca_tx_rend.sql` | Conta escolas e valores não nulos de rendimento por ano. |
| `src/grafico_abandono.py` + `sql/exploracao/01_abandono_por_ano.sql` | Gera `docs/figuras/abandono_<uf>.html`: série de abandono UF x Brasil, escolas públicas. |
| `src/conferencia_rendimento.py` + `sql/verificacao/02_escolas_uf_todas_colunas.sql` | Fase 3.1: confere o rendimento da BD com o INEP do grupo escola a escola e localiza colunas deslocadas. Saídas em `docs/conferencia/`. |
| `tests/` | Testes sem rede: usam uma `basedosdados` falsa. |

## Etapa zero, passo a passo

1. **Descobre as colunas.** Roda o SQL 00 e obtém os nomes reais da
   tabela. O projeto não assume nomes de coluna que ainda não foram
   confirmados no catálogo.
2. **Escolhe as colunas de rendimento.** Qualquer coluna com `aprov`,
   `reprov` ou `abandon` no nome. Se não houver nenhuma, o gate
   reprova na hora.
3. **Conta por ano.** Gera o SQL 01 com um `COUNTIF(coluna IS NOT NULL)`
   por coluna e roda para a UF e o intervalo de anos pedidos.
4. **Salva o snapshot.** Arquivo `check_tx_rend_AAAAMMDDTHHMMSSZ.parquet`
   em `dados/cache/` e uma linha em `dados/metadados/snapshots.csv`
   (hash da consulta, data UTC, linhas, colunas, versão da biblioteca).
   Nunca grava credencial.
5. **Avalia o gate** (`02_DADOS.md`, §3). Reprova se faltar algum ano,
   houver chave `(id_escola, ano)` duplicada ou se `taxa_abandono_ef_anos_finais`
   ou `taxa_abandono_em` forem nulas em todas as escolas de algum ano.

## Códigos de saída

| Código | Significado |
|---|---|
| 0 | Gate aprovado. Pode seguir para a consolidação. |
| 1 | Erro técnico (login, faturamento, tabela inexistente, SQL inválido). |
| 2 | Gate reprovado: a Base dos Dados não tem o que o projeto precisa. |

## Tratamento de erros

`classificar_erro` percorre a cadeia de exceções (a `basedosdados`
embrulha erros do Google) e decide:

- **Repete (até 4 tentativas, espera 2s, 4s, 8s + variação):** serviço
  indisponível, timeout, limite de taxa, falha de conexão.
- **Não repete, explica:** credencial ausente/expirada, acesso negado
  (403, faturamento), tabela inexistente (404), SQL rejeitado (400).

## Reprodutibilidade

- A consulta é a especificação; vive no git.
- O **snapshot** é a referência dos experimentos, porque a nuvem pode
  mudar. Cada resultado deve citar o `snapshot_id`.
- `dados/cache/` não vai para o git. `dados/metadados/snapshots.csv`
  vai.

## O que já foi confirmado na Base dos Dados

- A tabela `basedosdados.br_inep_indicadores_educacionais.escola` existe
  (confirmado em 03/11/2026 pela execução real).
- Ela **não tem `sigla_uf`**. A UF é filtrada pelos 2 primeiros dígitos do
  código INEP da escola, `id_escola` (RR = `14`). `id_municipio` não serve:
  está nulo em todas as linhas de 2022.
- **2023 e 2024 têm as colunas deslocadas 71 posições** na tabela por escola
  (diagnóstico escola a escola em `docs/conferencia/RESULTADO_FASE_3_1.md`).
  Por isso aprovação + reprovação + abandono não fecha 100%. O gate reprova esses anos.
- **2025 ainda não está publicado** na tabela por escola (a `brasil` já tem).
- 2007–2022: as 12 taxas de rendimento conferem com o INEP **escola a escola**
  (uma escola divergente em 2007). Conferência: `src/conferencia_rendimento.py`.
- Tem colunas de rendimento por etapa e série (`taxa_aprovacao_*`,
  `taxa_reprovacao_*`, `taxa_abandono_*`). Os alvos do projeto são
  `taxa_abandono_ef_anos_finais` e `taxa_abandono_em`.
- Colunas de IED aparecem como `ied_*_nivel_1..6`, sem o agregado
  `ALTO` do contrato legado (ver `02_DADOS.md`, §17).

Resultado do gate em 03/11/2026: **reprovado** (2023–2024 inconsistentes, 2025 ausente).

## Como estender

Nova tabela da BD = novo `.sql` em `sql/` + nota em `docs/fontes/` +
teste de unicidade da chave (regras em `02_DADOS.md`, §4).
