# abandonoEscolar — verificação e extensão via Base dos Dados

Parte do projeto de pesquisa **Risco de abandono escolar em Roraima**
(PIBIC/UERR, Edital 35/2026; orientador: Prof. Bruno Cesar Barreto Figueiredo).

Este repositório é a **abordagem pela [Base dos Dados](https://basedosdados.org/)**
(BD), ao lado da abordagem do grupo, que trabalha direto com os arquivos do INEP:

| Repositório | Papel |
|---|---|
| [gabsma25/abandono-escolar](https://github.com/gabsma25/abandono-escolar) | Pipeline oficial do INEP (2019–2025), objetivo, decisões e síntese do projeto. Referência de método. |
| [GustavoGGI/Dados-do-Projeto](https://github.com/GustavoGGI/Dados-do-Projeto) | Base estendida `gustavo/` (rendimento 2007–2025 + infraestrutura do Censo). |
| **este** | Consulta à BD por SQL no BigQuery para **verificar** as bases do grupo e, se aprovado, **estender** o painel com TDI/ATU/IED de 2007–2018. |

O objetivo do projeto, as decisões e o protocolo de avaliação estão no
repositório do grupo (`CLAUDE.md` §1, `docs/DECISOES.md`, `docs/SINTESE_DO_PROJETO.md`
na branch `avaliacao-etapas-1-2`). Este repositório não define método nem treina modelos.

## Estado (novembro/2026)

- **Rendimento 2007–2022:** a BD confere com o INEP **escola a escola** nas 12
  taxas (uma escola divergente em 2007). [FATO]
- **2022:** `id_escola` vem como `"14000016.0"` na BD; o código normaliza. [FATO]
- **2023–2024:** as colunas da tabela por escola da BD estão **deslocadas 71
  posições**; não usar esses anos da BD. **2025** não publicado. [FATO]
- Detalhes: [`docs/conferencia/RESULTADO_FASE_3_1.md`](docs/conferencia/RESULTADO_FASE_3_1.md).
- Próximos passos e pendências: [`docs/PLANO_DE_ACAO.md`](docs/PLANO_DE_ACAO.md),
  [`docs/PENDENCIAS.md`](docs/PENDENCIAS.md).

> `01_PROJETO.md`, `02_DADOS.md` e `03_METODOLOGIA.md` são cópias adaptadas
> dos *Relatórios do Projeto* e estão **desatualizados** (objetivo anterior a
> 02/11/2026). Serão substituídos na Fase 1 do plano; não os use como referência.

## Como rodar

Pré-requisitos: Python 3.12+, acesso ao projeto `abandonoescolar1` no Google
Cloud (BigQuery). Na primeira consulta, o navegador abre para login no Google.

```powershell
cd C:\Users\Ricardo\Documents\abandonoEscolar
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

| Comando | O que faz |
|---|---|
| `python -m src.extracao_bd` | Etapa zero: verifica cobertura e consistência do rendimento na BD (gate). |
| `python -m src.conferencia_rendimento --base-inep <...>\base_atual.parquet` | Confere a BD com o INEP do grupo, escola a escola. |
| `python -m src.grafico_abandono --uf RR` | Gráfico da série de abandono (RR × Brasil, escolas públicas). |
| `python -m pytest -q` | Testes (sem rede e sem credenciais). |

Passo a passo, opções e erros comuns: [`docs/COMO_USAR.md`](docs/COMO_USAR.md).
Arquitetura: [`docs/COMO_FUNCIONA.md`](docs/COMO_FUNCIONA.md).

## Estrutura

```text
sql/verificacao/   consultas da Etapa zero e da conferência
sql/exploracao/    consultas descritivas (gráfico)
src/               extração, validação de parâmetros, conferência, gráfico
tests/             testes com a basedosdados simulada
docs/              guias, plano, pendências, resultados (docs/conferencia/)
dados/cache/       snapshots das consultas (fora do git)
dados/metadados/   registro dos snapshots (versionado)
```

## Regras

Este repositório segue as regras do grupo (`CLAUDE.md` §3 do `abandono-escolar`):
`CO_ENTIDADE` como texto, `merge` com `validate="1:1"`, contagens publicadas
geradas por código, nunca imputar ausente estrutural como 0. Consultas SQL
recebem parâmetros validados e nunca texto livre. Credenciais não entram no
repositório.
