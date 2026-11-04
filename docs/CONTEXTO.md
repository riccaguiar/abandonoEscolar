# Contexto: objetivo do projeto e papel deste repositório

Este documento substitui os antigos `01_PROJETO.md`, `02_DADOS.md` e
`03_METODOLOGIA.md` (removidos em 2026-11-04; continuam no histórico do git).
Eles eram cópias adaptadas dos *Relatórios do Projeto* e repetiam o objetivo
anterior e afirmações que os dados derrubaram (seção 4).

**Regra:** objetivo, método e decisões do projeto vivem no repositório do grupo.
Este repositório cita, não copia. Se algo aqui divergir de lá, vale lá.

Níveis de evidência, como no grupo: **[FATO]** verificável reexecutando código ·
**[MEDIDO]** com intervalo e correção para testes múltiplos · **[PONTUAL]** sem
intervalo ou sem sobreviver à correção · **[REFUTADO]**.

---

## 1. O projeto

- **Título:** Risco de abandono escolar em Roraima.
- **Tipo:** PIBIC/UERR (Edital 35/2026) e artigo da disciplina de Mineração de Dados.
- **Orientador:** Prof. Bruno Cesar Barreto Figueiredo (UERR).
- **Grupo:** Gabriela Monteiro (líder; repositório oficial), Gustavo (pipeline
  estendido `gustavo/`, agora com João Ricardo) e João Ricardo (este repositório).

