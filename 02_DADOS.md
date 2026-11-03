# 02 — Dados

Tudo sobre os dados: fonte oficial (Base dos Dados), aquisição por SQL,
repositório, base longitudinal, qualidade, limites e enriquecimento
planejado.

---

# Parte A — Fontes

## 1. Fonte oficial: Base dos Dados

- **Plataforma:** https://basedosdados.org/
- **Código e ferramentas:** https://github.com/basedosdados
- **Armazenamento:** tabelas no BigQuery (Google Cloud), acessadas por
  SQL.
- **Acesso no projeto:** biblioteca Python `basedosdados`
  (`bd.read_sql` para consultas, `bd.read_table` para leitura direta
  de uma tabela).
- **Origem dos dados:** INEP. A Base dos Dados padroniza e publica as
  tabelas. Citar as duas fontes (§5).

## 2. Foco inicial: Indicadores Educacionais

| Indicador | Sigla | Uso no projeto | Status na BD |
|---|---|---|---|
| Taxa de rendimento (aprovação, reprovação, abandono) | `tx_rend` | Features `t` e alvo `t+1` | **A verificar** (§3) |
| Distorção idade-série | TDI | Feature (variável mais importante nos experimentos legados) | A verificar |
| Média de alunos por turma | ATU | Feature | A verificar |
| Esforço docente | IED | Feature; disponível a partir de 2021 na fonte legada | A verificar |
| Horas-aula diárias | HAD | Feature futura (§29) | A verificar |

Escopo: nível **escola**. Municípios e UF/Brasil não entram na base
longitudinal, mas podem ser usados como contexto em consultas futuras.

## 3. Premissa sobre a taxa de rendimento

- A versão anterior descartava a Base dos Dados por não conter
  `tx_rend`.
- **A restrição está revogada.** O projeto segue com a Base dos Dados.
  Assume-se que a tabela atualizada contém a taxa de rendimento, ou
  que ela pode ser calculada por SQL a partir das colunas disponíveis.
- **Gate de verificação:** a primeira consulta do pipeline
  (`sql/verificacao/01_presenca_tx_rend.sql`) confirma, para Roraima
  em 2019–2025:
  - colunas de aprovação, reprovação e abandono (ou os insumos para
    calculá-las);
  - granularidade escola-ano;
  - chave de escola e de ano únicas por linha;
  - contagem de escolas por ano.
- **Se o gate falhar**, nenhuma modelagem começa. A alternativa é
  escolhida e registrada em `06_DECISOES_PROBLEMAS_PERGUNTAS.md`, na
  ordem:
  1. Outra tabela da BD que contenha o rendimento por escola (buscar
     no catálogo).
  2. Cálculo de rendimento a partir de matrículas e situação de
     matrícula, se a BD tiver esses dados por escola-ano.
  3. Proxy declarado (por exemplo, queda de matrículas entre `t` e
     `t+1`). Proxy **não é** taxa de abandono e precisa de nome e
     texto próprios no artigo.
- **Não trocar o alvo em silêncio.** Toda mudança de definição do
  alvo é uma decisão registrada.

## 4. Escalabilidade: data lake da Base dos Dados

A BD tem muitas tabelas. O projeto é construído para receber novas
fontes sem reescrever o pipeline.

### Regras de integração

Toda tabela nova entra com:

1. **Grão declarado** (ex.: escola-ano, município-ano).
2. **Chave de junção** explícita (ex.: identificador da escola e
   ano).
3. **Checagem de unicidade** da chave na própria consulta.
4. **Contagem antes e depois do join**, registrada no log da
   extração. Aumento de linhas indica fan-out.
5. **Entrada no catálogo** `docs/fontes/<dataset>__<tabela>.md`, com
   URL, colunas usadas, cobertura temporal, licença e data da consulta.

### Candidatas futuras (a verificar na BD)

- Censo Escolar: infraestrutura, dependências, escola indígena, terra
  indígena, assentamento, localização diferenciada.
- INSE (via Saeb), com as mesmas ressalvas de §24.
- Dados do Pé-de-Meia por escola, se a BD publicar.
- Indicadores municipais, como contexto socioeconômico.

## 5. Citação

