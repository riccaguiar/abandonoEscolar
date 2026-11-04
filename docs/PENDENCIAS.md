# Pendências

## P-BD-01 — Defeitos da tabela por escola da Base dos Dados

- **Status:** diagnosticado em 2026-11-04 (Fase 3.1); issue redigida, **não
  enviada** (aguarda aval do orientador).
- **Tabela:** `basedosdados.br_inep_indicadores_educacionais.escola`.
- **Defeitos** (detalhes em `docs/conferencia/RESULTADO_FASE_3_1.md`):
  - 2023–2024: colunas deslocadas 71 posições; o rendimento do INEP está na
    tabela, mas em outras colunas. TDI/ATU desses anos também suspeitos.
  - 2022: `id_escola` como `"14000016.0"` e `id_municipio` nulo. **Contornado**
    no código (normalização do `id_escola`; filtro de UF pelo prefixo).
  - 2025: não publicado na tabela por escola.
  - 2007: uma escola (`14320096`) sem aprovação do fundamental.
  - Tabela agregada `brasil`: sem rendimento em 2006, 2009 e 2010 (apontado
    pelo orientador; não reconferido aqui).
- **Impacto no projeto:** nenhum para 2023–2025, que vêm do INEP do grupo.
  Emendar BD + INEP não traz ganho (a opção antiga de baixar as planilhas de
  2023–2025 já foi feita pelo grupo).
- **Próximo passo:** levar o rascunho da issue ao orientador.
- **Como verificar se a BD corrigiu:** rodar
  `python -m src.conferencia_rendimento --extrair --base-inep ...`; os anos
  2023–2024 passam a ter `n_diferentes = 0`.
