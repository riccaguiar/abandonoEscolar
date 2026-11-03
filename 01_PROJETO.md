# 01 — Projeto

Contexto, pergunta, escopo, fonte de dados, pessoas, estado atual e
glossário. Tudo que uma IA precisa saber sobre o projeto *antes* de
olhar para os dados.

> **Revisão de novembro/2026:** a fonte de dados mudou. O projeto deixa
> de baixar arquivos brutos do INEP e passa a consultar a
> [Base dos Dados](https://basedosdados.org/) via SQL na nuvem. Ver
> Parte C, seção 9, e as decisões em `06_DECISOES_PROBLEMAS_PERGUNTAS.md`.

---

# Parte A — Identificação e pergunta

## 1. Identificação

- **Título:** Risco de abandono escolar em Roraima
- **Tipo:** Projeto de iniciação científica (PIBIC/UERR, Edital 35/2026)
  **e** artigo da disciplina de Mineração de Dados.
- **Orientador:** Prof. Bruno Cesar Barreto Figueiredo.
- **Instituição:** Universidade Estadual de Roraima (UERR).
- **Repositório do projeto:** https://github.com/gabsma25/abandonoescolar
- **Fonte de dados oficial:** Base dos Dados (https://basedosdados.org/),
  código e ferramentas em https://github.com/basedosdados.
- **Status em novembro/2026:** em andamento. Pipeline de dados legado
  (baseado em arquivos do INEP) concluído; reescrita para a Base dos
  Dados iniciada. Modelagem em iteração. Ritmo avaliado como "ótimo"
  pelo orientador em 30/09/2026.

## 2. Pergunta de pesquisa

> Com os indicadores educacionais de uma escola de Roraima no ano `t`,
> é possível estimar a taxa de abandono esperada no ano `t+1` — nos
> anos finais do ensino fundamental e no ensino médio — para apoiar
> ações preventivas de gestão?

## 3. Escopo

### O que o projeto faz

- Trabalha com **escola-ano** como unidade de análise.
- Foca nas **escolas de Roraima**.
- Cobre **anos finais do ensino fundamental** (9º ano) e **ensino
  médio** (1ª, 2ª, 3ª série).
- Usa dados **públicos** consultados na **Base dos Dados** (BD), que
  reúne e padroniza microdados e indicadores do INEP em um data lake
  no BigQuery.
- Prevê **taxa de abandono em `t+1`**, a partir de indicadores de `t`.
- Entrega **dois modelos**: um para anos finais, um para ensino médio.
- Estrutura a aquisição para **crescer**: novas tabelas da BD entram
  como novas consultas SQL, sem reescrever o pipeline (ver
  `02_DADOS.md`, Parte E).

### O que o projeto NÃO faz

- **Não prevê alunos individuais.** Análise agregada no nível da
  escola.
- **Não trata de evasão.** Abandono é o aluno que deixa de frequentar
  durante o ano letivo (existe por escola). Evasão é o aluno que não
  se matricula no ano seguinte (só é publicada de forma agregada).
  Este projeto trata de **abandono**.
- **Não ranqueia nem pune escolas.** O resultado destina-se a
  priorizar escolas para diagnóstico e apoio.
- **Não é causal.** Importância preditiva não é causalidade. Dizer
  "TDI contribuiu para a previsão" ≠ "TDI causa abandono".
- **Não baixa arquivos brutos.** Não há download de zips, extração
  local nem validação de arquivos por hash. Os dados são consultados
  por SQL na nuvem e o projeto guarda apenas recortes (snapshots)
  usados nos experimentos.

## 4. Justificativa

- Abandono escolar é fenômeno crítico, especialmente em Roraima, onde
  há escolas indígenas, rurais, ribeirinhas e em assentamentos com
  dinâmicas próprias.
- O Estado precisa priorizar recursos de intervenção — não há equipe
  para acompanhar todas as escolas.
- Um modelo que antecipa um ano à frente quais escolas terão abandono
  elevado permite ação preventiva.
- A separação entre anos finais e ensino médio permite comparar uma
  etapa atingida por política específica (Pé-de-Meia, no EM) com
  outra não atingida (fundamental) — comparação útil mesmo sem grupo
  de controle.
- A Base dos Dados reduz o custo de aquisição (sem 110 zips e 3 GB
  extraídos) e dá acesso a outras tabelas do mesmo padrão, o que
  facilita o enriquecimento futuro.

## 5. Produtos esperados

- **PIBIC:** relatório técnico-científico.
- **Disciplina:** artigo.
- **Código:** repositório público com consultas SQL, extração, base
  longitudinal e notebooks.
- **Reprodutibilidade:** consultas SQL versionadas no git, com hash
  registrado, e snapshots datados dos dados usados em cada experimento.

## 6. Base legal e ética

- Dados públicos, disponibilizados pelo INEP e tratados pela Base dos
  Dados. A licença de uso e a forma de citação devem ser conferidas no
  site da BD antes da publicação.
- Nenhum dado pessoal de aluno. As tabelas usadas são agregadas por
  escola.
- Unidade de análise agregada (escola), sem identificação individual.
- Uso explicitamente não punitivo.
- Credenciais de acesso à nuvem (projeto de faturamento do Google
  Cloud) não entram no repositório.

## 7. Delimitações temporais

- **Período alvo:** 2019 a 2025. A disponibilidade de cada ano na BD
  deve ser confirmada na verificação inicial (`02_DADOS.md`, §12).
- **Defasagem do desfecho:** o abandono de `t+1` só é conhecido bem
  depois do fim de `t+1` (segunda etapa do Censo Escolar, coletada no
  ano seguinte).
- **Último ano com alvo conhecido:** 2025, se a BD publicar o ano.
- **2026 em diante:** só poderá ser previsto quando o Censo
  correspondente for publicado e incorporado à BD.

---

# Parte B — Pessoas

O projeto é desenvolvido em grupo. Cada integrante contribui de forma
complementar — não há atribuição fixa de papéis; o trabalho é
distribuído conforme a necessidade de cada fase.

## Integrantes

- **Gustavo** — integrante do grupo.
- **Gabriela Monteiro** — integrante do grupo.
- **João Ricardo** — integrante do grupo.

## Orientação

- **Prof. Bruno Cesar Barreto Figueiredo** — orientador do projeto.

## Como o trabalho está organizado

- Encontros informais no grupo para alinhar o que cada um está
  fazendo.
- O orientador acompanha a evolução e dá retorno pontual sobre
  decisões metodológicas e resultados.
- Não há hierarquia rígida nem subgrupos fixos.

---

# Parte C — Estado atual

Data de referência: novembro/2026.

## 8. Concluído (pipeline legado, base INEP)

### Ambiente e dados

- Repositório clonado e rodando localmente.
- Base INEP reproduzida em 01/10/2026 (~3h52min para 110 zips). Esse
  processo **foi descontinuado** com a mudança de fonte (ver §9).
- Recorte de Roraima e inventários gerados a partir dos microdados e
  indicadores do INEP.

### Base longitudinal (legado)

- Gerada: **6.054 linhas × 59 colunas**, 934 escolas, 2019–2025,
  Roraima.
- Estrutura `ANO` (t) e `ANO_ALVO` (t+1) pronta.
- Alvos: `ABANDONO_FUN_T1`, `ABANDONO_FUN_AF_T1`, `ABANDONO_MED_T1`.
- Validações passaram: mesmas 6 escolas mudam de localização, mesmas
  105 mudam de nome ao longo da série.
- **Uso atual:** referência de comparação com a nova base da BD. Não é
  mais a base de referência para novos experimentos.

### Experimentos de modelagem (legado)

- **Smoke test** (split aleatório em 2025) — validou o pipeline.
- **v1_old** — pipeline metodologicamente correto (filtra públicas,
  usa Pipeline, One-Hot, split temporal). Resultado para anos finais:
  R² 0,162 no teste 2025; R² −0,078 na validação 2024. **Ensino
  médio não foi executado.** Instabilidade temporal real entre 2024
  e 2025. Nota: o v1_old usou todas as features numéricas no modelo
  AF, inclusive do EM — contraria a regra de separação por etapa.
  Corrigir antes de reproduzir.
- **v1 atual** — pipeline com 4 problemas conhecidos (não filtra
  públicas, imputação quebrada por tipo, imputação antes do split,
  descarta categóricas). Resultado preliminar:
  - **AF:** RandomForest R² 0,1843 | GradientBoosting R² 0,2011.
  - **EM:** RandomForest R² 0,1214 | GradientBoosting R² 0,0907.
- Esses números foram obtidos com a base INEP. **Não são comparáveis**
  com resultados da base da BD até a re-execução.

### Análise crítica

- Relatório do orientador (via LLM) com 12 pontos de melhoria. Aceito
  em quase totalidade.

### Achados científicos (legado, a revalidar)

- **TDI (distorção idade-série) é a variável mais importante** nos
  três casos analisados (v1_old AF, v1 atual AF, v1 atual EM).
  Consistente entre modelos e etapas.
- RMSE > MAE em ambos os modelos → existem outliers mal previstos.
- Modelo não generaliza entre anos (R² negativo na validação de
  2024).

## 9. Mudança de fonte de dados (novembro/2026)

| Item | Antes | Agora |
|---|---|---|
| Fonte primária | Arquivos `.zip` do INEP (110 arquivos, ~2,9 GB) | Base dos Dados, via SQL no BigQuery |
| Aquisição | Download, extração de ~3 GB, sha256 por arquivo, certificado TLS | `basedosdados` (`bd.read_sql`) com consultas parametrizadas |
| Recorte | Filtro em Python, após extração | Filtro e junções feitas na nuvem |
| Reprodutibilidade | Hash do arquivo | Hash da consulta + snapshot datado |
| Escopo de tabelas | Fixo (Censo + Indicadores) | Expansível (data lake da BD) |
| Restrição antiga | Base dos Dados descartada por falta de `tx_rend` | Restrição revogada; ver §10 |

## 10. Premissa sobre a taxa de rendimento

- A versão anterior descartava a Base dos Dados porque ela não tinha
  `tx_rend`.
- A restrição foi **revogada** por decisão do grupo. O projeto segue
  com a Base dos Dados assumindo que a taxa de rendimento está
  disponível na tabela atualizada, ou que pode ser derivada por SQL.
- **Essa premissa é um gate, não uma certeza.** A primeira etapa
  do pipeline novo verifica a presença de aprovação, reprovação e
  abandono por escola-ano em Roraima (`02_DADOS.md`, §3). Se a
  verificação falhar, a alternativa é registrada em
  `06_DECISOES_PROBLEMAS_PERGUNTAS.md` antes de qualquer modelagem.

## Pendente

### Verificação da fonte (bloqueante)

- Confirmar, no catálogo da BD, a tabela de indicadores educacionais
  e suas colunas.
- Confirmar presença de `tx_rend` (aprovação, reprovação, abandono) e
  cobertura de RR em 2019–2025.
- Registrar em `docs/fontes/` a tabela escolhida, grão, chave e data
  da consulta.

### Reconstrução da base longitudinal

- Escrever as consultas SQL de `sql/indicadores/`.
- Gerar o primeiro snapshot e a base longitudinal da BD.
- Comparar com a base INEP legada (contagens, escolas, alvos).

### Dados externos do orientador

- `dados/externo/base_longitudinal_v1/` — seis arquivos entregues em
  17/09/2026, ainda ausentes no clone local.
- Necessários para comparação com a base reproduzível.
- Registrar no `dados/metadados/snapshots.csv` com `estagio=externo`.

### Re-execução de modelos

- Repetir smoke test, v1 corrigido e walk-forward com a base da BD.
- Só então comparar com os números legados.

### Enriquecimento da base (Fase 3)

Ver `07_PLANOS.md`. Resumo:

- Escola indígena e localização diferenciada.
- Flag de elegibilidade.
- Flag de multisseriada.
- Esforço docente 2019–2020 e HAD.
- Pé-de-Meia.
- INSE (só para análise de grupos).
- Tabelas do data lake da BD (Censo Escolar, entre outras).

### Refinamento metodológico (Fase 2)

Ver `07_PLANOS.md`. Resumo:

- Corrigir os 4 problemas do pipeline legado (ou substituí-lo pelo
  novo, que já nasce com as correções).
- Adicionar baseline de persistência.
- Validação walk-forward.

### Publicação

- Artigo da disciplina — pendente.
- Relatório PIBIC — pendente.

---

# Parte D — Glossário

Três grupos: **siglas do INEP**, **fonte e infraestrutura** e
**termos do projeto**.

## Siglas e termos do INEP

| Sigla | Nome | O que é |
|---|---|---|
| **Censo Escolar** | Censo Escolar da Educação Básica | Microdados anuais com infraestrutura, dependências, equipamentos, profissionais, oferta, acessibilidade, escola indígena, terra indígena, assentamento. |
| **tx_rend** | Taxa de Rendimento Escolar | Aprovação, reprovação e abandono, por escola e por série. Fonte do alvo. Disponibilidade na BD a verificar (§10). |
| **TDI** | Taxa de Distorção Idade-Série | % de alunos com 2+ anos de atraso. |
| **ATU** | Média de Alunos por Turma | Tamanho médio das turmas. |
| **IED** | Indicador de Esforço Docente | Carga e complexidade do trabalho docente (N1–N6 + ALTO). |
| **HAD** | Média de Horas-Aula Diárias | Número médio de horas-aula por dia. |
| **INSE** | Indicador de Nível Socioeconômico | Nível socioeconômico médio dos alunos. Depende do Saeb; cobre ~metade das escolas públicas. |
| **Saeb** | Sistema de Avaliação da Educação Básica | Avaliação federal; condiciona o INSE. |
| **Pé-de-Meia** | Programa Pé-de-Meia | Programa federal em vigor desde 2024. Foca permanência e frequência no EM público. |
| **INEP** | Instituto Nacional de Estudos e Pesquisas Educacionais Anísio Teixeira | Órgão federal responsável pelos dados originais. |

## Fonte e infraestrutura

| Termo | O que é |
|---|---|
| **Base dos Dados (BD)** | Plataforma que organiza dados públicos brasileiros em tabelas padronizadas, com documentação e metadados. Fonte oficial do projeto. |
| **BigQuery** | Data warehouse do Google Cloud onde as tabelas da BD ficam. Consultado por SQL. |
| **`basedosdados`** | Biblioteca Python oficial para consultar a BD (`read_sql`, `read_table`). |
| **Projeto de faturamento** | Projeto no Google Cloud que recebe a cobrança das consultas. Obrigatório para executar SQL. Identificado por variável de ambiente. |
| **Data lake** | Conjunto de tabelas da BD que podem ser cruzadas com o projeto. Base da escalabilidade. |
| **Consulta versionada** | Arquivo `.sql` no git, identificado por hash. Registra exatamente o que foi extraído. |
| **Snapshot** | Cópia datada do resultado de uma consulta, usada como entrada dos experimentos. |

## Termos do projeto

### Unidade de análise

- **Escola-ano.** Cada linha é uma escola em um ano.
- **Anos finais.** 6º ao 9º ano. Foco no 9º.
- **Ensino médio.** 1ª, 2ª e 3ª séries.
- **Anos iniciais.** 1º ao 5º ano. Fora do escopo, mas presente na
  base como contexto.

### Desenho

- **t → t+1.** Features do ano `t`; alvo no ano `t+1`.
- **`ANO`.** Ano de referência das features.
- **`ANO_ALVO`.** Ano do desfecho. Sempre `ANO + 1`.
- **Sufixo `_T1`.** Marca alvos ("_T1" = target do ano seguinte).
- **Sufixo `_LAG1`.** Variável do ano anterior (t−1).
- **Sufixo `_DELTA1`.** Variação anual (t − (t−1)).

### Pré-processamento

- **Leakage (vazamento).** Usar, como feature, informação que não
  estaria disponível no momento da previsão.
  - **Temporal:** features e alvo do mesmo ano. Em SQL, o caso típico
    é uma função de janela olhando para o futuro (`LEAD`).
  - **Entre alvos:** usar `ABANDONO_FUN_T1` como feature para prever
    `ABANDONO_MED_T1` (mesmo período, variável irmã).
- **Baseline de persistência.** "abandono(t+1) = abandono(t)". Todo
  modelo real precisa bater esse baseline.
- **Missing estrutural.** Ausência que reflete o que a escola oferece,
  não erro.
- **Fan-out de junção.** Join que multiplica linhas quando a chave
  não é única. Verificado com contagens antes e depois.

### Split

- **Split aleatório.** Sorteio dentro do mesmo ano. Fácil, inflado.
- **Split temporal.** Treina em anos anteriores, testa no seguinte.
- **Walk-forward.** Validação ano a ano.

### Métricas

- **MAE** — erro médio absoluto (p.p.).
- **RMSE** — raiz do erro quadrático médio (p.p.).
- **R²** — fração da variância explicada além da média. **Não é
  acurácia.** Vai de −∞ a 1; negativo = pior que a média.
- **Precisão, Recall, F1** — classificação.
- **ROC-AUC, PR-AUC** — classificação em classes desbalanceadas.
- **Recall@K / Precision@K** — métrica operacional: das K escolas
  priorizadas, quantas realmente tinham alto abandono.

### Alvo

- **Abandono.** Aluno que deixa de frequentar durante o ano letivo.
  Existe por escola. **Alvo do projeto.**
- **Evasão.** Aluno que não se matricula no ano seguinte. Publicada
  agregada. **Não é o alvo.**
- **Zeros no alvo.** Alta fração de escolas com taxa = 0.