> BASE DOS DADOS. **Base dos Dados.** Disponível em:
> https://basedosdados.org/. Acesso em: <data>.

> BRASIL. Instituto Nacional de Estudos e Pesquisas Educacionais
> Anísio Teixeira (Inep). **Indicadores Educacionais: Taxas de
> Rendimento, Distorção Idade-série, Alunos por Turma, Esforço Docente
> e Horas-aula diária, 2019–2025.** Brasília: Inep. Dados tratados
> pela Base dos Dados. Acesso em: <data>.

> BRASIL. Instituto Nacional de Estudos e Pesquisas Educacionais
> Anísio Teixeira (Inep). **Microdados do Censo Escolar da Educação
> Básica.** Brasília: Inep. Dados tratados pela Base dos Dados. Acesso
> em: <data>. *(Quando o Censo entrar na base.)*

## 6. Fontes descartadas

- **Arquivos `.zip` do INEP** (110 arquivos, ~2,9 GB, extração local,
  validação sha256, certificado TLS do servidor): **substituídos** pela
  Base dos Dados em novembro/2026. O histórico continua no git, mas o
  fluxo não é mais executado.

---

# Parte B — Repositório e aquisição

## 7. Estrutura do repositório

O projeto não descompacta arquivos. O centro dele são as consultas
SQL.

```text
abandono-escolar/
├── sql/
│   ├── verificacao/
│   │   ├── 00_colunas_indicadores_escola.sql   descobre colunas
│   │   └── 01_presenca_tx_rend.sql   gate de disponibilidade (§3)
│   ├── indicadores/
│   │   └── 01_escola_ano.sql         consolidação de indicadores RR
│   └── futuro/                       consultas de novas tabelas da BD
├── src/
│   ├── config.py                     lê variáveis de ambiente
│   ├── consultas.py                  renderiza templates SQL com parâmetros validados
│   ├── extracao_bd.py                Etapa zero: executa consultas e grava snapshots
│   ├── base_longitudinal.py          gera ANO_ALVO, _LAG1, _DELTA1 e _T1
│   └── catalogo.py                   gera docs/catalogo_variaveis.html
├── dados/
│   ├── cache/                        snapshots Parquet (descartável, fora do git)
│   ├── processado/                   base longitudinal final (fora do git)
│   ├── externo/                      arquivos do orientador (ausente)
│   └── metadados/
│       └── snapshots.csv             registro de cada extração (versionado)
├── docs/
│   ├── fontes/                       uma nota por tabela da BD usada
│   ├── metodologia_variaveis.md
│   ├── DECISOES.md
│   ├── problemas.csv
│   ├── inventarios/
│   └── catalogo_variaveis.html
├── tests/
│   ├── test_consultas.py             validação de parâmetros e templates
│   └── test_base_longitudinal.py     regras de leakage (ver 03_METODOLOGIA.md, §3.3)
├── notebooks/
├── .env.example                      modelo das variáveis de ambiente (versionado)
├── .gitignore                        exclui .env, dados/cache e dados/processado
├── requirements.txt
└── CLAUDE.md
```

## 8. Pré-requisitos

- Python 3.12+ (numpy fixado exige 3.12).
- Git.
- Conta Google com acesso ao BigQuery e um **projeto de faturamento**
  no Google Cloud. A cota gratuita de consultas do BigQuery deve ser
  confirmada antes da primeira execução.
- Espaço: poucos centenas de MB para snapshots e base final.
- Tempo: minutos por extração completa (a medir na primeira execução).

## 9. Configuração e credenciais

- Variável de ambiente `BD_BILLING_PROJECT_ID` com o ID do projeto de
  faturamento. Não entra no código.
- Arquivo `.env` local, listado no `.gitignore`. O repositório traz
  apenas `.env.example`, com os nomes das variáveis e sem valores.
- A primeira execução pede login Google pelo pacote `basedosdados`.
  As credenciais ficam na máquina do usuário, fora do repositório.
- **Nunca** versionar credenciais, tokens ou o ID do projeto em
  arquivos do repositório, notebooks ou snapshots.

## 10. Comandos

```bash
git clone <url> abandono-escolar
cd abandono-escolar
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

# Verificação da fonte (gate da §3)
python -m src.extracao_bd

# Extração de Roraima, 2019–2025
python -m src.extracao_bd --uf RR --ano-inicio 2019 --ano-fim 2025

# Base longitudinal a partir do último snapshot
python -m src.base_longitudinal
```

