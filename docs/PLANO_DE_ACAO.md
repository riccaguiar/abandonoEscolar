# Plano de ação — retorno do orientador (novembro/2026)

Origem: mensagem do orientador sobre o commit `639e15b` (03/11/2026) e leitura
dos dois repositórios do grupo, indicados por ele como norte:

- `gabsma25/abandono-escolar` — pipeline oficial (INEP 2019–2025); registros de
  02/11 na branch `avaliacao-etapas-1-2` (`docs/DECISOES.md`,
  `docs/SINTESE_DO_PROJETO.md`, `CLAUDE.md`).
- `GustavoGGI/Dados-do-Projeto` — pipeline estendido `gustavo/` (rendimento
  2007–2025 + infraestrutura do Censo) e os `Relatórios do Projeto/`.

Status: **plano, nada implementado ainda.**

---

## 1. O norte: o que os dois repositórios mostram

### 1.1 O objetivo mudou (02/11/2026)

- **Antes:** estimar a taxa de abandono em t+1 e achar o melhor modelo.
- **Agora:** identificar **qual bloco de informação** sobre a escola no ano `t`
  carrega sinal sobre o abandono em `t+1` (AF e EM). A previsão é só o
  instrumento de medida.
- Um bloco carrega sinal quando melhora a **priorização (Recall@K, K = 10% e
  20%)** contra baselines pré-especificados (o principal é o **B1R_lag**:
  ordenar pelo abandono de t−1), no walk-forward, com **IC por bootstrap de
  escolas e correção de Holm**.
- Cenário B é o principal (sem rendimento de t). Blocos: 1 = rendimento
  defasado; 2 = +TDI e ATU; 3 = +IED N1..N5; 4 = +infraestrutura.
- A mudança ainda **não foi validada pelo orientador** (registrado como falha de
  processo no `DECISOES.md`).

### 1.2 O resultado e o gargalo

- 25 de 152 testes sobrevivem ao Holm. Nenhum modelo supera o B1R_lag e nenhum
  bloco supera o anterior (F5: 0 de 56).
- Leitura registrada: **falta de poder**, não ausência de sinal. São só 4
  transições de teste (2021–2024); o IC do Recall@10% agrupado tem ~0,15 de largura.
- O painel só começa em 2019 porque **TDI, ATU e IED por escola só existem na
  base oficial (2019–2025)**. Rendimento e infraestrutura já existem desde 2007
  (`gustavo/`), mas TDI/ATU/IED de 2007–2018 "não foram baixados". Estender o
  painel é a **D11, [DECIDIR] com o orientador**.

### 1.3 Onde a Base dos Dados entra (o papel do meu projeto)

A tabela `br_inep_indicadores_educacionais.escola` da BD vai de 2007 a 2024 e
tem, por escola, colunas de rendimento, **TDI, ATU, HAD e IED por etapa**
(inclusive `ied_ef_anos_finais_nivel_*`, que a base oficial não tem — hoje o
AF usa `IED_FUN`, uma exceção à D15). [FATO] para a existência das colunas;
**a cobertura de TDI/ATU/IED antes de 2019 ainda não foi verificada** (só o
rendimento foi, Fase 4.1).

Portanto o meu projeto **não é um pipeline de modelagem paralelo**. O papel
útil é:

1. **Verificação independente** das bases do grupo (a BD é outra rota até o
   mesmo dado do INEP). Em especial 2007–2018 do `gustavo/`, que hoje "não é
   reverificável" na máquina do grupo (síntese §5.2).
2. **Fornecedor de TDI/ATU/IED 2007–2018** para estender o painel, se a D11
   for aprovada, no formato que o instrumento do grupo consome.
3. **Não** é fonte para 2023–2025: esses anos estão quebrados ou ausentes na
   BD e já existem do INEP na base do grupo. Emendar BD + INEP não traz ganho.

### 1.4 Regras do grupo que meu código passa a seguir (`CLAUDE.md` §3)

