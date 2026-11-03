# 03 — Metodologia

Como o problema é formulado, de onde vêm os dados, quais colunas
entram em cada etapa, como o pipeline é montado, como o modelo é
validado e como é avaliado.

---

# Parte A — Desenho e variáveis

## 1. Formulação

### 1.1 Pergunta operacional

> Dados os indicadores educacionais de uma escola de Roraima no ano
> `t`, qual a taxa de abandono esperada no ano `t+1` — nos anos finais
> do ensino fundamental e no ensino médio?

### 1.2 Unidade de análise

- **Escola-ano.** Cada linha é uma escola em um ano.
- Não é previsão por aluno, por turma ou por série específica.
- Alvo é uma taxa agregada, na escala percentual (0 a 100).

### 1.3 Desenho `t → t+1`

- Features: colunas do ano `t`.
- Alvo: coluna `*_T1` (do ano `t+1`).
- Colunas `_LAG1` (t−1) e `_DELTA1` (variação t − (t−1)) também são
  features legítimas.
- **Nunca** usar informação de `t+1` como feature.

### 1.4 Dois conjuntos separados

| Conjunto | Etapa | Alvo | Universo |
|---|---|---|---|
| **AF** | Anos finais (9º) | `ABANDONO_FUN_AF_T1` | Escolas que oferecem anos finais |
| **EM** | Ensino médio | `ABANDONO_MED_T1` | Escolas que oferecem EM |

**Por que separar:**

- Etapas têm redes, distribuições e comportamentos distintos.
- Missing estrutural é diferente.
- Permite comparar etapa atingida por política (Pé-de-Meia no EM) com
  etapa não atingida.

### 1.5 Um modelo por etapa

Não se treina um modelo único. Cada modelo vê só as features da sua
etapa. Evita padrões espúrios por causa do missing.

---

## 2. Features por etapa

### 2.1 Anos finais (AF)

**Numéricas:**

- `ATU_FUN_AF`, `ATU_FUN_TOTAL`.
- `TDI_FUN_AF`, `TDI_FUN_TOTAL`.
- `APROVACAO_FUN_AF`, `REPROVACAO_FUN_AF`, `ABANDONO_FUN_AF`.
- `ABANDONO_FUN_AF_LAG1`, `ABANDONO_FUN_AF_DELTA1`.
- `TDI_FUN_AF_DELTA1`, `ATU_FUN_AF_DELTA1`.
- `IED_FUN_ALTO`, `IED_FUN_N1`–`IED_FUN_N6`.
- `ATU_FUN_AI`, `TDI_FUN_AI`, `APROVACAO_FUN_AI`, `REPROVACAO_FUN_AI`,
  `ABANDONO_FUN_AI` (contexto).

**Flags:** `DISP_ATU`, `DISP_TDI`, `DISP_IED`, `DISP_REND`.

**Categóricas:** `LOCALIZACAO`, `DEPENDENCIA`, `CO_MUNICIPIO`.

> Nota: as colunas acima são os nomes lógicos do contrato
> (`02_DADOS.md`, §16). A lista só vale depois do mapeamento para a
> Base dos Dados (`02_DADOS.md`, §17).

### 2.2 Ensino médio (EM)

**Numéricas:**

- `ATU_MED_TOTAL`, `TDI_MED_TOTAL`.
- `APROVACAO_MED`, `REPROVACAO_MED`, `ABANDONO_MED`.
- `ABANDONO_MED_LAG1`, `ABANDONO_MED_DELTA1`.
- `TDI_MED_TOTAL_DELTA1`, `ATU_MED_TOTAL_DELTA1`.
- `IED_MED_ALTO`, `IED_MED_N1`–`IED_MED_N6`.
- Features do fundamental como contexto (decisão em aberto).

**Flags e categóricas:** iguais às do AF.

### 2.3 Nunca usar como feature

- **IDs e metadados:** `CO_ENTIDADE`, `NO_ENTIDADE`, `NO_MUNICIPIO`,
  `ANO`, `ANO_ALVO`.
- **Alvos irmãos:** para AF, remover `ABANDONO_MED_T1`; para EM,
  remover `ABANDONO_FUN_AF_T1`. Mesmo período, vazamento direto.
- **O próprio alvo.**
- **Colunas derivadas de `t+1`** de qualquer tipo, inclusive as
  construídas por janela em SQL.

---

## 3. Leakage — as três formas

### 3.1 Temporal

Usar informação de `t+1` para prever `t+1`. **Regra:** features vêm
de `t` ou antes.

### 3.2 Entre alvos

Os três `_T1` são do mesmo período. Usar um para prever o outro é
vazamento direto. **Regra:** sempre remover os outros `_T1`.

### 3.3 Por janela em SQL