Uso em código:

```python
import os
import basedosdados as bd

from src.consultas import renderizar

sql = renderizar("indicadores/01_escola_ano.sql", uf="RR", anos=(2019, 2025))
df = bd.read_sql(sql, billing_project_id=os.environ["BD_BILLING_PROJECT_ID"])
```

## 11. Regras para consultas parametrizadas

- Parâmetros (UF, anos, nomes de tabela) são **validados** em
  `src/consultas.py` contra listas permitidas antes de entrar no SQL.
  Ex.: UF só aceita siglas de 2 letras da lista; anos só aceitam
  inteiros entre 2019 e o último ano disponível.
- Nomes de tabela e coluna vêm de um dicionário fixo, nunca de texto
  livre.
- Nada de `f-string` com entrada do usuário dentro de SQL.
- Cada consulta é um arquivo `.sql` versionado. Mudança no arquivo
  muda o hash e gera nova linha em `snapshots.csv`.

## 12. O que o pipeline de aquisição faz

1. Verifica variáveis de ambiente e acesso ao projeto de faturamento.
2. Executa `sql/verificacao/` (presença de tabelas, colunas, cobertura
   de RR por ano). Interrompe se o gate da §3 falhar.
3. Executa a consolidação em `sql/indicadores/`: junção dos indicadores
   por escola-ano, filtro de RR, agregação feita na nuvem.
4. Checagens no DataFrame: grão, unicidade da chave, contagens por ano,
   tipos.
5. Grava snapshot em `dados/cache/` (Parquet) e uma linha em
   `dados/metadados/snapshots.csv`, com: nome da consulta, hash da
   consulta, data da extração, nº de linhas e colunas, e versão da
   biblioteca. **Nunca** grava credencial nem o ID do projeto.
6. Gera a base longitudinal em `dados/processado/`.
7. Atualiza o catálogo de variáveis.

## 13. Reprodutibilidade

- A consulta SQL é a especificação. Vive no git, com hash.
- A nuvem pode mudar (revisões da BD, novos anos, correções). Por isso
  o **snapshot é a referência dos experimentos**, não a consulta
  viva.
- Cada experimento registra o `snapshot_id` usado.
- Ao reexecutar a consulta, o pipeline compara hash, nº de linhas e
  contagens por ano com o último snapshot. Divergência **não
  sobrescreve** o snapshot: o resultado novo vai para
  `dados/cache/divergente/` e o pipeline para, até decisão.
- Rodar de novo é seguro: snapshot que confere não é refeito.

## 14. Limitações de acesso

- Cota de consulta do BigQuery. Consultas amplas (todas as UFs) podem
  consumir muito da cota. Por isso o recorte de RR é feito na consulta,
  não depois.
- Dependência de rede e de serviço externo.
- Mudança de schema na BD (renomeação de coluna, nova versão de
  tabela). Detectada pelo teste de schema em `tests/`.
- Publicação com atraso em relação ao INEP. A data de consulta sempre
  fica registrada.

---

# Parte C — Base longitudinal

## 15. Visão geral

- **Arquivo:** `dados/processado/base_longitudinal_rr_2019_2025.parquet`.
- **Status:** **a regenerar** a partir da Base dos Dados. A versão
  legada, de origem INEP, tem 6.054 linhas × 59 colunas e 934 escolas
  (referência de comparação).
- **Cobertura alvo:** 2019 a 2025, Roraima, escola-ano.
- **Unidade:** uma escola em um ano (`ANO`), com alvo em t+1
  (`ANO_ALVO`).
- **Contrato:** os nomes de coluna abaixo são lógicos e mantidos para
  não quebrar o código de modelagem. O mapeamento para os campos da
  BD está na §16.

## 16. Contrato de colunas

### 16.1 Identificação e metadados