- `CO_ENTIDADE` e `CO_MUNICIPIO` como `string`; taxas como `Float64` nullable.
- Todo `merge` com `validate="1:1"` e `how="left"` a partir da base.
- Toda contagem publicada é gerada por código, nunca digitada.
- Nunca imputar ausente estrutural como 0.
- Nunca selecionar variável pela correlação com o desfecho.
- Nunca usar aprovação + reprovação + abandono juntas como preditores
  (identidade contábil, P026); nunca IED N6/ALTO com N1..N5.
- Afirmações em docs com nível de evidência: [FATO], [MEDIDO], [PONTUAL],
  [EXPLORATÓRIO], [INTERPRETAÇÃO], [REFUTADO].
- Decisões em log datado (`DECISOES.md`), uma entrada por decisão.

---

## 2. Fases

### Fase 0 — Contexto que ainda falta

| # | Ação | Estado |
|---|---|---|
| 0.1 | Ler objetivo, decisões e síntese de 02/11 | **Feito** (seção 1). |
| 0.2 | Instrumento de avaliação `gustavo/avaliacao/` | **Não está público** (13 commits locais). Pedir ao Gustavo o push, para rodar o painel estendido se a D11 for aprovada. |
| 0.3 | Rendimento INEP de RR por escola | **Disponível**: `gustavo/saida/base_atual.parquet` (2007–2025, colunas harmonizadas) e `gustavo/cache/tx_rend/`. |
| 0.4 | TDI/ATU/IED INEP de RR por escola (2019–2025) | **Não versionado** (`abandono-escolar/dados/interim/indicadores_rr/`, regra 2). Pedir os arquivos ao grupo ou regerar com o `bootstrap.py` deles. |
| 0.5 | Perguntar ao orientador o que está confirmado (objetivo, Cenário B, B1R_lag, Holm, K) e se a D11 está aberta | Pendente — perguntas na seção 4. |

### Fase 1 — Documentação: alinhar e parar de duplicar

Os meus `01_PROJETO.md`, `02_DADOS.md` e `03_METODOLOGIA.md` são cópias
adaptadas dos `Relatórios do Projeto/`, que estão desatualizados e são a
origem dos erros apontados. Proposta: **não manter cópias**.

- Substituir os três por um `README.md` curto: o que é este repositório
  (verificação e extensão via BD), link para os documentos do grupo como
  referência de objetivo e método, e o que este repositório entrega.
- Manter só documentação própria: `docs/COMO_FUNCIONA.md`, `docs/COMO_USAR.md`,
  `docs/PENDENCIAS.md`, este plano, e um `docs/DECISOES.md` datado.
- Na reescrita, eliminar: "TDI é a variável mais importante" (só vale na forma
  restrita: árvore, [MEDIDO]); "B ou C" como recomendação; "R² da persistência = 0
  por definição" (errado fora da amostra); "BD é a fonte oficial"; o motivo
  errado "BD não tem `tx_rend`" (tem; o problema é 2023–2025).
- Rebaixar "2019–2022 batem com o legado" para o que foi conferido: contagem
  e média por ano × etapa em 2007–2022 (conferência do orientador); **escola a
  escola ainda não**.
- Atualizar `PENDENCIAS.md` (P-BD-01): a opção "baixar INEP 2023–2025" já está
  feita pelo grupo; a pendência vira diagnosticar e reportar à BD. Acrescentar:
  tabela `brasil` sem rendimento em 2006, 2009 e 2010.
- Corrigir o link do repositório do grupo (`gabsma25/abandono-escolar`).
- Remover referências a arquivos que não existem (`06_…`, `07_…`,
  `docs/fontes/`, `sql/indicadores/`, testes de schema e de `LEAD`).

### Fase 2 — Consertar o código de verificação (independe de terceiros)

1. **Gate linha a linha.** Contar, por ano e etapa, linhas com
   `|aprovação + reprovação + abandono − 100|` acima de uma tolerância numérica
   (no INEP o desvio máximo é 3e-14). Antes de fixar, olhar a distribuição real
   na BD em 2007–2022. Reprova com qualquer linha fora.
2. **Snapshots.** Registrar o sha256 do arquivo de resultado (o hash da
   consulta prova o pedido, não o que voltou). Mesma consulta + resultado igual
   = não grava de novo; resultado diferente = `dados/cache/divergente/`, aviso
   e código de saída próprio. Limpar os snapshots repetidos de `abandono_por_ano`.