Na Base dos Dados, a consolidação é feita em SQL. A forma mais comum
de vazamento temporal nesse contexto é uma função de janela que olha
para a frente:

- `LEAD(...) OVER (PARTITION BY id_escola ORDER BY ano)` usado para
  construir **feature**: vazamento.
- `LAG(...)` para `_LAG1` e `_DELTA1`: correto, olha para trás.
- `LEAD(...)` **somente** para construir `_T1`: correto, é o alvo.

**Regra:** `LEAD` só aparece na consulta de construção do alvo,
documentado no próprio arquivo `.sql`. O teste em `tests/` verifica
que nenhuma coluna de feature depende de `ANO + 1`.

---

## 4. Decisões em aberto sobre features

### 4.1 Features cruzadas entre etapas

Usar features do EM para prever AF (ou vice-versa) implica imputar
metade dos valores (escolas que não oferecem a outra etapa).
**Decisão atual:** manter cada modelo apenas com features da sua
etapa + do fundamental como contexto.

### 4.2 Categóricas

- `LOCALIZACAO` (2), `DEPENDENCIA` (4), `CO_MUNICIPIO` (15).
- **Decisão:** One-Hot para todas. Simples, interpretável, sem risco
  de leakage. Confirmar a contagem de categorias na base da BD.

### 4.3 Pico de 2022

Três opções em aberto:

- **A:** incluir 2022 no treino normalmente.
- **B:** treinar sem 2022, testar em 2023+.
- **C:** usar 2022 como teste natural (treinar em anos "normais").

Recomendação preliminar: B ou C.

---

# Parte B — Pipeline

## 5. Etapa zero: consolidação na nuvem

A base longitudinal começa na Base dos Dados, não em Python. A
consolidação dos indicadores educacionais é feita em SQL no BigQuery e
só o resultado final é carregado em DataFrame para treino.

### 5.1 Passos da consolidação

1. **Verificar a fonte** (`sql/verificacao/`): tabelas, colunas e
   cobertura de RR por ano. Gate: presença de `tx_rend` (ver
   `02_DADOS.md`, §3). Se falhar, o pipeline para.
2. **Filtrar Roraima na consulta**, não depois.
3. **Consolidar por escola-ano**: uma linha por (escola, ano), com as
   colunas de cada indicador. Indicadores de etapas diferentes entram
   como colunas, não como linhas.
4. **Cruzar tabelas** pela chave (escola, ano), com checagem de
   unicidade antes do join e contagem antes e depois.
5. **Construir `_LAG1` e `_DELTA1`** com `LAG`.
6. **Construir `_T1`** com `LEAD`, só nesta etapa, documentado.
7. **Carregar o resultado** em DataFrame e gravar o snapshot.

### 5.2 Esqueleto da consulta

Os nomes de tabela e coluna abaixo são placeholders. Os nomes reais
vêm da verificação da §5.1.

```sql
-- sql/indicadores/01_escola_ano.sql (esqueleto)
WITH rend AS (
  SELECT id_escola, ano, aprovacao_fun_af, reprovacao_fun_af, abandono_fun_af
  FROM `<projeto>.<dataset>.<tabela_rendimento>`
  WHERE sigla_uf = 'RR'
),
tdi AS (
  SELECT id_escola, ano, tdi_fun_af
  FROM `<projeto>.<dataset>.<tabela_tdi>`
  WHERE sigla_uf = 'RR'
),
base AS (
  SELECT r.*, t.tdi_fun_af
  FROM rend r
  LEFT JOIN tdi t USING (id_escola, ano)
)
SELECT
  b.*,
  LAG(b.abandono_fun_af) OVER (PARTITION BY b.id_escola ORDER BY b.ano) AS abandono_fun_af_lag1,
  LEAD(b.abandono_fun_af) OVER (PARTITION BY b.id_escola ORDER BY b.ano) AS abandono_fun_af_t1
FROM base b
```

Pontos de atenção no esqueleto:

- `LEAD` aparece só em `abandono_fun_af_t1`, que é o alvo.
- O `LEFT JOIN` mantém as escolas de `rend`. Se `tdi` tiver mais de
  uma linha por (escola, ano), o resultado duplica. Por isso a
  unicidade é checada antes.
- O `LEAD` usa a série completa da escola. Se a escola não tiver o
  ano seguinte, o alvo é nulo. Isso é o comportamento esperado.

## 6. Ordem correta do pipeline

1. Consolidação na nuvem (§5).
2. Carregar o snapshot em DataFrame.
3. Checagens: grão, unicidade, contagens por ano, tipos.
4. Filtrar para o alvo (AF ou EM).
5. Filtrar apenas escolas públicas (`REDE_PUBLICA == 1`).
6. Remover linhas com alvo nulo.
7. **Separar treino / validação / teste.**
8. **Ajustar o pré-processamento só no treino.**
9. **Aplicar no teste.**
10. Treinar o modelo.
11. Avaliar.