| Coluna | Tipo | Descrição |
|---|---|---|
| `ANO` | Int16 | Ano de referência. |
| `ANO_ALVO` | Int16 | Sempre `ANO + 1`. Nulo no último ano. |
| `CO_ENTIDADE` | string | Identificador da escola. Chave para junção. |
| `NO_ENTIDADE` | string | Nome da escola. Muda ao longo da série em 105 casos (legado). |
| `CO_MUNICIPIO` | string | Identificador do município. |
| `NO_MUNICIPIO` | string | Nome do município. |
| `LOCALIZACAO` | string | Urbana ou Rural. |
| `DEPENDENCIA` | string | Municipal, Estadual, Privada, Federal. |

### 16.2 Flags

| Coluna | Descrição |
|---|---|
| `REDE_PUBLICA` | 1 = pública, 0 = privada. |
| `DISP_ATU`, `DISP_TDI`, `DISP_IED`, `DISP_REND` | 1 = tem dado do indicador. |

Permitem distinguir "escola sem indicador" de "indicador = zero".

### 16.3 Indicadores por etapa

| Grupo | Colunas | Observação |
|---|---|---|
| ATU | `ATU_FUN_TOTAL`, `ATU_FUN_AI`, `ATU_FUN_AF`, `ATU_MED_TOTAL` | Média de alunos por turma. |
| TDI | `TDI_FUN_TOTAL`, `TDI_FUN_AI`, `TDI_FUN_AF`, `TDI_MED_TOTAL` | Distorção idade-série. |
| IED | `IED_FUN_N1`–`IED_FUN_N6`, `IED_FUN_ALTO`, `IED_MED_N1`–`IED_MED_N6`, `IED_MED_ALTO` | Só a partir de 2021 na fonte legada. |
| Aprovação | `APROVACAO_FUN`, `APROVACAO_FUN_AI`, `APROVACAO_FUN_AF`, `APROVACAO_MED` | Depende de `tx_rend` (§3). |
| Reprovação | `REPROVACAO_FUN`, `REPROVACAO_FUN_AI`, `REPROVACAO_FUN_AF`, `REPROVACAO_MED` | Depende de `tx_rend` (§3). |
| Abandono em t | `ABANDONO_FUN`, `ABANDONO_FUN_AI`, `ABANDONO_FUN_AF`, `ABANDONO_MED` | Features legítimas: abandono em `t`, alvo em `t+1`. |

### 16.4 Derivadas (construídas no pipeline, não na consulta)

| Grupo | Colunas | Regra |
|---|---|---|
| `_LAG1` | `ABANDONO_FUN_LAG1`, `ABANDONO_FUN_AF_LAG1`, `ABANDONO_MED_LAG1` | Valor de `t−1` da mesma escola. Nulo quando não há `t−1`. |
| `_DELTA1` | `TDI_FUN_AF_DELTA1`, `TDI_MED_TOTAL_DELTA1`, `ATU_FUN_AF_DELTA1`, `ATU_MED_TOTAL_DELTA1`, `ABANDONO_FUN_AF_DELTA1`, `ABANDONO_MED_DELTA1` | `t − (t−1)`. Nulo quando não há `t−1`. |
| `_T1` (alvos) | `ABANDONO_FUN_T1`, `ABANDONO_FUN_AF_T1`, `ABANDONO_MED_T1` | Valor de `t+1` da mesma escola. Nulo no último ano. **Único lugar onde `t+1` aparece.** |

### 16.5 Contagem-alvo

| Grupo | Nº |
|---|---|
| Identificação | 8 |
| Flags | 5 |
| ATU | 4 |
| TDI | 4 |
| IED | 14 |
| Aprovação | 4 |
| Reprovação | 4 |
| Abandono em t | 4 |
| `_LAG1` | 3 |
| `_DELTA1` | 6 |
| `_T1` | 3 |
| **Total** | **59** |

A contagem pode mudar após o mapeamento real (§17). Mudança é
registrada em `docs/DECISOES.md`.

## 17. Mapeamento BD → contrato

Preenchido após a verificação da §3. Colunas com status "a verificar"
não entram em experimento.

| Coluna lógica | Tabela BD | Campo BD | Status |
|---|---|---|---|
| `CO_ENTIDADE` | a definir | a definir | A verificar |
| `ANO` | a definir | a definir | A verificar |
| `REDE_PUBLICA` | a definir | a definir | A verificar |
| `LOCALIZACAO` | a definir | a definir | A verificar |
| `DEPENDENCIA` | a definir | a definir | A verificar |
| `TDI_*` | a definir | a definir | A verificar |
| `ATU_*` | a definir | a definir | A verificar |
| `IED_*` | a definir | a definir | A verificar |
| `APROVACAO_*`, `REPROVACAO_*`, `ABANDONO_*` | a definir | a definir | **Gate (§3)** |

