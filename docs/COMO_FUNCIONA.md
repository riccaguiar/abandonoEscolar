# Como o programa funciona

Este documento explica a arquitetura do pipeline de extração. Para
rodar, veja `COMO_USAR.md`. Contexto científico e regras de dados estão
em `docs/CONTEXTO.md`, que aponta para os documentos do grupo.

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
   Conta também, **linha a linha**, nos anos finais e no médio: escolas em que
   `|aprovação + reprovação + abandono − 100|` passa de 1e-6, e escolas com só
   uma ou duas das três taxas. (Na BD de 2007–2022 o maior desvio é 1,4e-14;
   no INEP, 3e-14.)
4. **Salva o snapshot** (ver "Snapshots", abaixo).
5. **Avalia o gate.** Reprova se faltar algum ano, houver chave
   `(id_escola, ano)` duplicada, `taxa_abandono_ef_anos_finais` ou
   `taxa_abandono_em` forem nulas em todas as escolas de algum ano, ou se
   **qualquer** escola tiver a soma fora de 100 ou o trio incompleto.

## Códigos de saída

| Código | Significado |
|---|---|
| 0 | Gate aprovado. Pode seguir para a consolidação. |
| 1 | Erro técnico (login, faturamento, tabela inexistente, SQL inválido). |
| 2 | Gate reprovado: a Base dos Dados não tem o que o projeto precisa. |
| 3 | A mesma consulta devolveu resultado diferente do snapshot anterior (ver abaixo). |

## Tratamento de erros

`classificar_erro` percorre a cadeia de exceções (a `basedosdados`
embrulha erros do Google) e decide:

- **Repete (até 4 tentativas, espera 2s, 4s, 8s + variação):** serviço
  indisponível, timeout, limite de taxa, falha de conexão.
- **Não repete, explica:** credencial ausente/expirada, acesso negado
  (403, faturamento), tabela inexistente (404), SQL rejeitado (400).

## Snapshots (`src/snapshots.py`)

O hash da consulta prova o que foi pedido; o hash do resultado prova o que
voltou. Cada snapshot é registrado em `dados/metadados/snapshots.csv` com os dois.

| Situação | O que acontece |
|---|---|
| Consulta nova | Grava `dados/cache/<consulta>_<data UTC>.parquet` e registra (`status = ok`). |
| Mesma consulta, mesmo resultado | Não grava nada; reaproveita o snapshot existente. |
| Mesma consulta, resultado diferente | Grava em `dados/cache/divergente/`, registra com `status = divergente`, **não substitui** o anterior e sai com código 3. Para adotar o novo: rodar de novo com `--aceitar-divergencia`. |

- `sha256_resultado`: hash do conteúdo lido de volta do disco (não depende de
  metadados do Parquet). `sha256_arquivo`: hash dos bytes do arquivo.
- `python -m src.snapshots --deduplicar` remove snapshots repetidos (mesma
  consulta e mesmo resultado), mantendo o mais antigo.
- Nunca grava credencial nem o ID do projeto de faturamento.

## Reprodutibilidade

- A consulta é a especificação; vive no git.
- O **snapshot** é a referência dos experimentos, porque a nuvem pode
  mudar. Cada resultado deve citar o `snapshot_id`.
- `dados/cache/` não vai para o git. `dados/metadados/snapshots.csv`
  vai.
- Versões: `requirements.txt` fixa as dependências diretas com `==`;
  `requirements-lock.txt` fixa o ambiente inteiro.

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
  `ALTO` da base oficial do grupo (lá, `ALTO` = N4 + N5 + N6).

Resultado do gate em 03/11/2026: **reprovado** (2023–2024 inconsistentes, 2025 ausente).

## Como estender

Nova tabela da BD = novo `.sql` em `sql/` + checagem de unicidade da chave
(escola, ano) + contagem antes e depois de cada `merge` (`validate="1:1"`) +
conferência contra o INEP nos anos em que o grupo tem o dado + entrada em
`docs/DECISOES.md`.