**Fazer 8 e 9 antes de 7 é leakage.**

## 7. Tratamento de missing

O missing é **estrutural**. Decisões:

- **Não imputar tudo cegamente.** Escola sem EM não deve ter
  `IED_MED_ALTO` imputado.
- **Filtrar por etapa primeiro.**
- **Imputar apenas o que sobrar.**

### 7.1 Imputer

```python
numeric_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler',  StandardScaler()),
])
categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='constant', fill_value='Missing')),
    ('onehot',  OneHotEncoder(handle_unknown='ignore', sparse_output=False)),
])
```

Mediana porque há outliers fortes. `handle_unknown='ignore'`
para o teste não quebrar com categoria nova.

### 7.2 ColumnTransformer

```python
preprocessor = ColumnTransformer([
    ('num', numeric_transformer, num_cols),
    ('cat', categorical_transformer, cat_cols),
], remainder='drop')
```

`num_cols` e `cat_cols` definidos **depois** de remover alvo e alvos
irmãos. Erro comum: definir antes e incluir o alvo por engano.

---

## 8. Split

### 8.1 Aleatório

- Sorteio dentro do mesmo ano.
- **Uso:** apenas smoke test.
- **Problema:** superestima. Modelo vê escolas do mesmo ano no treino
  e teste.

### 8.2 Temporal

- Treina em anos anteriores, testa no seguinte.
- **Uso:** avaliação realista.
- **Limitação:** um único ponto de teste.

### 8.3 Walk-forward

- Treina em 2019–2020, testa 2021; treina em 2019–2021, testa 2022;
  e assim por diante.
- **Vantagem:** distribuição de R² entre folds, revela
  instabilidade.
- **Exemplo legado:** v1_old teve R² 0,162 no teste 2025 e R² −0,078
  na validação 2024. Walk-forward tornaria isso explícito.

### 8.4 Decisão em aberto

| Opção | Treino | Validação | Teste |
|---|---|---|---|
| A | 2020–2022 | 2023 | 2024–2025 |
| B | 2020–2021 + 2023 | 2024 | 2025 |
| C | walk-forward | | |

Recomendação preliminar: B ou C.

---

## 9. Baseline de persistência

Antes de qualquer modelo:

> Previsão de abandono(t+1) = abandono(t) da mesma escola.

**Métricas esperadas (legado, a recalcular na base da BD):**

- MAE ≈ 2,5 p.p.
- RMSE ≈ 3,8 p.p.
- R² = 0 (por definição).

Todo modelo precisa bater esse baseline. R² 0,20 e MAE 2,4 é
marginalmente melhor. MAE 3,0 é pior, mesmo com R² positivo.

---

## 10. Problemas conhecidos

### 10.1 Pipeline legado (checklist de regressão)

O `v1.ipynb` tinha 4 problemas. Ele será substituído pelo pipeline da
Parte B, que já nasce com as correções. Os itens abaixo viram testes
de regressão: o novo pipeline não pode reproduzi-los.

#### 10.1.1 Não filtra escolas públicas

Removido em relação ao v1_old. Privadas têm abandono menor; misturar
facilita artificialmente.
**Correção:** `df[df['REDE_PUBLICA'] == 1]`.

#### 10.1.2 Imputação quebrada por tipo

Código filtra `float64`/`int64`, mas base usa `Float64`, `Int8`,
`Int16`. Depois um `fillna(0)` transforma ausência em zero.
**Correção:** `select_dtypes(include='number')` e tipos nulos
tratados explicitamente.

#### 10.1.3 Imputação antes do split

Imputer aprende estatísticas do teste. Leakage sutil.
**Correção:** mover imputação para dentro do `Pipeline`.

#### 10.1.4 Categóricas descartadas

`select_dtypes(include=[np.number])` elimina `LOCALIZACAO`,
`DEPENDENCIA`, `CO_MUNICIPIO`.
**Correção:** `ColumnTransformer`.

### 10.2 Riscos novos da fonte Base dos Dados

- **`LEAD` em feature:** vazamento silencioso no SQL. Controle: §3.3 e
  teste de feature.
- **Fan-out de join:** duplicação de linhas em junção de tabelas. Controle:
  checagem de unicidade e contagens (§5.1, passo 4).
- **Mudança de schema entre versões:** coluna renomeada quebra o
  pipeline ou, pior, muda o significado. Controle: teste de schema e
  registro da versão no snapshot.
- **Tipos da BD:** nulos com tipos do pandas. Controle: §10.1.2.
- **Revisão da fonte:** a BD pode corrigir dados. Controle: snapshot
  datado e comparação de contagens (`02_DADOS.md`, §13).

---

## 11. Modelos

### 11.1 Regressão (tarefa principal)