## 18. Convenções de nomenclatura

- `_AI` — anos iniciais.
- `_AF` — anos finais.
- `_MED` — ensino médio.
- `_FUN` — fundamental inteiro.
- `_LAG1` — ano anterior.
- `_DELTA1` — diferença anual.
- `_T1` — target do ano seguinte.

---

# Parte D — Qualidade e limites

## 19. Missing estrutural

Os nulos não são aleatórios. Refletem o que a escola oferece.

| Grupo | % nulos (legado) | Por quê |
|---|---|---|
| `*_MED*` | ~80–85% | Só escolas com EM. |
| `*_FUN_AF*` | ~71–76% | Só escolas com anos finais. |
| `*_FUN_AI*` | ~38–69% | Só escolas com anos iniciais. |
| `*_FUN` | ~24% | Só escolas com fundamental. |
| IDs, localização, `DISP_*` | 0% | Sempre presentes. |

**Consequência:** não dá para rodar um modelo único misturando tudo.
Confirma a decisão de separar em dois conjuntos. Percentuais a
recalcular com a base da BD.

## 20. Zeros no alvo

| Alvo | % zeros (legado) |
|---|---|
| `ABANDONO_FUN_T1` | 66,1% |
| `ABANDONO_FUN_AF_T1` | 44,1% |
| `ABANDONO_MED_T1` | 32,3% |

**Implicações:**

- Métricas lineares dominadas por "acertar o zero".
- R² pode ser enganoso.
- Talvez valha uma abordagem em duas etapas: (a) classificar se há
  abandono, (b) se sim, estimar quanto.

## 21. Distribuição temporal do alvo

Valores legados (INEP). Revalidar com a base da BD: se `tx_rend` da BD
tiver origem e metodologia diferentes, a distribuição pode mudar.

| ANO_ALVO | AF | EM |
|---|---|---|
| 2020 | 0,99 | 1,60 |
| 2021 | 2,96 | 5,54 |
| 2022 | 4,94 | 11,41 |
| 2023 | 3,00 | 7,18 |
| 2024 | 2,63 | 5,42 |
| 2025 | 2,42 | 5,91 |

**Pico em 2022**

- Corresponde ao retorno pós-pandemia.
- Abandono do EM triplicou entre 2020 e 2022.
- Contamina qualquer split temporal. Treinar em 2020–2022 e testar
  em 2023–2025 vê distribuições muito diferentes.

## 22. Painel não balanceado

- Legado: 934 escolas em 7 anos, nem toda escola aparece em todos os
  anos, 6 escolas mudam de localização, 105 mudam de nome.
- Mesma verificação na base da BD.

## 23. Cobertura do IED

Só existe a partir de 2021 na fonte legada. Em 2019 e 2020, `IED_FUN_*`
e `IED_MED_*` são nulos. Ver problema P019. Verificar se a BD cobre
2019–2020.

## 24. INSE

- Existe apenas em 2019, 2021 e 2023 (fonte legada).
- Depende da participação no Saeb.
- ~Metade das escolas públicas (a confirmar para Roraima).
- Ausência concentra-se em escolas pequenas e rurais.
- **Decisão:** usar só para comparar grupos, não como feature.

## 25. Duplicatas e outliers

- Legado: nenhuma duplicata completa, nenhuma duplicata por
  (`CO_ENTIDADE`, `ANO`).
- Outliers presentes em `TDI_*`, `IED_FUN_N1`, `ABANDONO_*`.
- RMSE > MAE indica erros muito grandes em algumas escolas.
- **Na BD:** a checagem de unicidade da chave roda na consulta e no
  DataFrame. Falha interrompe a extração.

## 26. Qualidade específica da Base dos Dados

- **Atualização e revisão:** a BD pode publicar com atraso ou corrigir
  tabelas. Cada snapshot grava a data da consulta.
- **Schema:** nomes de coluna e tipos podem mudar entre versões.
  Teste de schema em `tests/` quebra cedo, não no meio da modelagem.