3. **Ambiente igual ao do grupo.** Python 3.12; todas as versões com `==`,
   alinhadas ao `Dados-do-Projeto/requirements.txt` (scikit-learn 1.8.0 — a
   troca para 1.9.1 já mudou um resultado em até 0,0036).
4. **Tipagem e merges** conforme a seção 1.4.

### Fase 3 — Conferência escola a escola

> **3.1 feita em 2026-11-04** — `docs/conferencia/RESULTADO_FASE_3_1.md`. 2007–2022 confere
> escola a escola (1 escola divergente em 2007); 2022 tem `id_escola` como `"14000016.0"`;
> 2023–2024 têm as colunas deslocadas 71 posições. Rascunho de issue pronto, não enviado.

Compara a BD com o INEP por `(CO_ENTIDADE = id_escola, ANO)`.

1. **Rendimento 2007–2024** contra `gustavo/saida/base_atual.parquet`
   (`APROVACAO_*`, `REPROVACAO_*`, `ABANDONO_*` de AF e EM):
   - 2007–2022: esperado igual valor a valor. Vira **verificação independente
     de 2007–2018 do `gustavo/`**, que o grupo não consegue refazer hoje;
   - 2023–2024: para cada coluna da BD, procurar com qual coluna do INEP ela
     bate na mesma escola (colunas trocadas) ou se bate em outra escola (linhas
     desalinhadas). Explicar as ~95 escolas a mais no AF (BD 327/341 × INEP 233/240).
2. **TDI/ATU/IED 2019–2024** contra a base oficial (depende de 0.4). Mesma
   lógica; é o que decide se a BD serve para TDI/ATU/IED.
3. Conferir com consulta reproduzível o `id_municipio` nulo em 2022.
4. Saída: um CSV de divergências gerado por código e um **rascunho de issue**
   para a Base dos Dados. Abrir só com o aval do orientador.

### Fase 4 — Extensão do painel para 2007–2018 (só com a D11 aprovada)

1. Medir a cobertura por escola de TDI/ATU/IED da BD em RR, 2007–2018, e
   aplicar o gate linha a linha.
2. Gerar um Parquet no formato que o `painel.py` do grupo consome:
   `CO_ENTIDADE` (string), `ANO`, `TDI_*`, `ATU_*`, `IED_*` com os nomes da base
   oficial; uma linha por escola-ano; sha256 registrado.
3. Apresentar ao orientador quantas transições de teste a mais o painel ganha.
4. Rodar o instrumento do grupo (depende de 0.2) — quem decide os testes é o
   protocolo deles, não este repositório.

### Fase 5 — Do lado do orientador e do grupo (não é tarefa minha)

- Corrigir nos `Relatórios do Projeto/` as afirmações que eu herdei
  (`01_PROJETO.md:171`; `03_METODOLOGIA.md:132`, `:223`, `:237`).
- Publicar os registros de 02/11 no `main` e o `gustavo/avaliacao`.
- Registrar a correção da premissa da D1 (a BD tem as colunas de rendimento).

---

## 3. Ordem sugerida

1. Enviar as perguntas (seção 4) e o pedido ao Gustavo (0.2, 0.4).
2. Em paralelo: Fase 2 e Fase 3.1 (só dependem do que já é público).
3. Fase 1, depois da resposta do orientador sobre o objetivo.
4. Fase 3.2 quando chegarem os dados de TDI/ATU/IED.
5. Fase 4 só com a D11 decidida.

## 4. Perguntas para o orientador

1. O objetivo de 02/11 (qual bloco carrega sinal, Recall@K × B1R_lag, Holm) está
   confirmado? E o Cenário B e os K de 10% e 20%?
2. A D11 (estender o painel para 2007–2018) está aberta? Se a BD fornecer
   TDI/ATU/IED desses anos, conferidos escola a escola, o senhor considera?
3. O IED específico dos anos finais da BD (a base oficial só tem `IED_FUN`)
   interessa, ou a exceção à D15 fica como está?
4. Posso abrir a issue na Base dos Dados depois da conferência escola a escola?
5. Quer que eu proponha o texto do registro sobre a premissa da D1?
