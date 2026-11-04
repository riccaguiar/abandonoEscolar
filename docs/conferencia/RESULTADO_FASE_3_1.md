# Fase 3.1 — Rendimento escola a escola: Base dos Dados × INEP

Data: 2026-11-04. Script: `src/conferencia_rendimento.py` (testes em
`tests/test_conferencia_rendimento.py`). Números abaixo vêm das saídas do
script nesta pasta; para regerar:

```powershell
python -m src.conferencia_rendimento --base-inep <Dados-do-Projeto>\gustavo\saida\base_atual.parquet
```

## Entradas

| Lado | Arquivo | Identificação |
|---|---|---|
| BD | `basedosdados.br_inep_indicadores_educacionais.escola`, RR, 2007–2024, todas as colunas | snapshot e sha256 em `rendimento_metadados.json` |
| INEP | `gustavo/saida/base_atual.parquet` (GustavoGGI/Dados-do-Projeto, commit `f524873`) | sha256 em `rendimento_metadados.json` |

Chave: `(CO_ENTIDADE = id_escola, ANO)`, `merge` com `validate="1:1"`. Colunas:
as 12 taxas de rendimento (aprovação, reprovação e abandono × fundamental, anos
iniciais, anos finais, médio). Igual = diferença ≤ 1e-9.

## Resultados

### 2007–2022: a BD confere com o INEP escola a escola [FATO]

- 2008–2022: **todos** os pares escola × coluna presentes nos dois lados são
  iguais, e nenhuma escola tem a taxa num lado e não no outro
  (`rendimento_por_ano_coluna.csv`).
- 2007: tudo igual, exceto **uma escola** (`14320096`): a BD não tem a
  aprovação do fundamental e dos anos iniciais (INEP: 8,4); reprovação e
  abandono batem.
- Consequência: é a primeira conferência **independente e escola a escola**
  de 2007–2018 da base estendida do `gustavo/`, que a síntese do grupo
  (§5.2) registra como não reverificável na máquina do grupo. Vale para as 12
  taxas de rendimento, não para a infraestrutura.

### 2022: código da escola gravado como número [FATO]

- Em 2022 a BD grava `id_escola` como `"14000016.0"` (870 de 870 escolas de RR).
  Sem normalizar, nenhuma escola de 2022 casa com o INEP.
- Junto com o `id_municipio` nulo em 2022, indica conversão de tipo na carga
  desse ano.
- O script normaliza (remove `.0` e exige 8 dígitos); depois disso 2022 confere.

### 2023–2024: as colunas estão deslocadas 71 posições [FATO]

- Os valores de rendimento do INEP **estão na tabela**, mas 71 colunas adiante:
  cada uma das 12 taxas aparece, com o mesmo valor em todas as escolas e o
  mesmo padrão de nulos, na coluna 71 posições à direita da esperada
  (`rendimento_deslocamento.csv`). Ex.: aprovação do fundamental em
  `tnr_em_nao_seriado`; abandono do EM em `ied_ef_nivel_2`.
- Na exploração, o mesmo vale para as **54** colunas de rendimento por série
  (posições 136–189 da tabela, em vez de 65–118). [FATO na exploração; o
  script de produção confere as 12 do painel.]
- Por isso a soma aprovação + reprovação + abandono não fecha 100% nesses anos:
  as colunas `taxa_*` guardam outro conteúdo.
- O sintoma apontado pelo orientador (327 e 341 escolas de RR com "abandono dos
  anos finais" na BD × 233 e 240 no INEP) se explica assim: a contagem é de
  outro indicador que caiu na coluna, não de rendimento.
- TDI e ATU de 2023–2024 também parecem deslocados (médias de RR implausíveis:
  ATU dos anos finais ~38 alunos/turma; TDI do EM quase todo nulo). **Não
  conferido** contra o INEP (Fase 3.2, depende dos dados de TDI/ATU).

### Hipótese descartada

"A coluna de abandono da BD traz o TDI": descartada pelo orientador pela média
(TDI AF de RR 2023 = 27,7 no INEP) e agora pelo mecanismo: é um deslocamento de
posição, não a troca de uma coluna por outra.

## O que isso muda no plano

- A pendência com a BD agora tem diagnóstico exato (rascunho de issue abaixo).
- Para o projeto, 2023–2025 continuam vindo do INEP do grupo. Recuperar
  2023–2024 da BD desfazendo o deslocamento é possível para o rendimento, mas
  não traz ganho e não deve virar regra.
- Rendimento 2007–2022 da BD é confiável escola a escola, o que sustenta usar a
  BD como fonte de **TDI/ATU/IED 2007–2018** (D11), desde que esses indicadores
  passem pela mesma conferência nos anos em que existe INEP (2019–2022).

---

## Rascunho de issue para a Base dos Dados (não enviado)

> **Abrir só com o aval do orientador.**

**Título:** `br_inep_indicadores_educacionais.escola`: colunas deslocadas em 2023–2024 e `id_escola` como float em 2022

**Corpo:**

Comparamos a tabela `basedosdados.br_inep_indicadores_educacionais.escola`
com as planilhas de Taxas de Rendimento por escola do INEP, escola a escola,
para as escolas de Roraima (`id_escola` começando com `14`), 2007–2024.

1. **2023 e 2024 — colunas deslocadas.** Os valores de rendimento do INEP
   aparecem 71 colunas à direita da posição correta. Exemplo: o valor de
   aprovação do ensino fundamental (`taxa_aprovacao_ef`) está em
   `tnr_em_nao_seriado`; o de abandono do ensino médio (`taxa_abandono_em`), em
   `ied_ef_nivel_2`. A igualdade é exata em todas as escolas de RR, nas 54
   colunas de rendimento. Em consequência,
   `taxa_aprovacao_* + taxa_reprovacao_* + taxa_abandono_*` não soma 100 nesses
   anos, em todo o Brasil. As colunas de TDI e ATU desses anos também parecem
   afetadas.
2. **2022 — `id_escola` como float.** O código vem como `"14000016.0"`, o que
   impede o join com outras tabelas pelo código INEP. `id_municipio` está nulo
   em todas as linhas de 2022.
3. **2025** ainda não está na tabela por escola (a tabela `brasil` já tem).

De 2007 a 2022 (após normalizar o `id_escola` de 2022), as 12 taxas de
rendimento conferem exatamente com o INEP, exceto uma escola em 2007
(`14320096`, sem a taxa de aprovação do fundamental).

Consulta e script de conferência: [link para o repositório].