- **Tipos:** a BD pode trazer tipos nulos do pandas (`Int64`,
  `Float64`). Ver problema 10.1.2 em `03_METODOLOGIA.md`.
- **Chaves:** o identificador da escola precisa ser confirmado como
  único por ano antes de qualquer junção.

## 27. Defasagem do desfecho

- Abandono de t+1 só é conhecido bem depois do fim de t+1.
- Segunda etapa do Censo é coletada no ano seguinte.
- Em novembro/2026, último ano com alvo é 2025, se a BD já publicar.

## 28. Resumo de limitações

| # | Limitação | Consequência |
|---|---|---|
| 1 | Missing estrutural | Separar por etapa. |
| 2 | Muitos zeros no alvo | Métricas dominadas por acertos triviais. |
| 3 | Pico de 2022 | Split temporal precisa tratar. |
| 4 | IED só a partir de 2021 (legado) | Perde 2019–2020 se a BD não cobrir. |
| 5 | INSE esparso e enviesado | Só para análise de grupos. |
| 6 | Outliers no alvo | RMSE > MAE. |
| 7 | Defasagem do desfecho | Um ano atrás do presente. |
| 8 | Disponibilidade de `tx_rend` na BD | Gate da §3. Bloqueia modelagem. |
| 9 | Cota e rede do BigQuery | Recorte na consulta; snapshot como referência. |

---

# Parte E — Enriquecimento futuro

Variáveis discutidas e priorizadas para inclusão. Cada uma entra como
nova tabela da BD, seguindo as regras da §4.

## 29. Escola indígena e localização diferenciada

- Do Censo Escolar: `IN_ESCOLA_INDIGENA`, terra indígena,
  assentamento.
- Hoje a base só distingue Urbana / Rural.
- **Por que incluir:** Roraima tem muitas escolas indígenas; sem isso
  não se avalia desempenho por grupo.
- **Como:** consultar a tabela do Censo na BD, juntar por escola-ano,
  adicionar como colunas. Não necessariamente como features — usar
  para avaliar por grupo.

## 30. Flag de elegibilidade

- `elegivel_analise` (0/1): 1 se oferece AF ou EM; 0 se só educação
  infantil.
- Não excluir fisicamente da base — manter e filtrar só na hora de
  treinar.

## 31. Multisseriadas

- Flag `multisseriada`.
- Onde não houver média dos anos finais, usar a do fundamental como
  aproximação.
- Criar coluna indicadora de substituição.

## 32. Esforço docente 2019–2020 (IED)

- Só existe a partir de 2021 na base legada.
- Verificar se a BD cobre 2019 e 2020.
- Pendente de confirmação da consistência metodológica.

## 33. Horas-aula diárias (HAD)

- Disponível em todos os anos na fonte INEP.
- Pode representar diferenças de organização e jornada.
- Pendente de decisão com o orientador. Ver P019.

## 34. Pé-de-Meia

- Vigente desde 2024. Foca permanência no EM público.
- Afeta validação (2023→2024) e teste (2024→2025) do desenho.
- Se a BD tiver dados por escola: nº de beneficiários, % de alunos
  atendidos.
- Se não: variável indicando pré/pós-2024, análises separadas.
- **Cuidado com leakage:** não usar informação que dependa da
  frequência do aluno para prever abandono no mesmo período.

## 35. Censo — infraestrutura e dependências

- Água, energia, esgoto, internet, acessibilidade.
- Biblioteca, quadra, laboratório.
- Computador, impressora, projetor.
- Disponível nos microdados do Censo; verificar se a BD publica em
  tabela consultável.
- **Cuidado:** muitas variáveis, risco de inflar o modelo.

## 36. Priorização

1. Escola indígena e localização diferenciada.
2. Flag de elegibilidade.
3. Flag de multisseriada.
4. Pé-de-Meia.
5. IED 2019–2020 e HAD.
6. INSE (só avaliação).
7. Infraestrutura do Censo (se houver tempo).

## 37. Princípio geral

Colocar as informações na base agora, documentar bem de onde cada
uma veio (tabela, data da consulta, grão e chave), e decidir depois,
por meio dos experimentos, quais entram no modelo final.