```python
modelos = {
    'Ridge': Ridge(alpha=1.0, random_state=RANDOM_STATE),
    'RandomForest': RandomForestRegressor(
        n_estimators=300, max_depth=10, min_samples_leaf=3,
        random_state=RANDOM_STATE, n_jobs=-1,
    ),
    'HistGradientBoosting': HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.05, max_depth=6,
        random_state=RANDOM_STATE,
    ),
}
```

### 11.2 Classificação (segunda tarefa, Fase 4)

Transformar alvo em binário (`abandono_t1 > limiar`). Treinar
classificadores. Avaliar com precisão/recall/F1 e Recall@K. Ver
`07_PLANOS.md`.

---

## 12. Reprodutibilidade

- `RANDOM_STATE = 1` fixo.
- `np.random.seed(RANDOM_STATE)`.
- `random_state=RANDOM_STATE` explícito em modelos e split.
- **Snapshot de entrada:** todo experimento registra o `snapshot_id`
  (linha em `dados/metadados/snapshots.csv`) e o hash da consulta SQL.
- **Versão da biblioteca:** `basedosdados` fixada em `requirements.txt`.
- Resultado sem `snapshot_id` não entra em relatório.

---

# Parte C — Métricas

## 13. Regressão

### 13.1 MAE — Erro Médio Absoluto

```text
MAE = média(|y_real − y_previsto|)
```

Em média, por quantos pontos percentuais (p.p.) o modelo erra. Mesma
unidade do alvo. Fácil de interpretar.

### 13.2 RMSE — Raiz do Erro Quadrático Médio

```text
RMSE = sqrt(média((y_real − y_previsto)²))
```

Sempre ≥ MAE.

- Se RMSE ≈ MAE: erros uniformes.
- Se RMSE ≫ MAE: existem outliers.

### 13.3 R² — Coeficiente de Determinação

```text
R² = 1 − (SQ_resíduos / SQ_total)
```

Fração da variância do alvo explicada além da média.

- R² = 1,0 — perfeito.
- R² = 0,0 — igual a prever a média.
- R² < 0 — pior que a média.

**Armadilha:** R² não é acurácia. R² = 0,20 significa "explicou
20% da variância além da média".

No projeto: R² entre 0,10 e 0,30 é modesto mas real. R² negativo
é informação importante.

### 13.4 Como reportar

- MAE e RMSE em pontos percentuais (p.p.), não em "%".
- R² sem unidade.
- Sempre comparar com o baseline.
- Indicar o `snapshot_id` de cada número.

---

## 14. Classificação (Fase 4)

### 14.1 Acurácia

Acertos totais / total. Enganosa em classes desbalanceadas. Não
usar como métrica principal.

### 14.2 Precisão

"Das escolas apontadas como alto risco, quantas realmente eram."

`VP / (VP + FP)`

### 14.3 Recall

"Das escolas que realmente tiveram alto abandono, quantas o modelo
antecipou."

`VP / (VP + FN)`

**Métrica crítica do projeto.** Errar dizendo que uma escola não está
em risco significa perder a chance de agir preventivamente.

### 14.4 F1

Média harmônica entre precisão e recall.

### 14.5 ROC-AUC

Área sob a curva ROC. Otimista em classes desbalanceadas.

### 14.6 PR-AUC

Área sob a curva Precisão-Recall. Mais informativa em classes
desbalanceadas. **Preferir.**

---

## 15. Métricas operacionais — Recall@K

Pergunta operacional:

> Se o Estado tivesse recursos para atuar preventivamente em apenas
> 30 escolas, quantas das escolas que efetivamente apresentariam
> abandono elevado o sistema conseguiria indicar um ano antes?

### 15.1 Como calcular

1. Ordenar escolas por risco previsto (decrescente).
2. Pegar as K primeiras.
3. Comparar com as K de maior abandono real.

- **Recall@K:** das escolas que realmente tiveram alto abandono,
  quantas estão entre as K previstas.
- **Precision@K:** das K previstas, quantas realmente tiveram.

### 15.2 Valores de K

Top 10, 20, 30, 50.

### 15.3 Por que é a métrica mais importante

- Aderente ao uso real.
- Interpretável fora da estatística.
- Combina com o desenho (priorizar, não prever com precisão).

Exemplo forte: "priorizando 30 das 235 escolas, o modelo
identificou 72% das que depois tiveram abandono elevado".

---

## 16. Prioridade das métricas

1. **Recall@K** — métrica operacional principal.
2. **MAE, RMSE** — erro absoluto em p.p.
3. **R²** — capacidade explicativa global.
4. **Precision@K** — custo da priorização.
5. **PR-AUC** — classificação.
6. **Precisão, Recall, F1** — classificação.
7. **Acurácia** — só por completude.

Sempre comparar com o baseline de persistência.