| Repositório | Conteúdo |
|---|---|
| [gabsma25/abandono-escolar](https://github.com/gabsma25/abandono-escolar) | Pipeline oficial INEP 2019–2025. **Referência de objetivo e método**: `CLAUDE.md` §1, `docs/DECISOES.md` e `docs/SINTESE_DO_PROJETO.md`, na branch `avaliacao-etapas-1-2`. |
| [GustavoGGI/Dados-do-Projeto](https://github.com/GustavoGGI/Dados-do-Projeto) | Base estendida `gustavo/` (rendimento 2007–2025 + infraestrutura do Censo) e os *Relatórios do Projeto*. |

## 2. Objetivo vigente

Fonte: `abandono-escolar/CLAUDE.md` §1 e `docs/DECISOES.md`, entrada
"Mudança de objetivo" (2026-11-02).

> Identificar qual informação disponível sobre uma escola no ano `t` carrega
> sinal sobre o abandono no ano `t+1`, por etapa (anos finais e ensino médio).
> A previsão é o instrumento de medida.

- Um **bloco** de informação carrega sinal quando, no walk-forward, melhora a
  priorização das escolas (**Recall@K**, K = 10% e 20%) contra baselines
  pré-especificados — o principal é o **B1R_lag** (ordenar pelo abandono de
  `t−1`) —, com intervalo por bootstrap de escolas e **correção de Holm**.
- Blocos cumulativos (Cenário B, sem rendimento de `t`): 1 = rendimento
  defasado; 2 = + TDI e ATU; 3 = + IED N1..N5; 4 = + infraestrutura.
- **Validação do orientador: pendente.** O próprio registro do grupo marca a
  mudança como feita sem a consulta prévia exigida (falha de processo).
- Pergunta anterior (17/09 a 02/11/2026), mantida como registro: estimar a
  intensidade do abandono em `t+1` e comparar métodos. O produto deixou de ser
  "o melhor modelo".

O que não mudou (decisões do orientador de 17/09/2026, D1–D7 no `DECISOES.md`
do grupo): escola-ano; painéis separados AF e EM; universo de escolas públicas
com taxa na etapa; desfecho = abandono da etapa em `t+1`; TDI é preditor;
2020–2021 ficam na base; **2024→2025 é teste bloqueado**. Uso pretendido:
priorizar escolas para diagnóstico, nunca ranquear nem punir; não prevê aluno.

## 3. Papel deste repositório

A Base dos Dados (BD) é outra rota até os mesmos dados do INEP. Este
repositório **não modela e não define método**. Ele:

1. **Verifica** as bases do grupo de forma independente. Feito para o
   rendimento 2007–2024 (`docs/conferencia/RESULTADO_FASE_3_1.md`). [FATO]
2. **Pode fornecer TDI/ATU/IED de 2007–2018** para estender o painel do grupo,
   se a D11 for aprovada pelo orientador. Hoje o painel começa em 2019 porque
   esses indicadores só existem na base oficial a partir de 2019, e o resultado
   nulo do grupo é atribuído à falta de poder (4 transições de teste).
3. **Não** é fonte do desfecho nem de 2023–2025.

### Por que a BD não é fonte do desfecho

**Não** é por falta de taxa de rendimento: a tabela
`br_inep_indicadores_educacionais.escola` tem as colunas de aprovação,
reprovação e abandono por etapa e série, e elas conferem com o INEP escola a
escola em 2007–2022 [FATO]. O motivo é outro:

- 2023–2024: colunas deslocadas 71 posições na tabela por escola [FATO];
- 2025: não publicado [FATO];
- o grupo já tem 2019–2025 do INEP por escola; emendar BD + INEP não traz ganho.

## 4. Correções de afirmações herdadas

Estas afirmações estavam nos antigos `01_PROJETO.md` e `03_METODOLOGIA.md`,
copiadas dos *Relatórios do Projeto* (onde ainda estão; corrigi-las lá cabe ao grupo).

| Afirmação | Situação | Fonte |
|---|---|---|
| "TDI é a variável mais importante" | **[REFUTADO] na forma geral.** A evidência original (importância por coluna, com as três taxas juntas) é inválida (P026). O que sobrevive: na **árvore**, a importância do TDI passa na correção de Holm (AF em K 10% e 20%; EM em K 20%) [MEDIDO]; no Ridge, não [PONTUAL]. | Síntese do grupo §3.2 e §4 (#11) |
| Split "B ou C" como recomendação em aberto | **Superada.** O protocolo vigente é walk-forward com janela expansiva, testes 2021–2024, 2025 bloqueado (D7). | `DECISOES.md`, 2026-11-02, "Etapa 2" |
| "R² da persistência = 0 por definição" | **Errada.** Fora da amostra, o R² compara o erro com a média **do ano de teste**, que nenhum modelo conhece; por isso a persistência tem R² negativo na maioria das transições (segundo a conferência do orientador, até a média do treino tem). Na Etapa 1 do grupo, o R² da persistência (B1) é positivo em 1 de 17 transições no AF e 1 de 17 no EM; o MAE da persistência é menor que o da média em 11 de 17 (AF) e 6 de 17 (EM) [PONTUAL]. Por isso o projeto decide por Recall@K: a persistência é ruim para estimar o valor e boa para ordenar as escolas. | Síntese do grupo §3.4 |
| "A Base dos Dados é a fonte oficial do projeto" | **Revista.** É a abordagem complementar deste repositório (seção 3). | este documento |
| "A Base dos Dados não tem `tx_rend`" (D1 do doc 06 dos *Relatórios*) | **Premissa errada; conclusão mantida por outro motivo** (seção 3). Registro da correção no grupo: proposta pendente, redação do grupo/orientador. | `docs/conferencia/RESULTADO_FASE_3_1.md` |

## 5. Onde ler o resto

| Assunto | Arquivo |
|---|---|
| Como rodar | [`COMO_USAR.md`](COMO_USAR.md) |
| Como o código funciona | [`COMO_FUNCIONA.md`](COMO_FUNCIONA.md) |
| Decisões deste repositório | [`DECISOES.md`](DECISOES.md) |
| Plano e próximos passos | [`PLANO_DE_ACAO.md`](PLANO_DE_ACAO.md) |
| Defeitos da BD e pendências | [`PENDENCIAS.md`](PENDENCIAS.md) |
| Conferência BD × INEP | [`conferencia/RESULTADO_FASE_3_1.md`](conferencia/RESULTADO_FASE_3_1.md) |
