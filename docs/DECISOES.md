# Log de decisões deste repositório

Uma entrada por decisão, com data, no padrão do `docs/DECISOES.md` do grupo.
Decisões de objetivo e método do projeto **não** entram aqui: são do grupo e do
orientador (`gabsma25/abandono-escolar`, `docs/DECISOES.md`).

---

## 2026-11-03 — Base dos Dados como abordagem de aquisição desta frente

**Decisão:** este repositório consulta a tabela
`basedosdados.br_inep_indicadores_educacionais.escola` por SQL no BigQuery
(biblioteca `basedosdados`), sem baixar arquivos do INEP.

**Revisão (2026-11-04):** a primeira versão chamava a BD de "fonte oficial do
projeto". Após o retorno do orientador, ela passa a ser a **abordagem
complementar** deste repositório: verificação das bases do grupo e possível
extensão do painel (`docs/CONTEXTO.md` §3). O pipeline oficial continua sendo
o do grupo, pelo INEP.

**Alternativa descartada:** substituir o pipeline do grupo pela BD — a BD tem
2023–2024 quebrados e não tem 2025.

---

## 2026-11-03 — UF filtrada pelo prefixo do código da escola

**Decisão:** a UF é filtrada pelos 2 primeiros dígitos de `id_escola` (código
INEP da escola = código IBGE da UF; RR = `14`).

**Evidência:** a tabela não tem `sigla_uf`; `id_municipio` é nulo em todas as
linhas de 2022 (RR sumia desse ano). Com o prefixo de `id_escola`, as contagens
de RR em 2021, 2023 e 2024 são idênticas às obtidas por `id_municipio`.

**Alternativa descartada:** junção com o diretório de municípios da BD — mais
uma dependência, e não resolveria 2022.

---

## 2026-11-04 — Normalização do `id_escola` de 2022

**Decisão:** remover o sufixo `.0` e exigir 8 dígitos
(`src/conferencia_rendimento.py`); qualquer outro formato é erro.

**Evidência:** em 2022 a BD grava `"14000016.0"` (870 de 870 escolas de RR);
sem normalizar, nenhuma escola de 2022 casa com o INEP. Depois de normalizar,
2022 confere escola a escola.

---

## 2026-11-04 — Gate linha a linha, tolerância 1e-6

**Decisão:** o gate da Etapa zero conta, por ano e etapa (AF, EM), escolas com
`|aprovação + reprovação + abandono − 100| > 1e-6` e escolas com só uma ou duas
das três taxas. Qualquer escola nessas condições reprova o ano.

**Evidência:** na BD de 2007–2022 (RR) o maior desvio é 1,4e-14; no INEP, 3e-14
(P026 do grupo). Em 2023–2024 há dezenas de escolas fora e centenas com trio
incompleto (`check_tx_rend` em `dados/metadados/snapshots.csv`).

**Alternativa descartada:** soma **média** até 1 p.p. de 100 (versão anterior):
uma média boa esconde linhas ruins, e o trio incompleto nem entra na média.

---

## 2026-11-04 — Gráfico: escolas inconsistentes fora da média

**Decisão:** no gráfico descritivo, escolas com soma fora de 100 ou trio
incompleto saem da média; o ano só é omitido quando elas passam de 1% das
escolas. O gate continua estrito.

**Evidência:** a regra estrita tirava o Brasil de 2007 inteiro por 3 escolas em
49.377.

---

## 2026-11-04 — Snapshots com hash do resultado e detecção de divergência

**Decisão:** cada snapshot registra o sha256 da consulta, do resultado (conteúdo
lido de volta) e do arquivo. Mesma consulta + mesmo resultado não grava de novo;
resultado diferente vai para `dados/cache/divergente/`, não substitui o anterior
e sai com código 3 (`--aceitar-divergencia` adota o novo). Ver `src/snapshots.py`.

**Evidência:** a mesma consulta do gráfico tinha rodado três vezes e gerado três
snapshots sem comparação (apontado pelo orientador). O hash da consulta prova o
que foi pedido, não o que voltou.

---

## 2026-11-04 — Versões fixadas; pandas 2.3.3

**Decisão:** dependências diretas com `==` em `requirements.txt`, ambiente
completo em `requirements-lock.txt`; numpy, pyarrow, pytest e scikit-learn
iguais aos do grupo. **Exceção:** pandas 2.3.3 (o grupo usa 3.0.5).

**Evidência:** `basedosdados` 2.0.3 depende de `pandavro`, que exige pandas < 3
(`pip check` acusa). A troca com o grupo é por Parquet. As saídas da Fase 3.1
ficaram idênticas byte a byte após a troca de versões.

**Pendente:** Python 3.12 (o do grupo); esta máquina só tem 3.14.

---

## 2026-11-04 — Documentação cita o grupo em vez de copiar

**Decisão:** removidos `01_PROJETO.md`, `02_DADOS.md` e `03_METODOLOGIA.md`;
no lugar, `docs/CONTEXTO.md`, que aponta para os documentos do grupo e lista as
correções das afirmações herdadas.

**Evidência:** as cópias carregavam o objetivo anterior a 2026-11-02 e três
afirmações que os dados derrubaram (apontado pelo orientador), além de
referências a arquivos e pastas que não existem neste repositório.

**Alternativa descartada:** corrigir as cópias — continuariam envelhecendo a
cada decisão nova do grupo.
