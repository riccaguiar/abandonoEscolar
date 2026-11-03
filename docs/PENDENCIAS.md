# Pendências

## P-BD-01 — Anos 2023–2025 ausentes ou inconsistentes na Base dos Dados

- **Status:** pendente (decisão adiada em 03/11/2026).
- **Problema:** na tabela `basedosdados.br_inep_indicadores_educacionais.escola`:
  - 2022: `id_municipio` nulo em todas as linhas. **Contornado** com filtro por `id_escola`.
  - 2023 e 2024: aprovação + reprovação + abandono não fecha 100% (Brasil inteiro).
    Colunas aparentemente trocadas. Ex.: abandono anos finais RR = 16,6% (legado INEP: ~3%).
  - 2025: não publicado na tabela por escola. A tabela `brasil` já tem 2023–2025 corretos.
- **Impacto:** sem 2023–2025, o desenho de validação (2024) e teste (2025) fica sem dados.
  O gate da Etapa zero reprova por isso.
- **Opções:**
  1. **INEP original só para 2023–2025:** baixar as 3 planilhas de Taxas de Rendimento
     por escola, padronizar para os nomes de coluna da BD e juntar com a série da BD,
     com coluna de origem. Exige registrar exceção à regra "sem arquivos brutos".
  2. **Issue na Base dos Dados** (https://github.com/basedosdados) relatando os três
     problemas e aguardar a correção.
  3. Recomendado: fazer as duas; remover a exceção quando a BD corrigir e conferir os números.
- **Como verificar se a BD corrigiu:** `python -m src.extracao_bd`; o gate deixa de
  apontar `soma_af`/`soma_em` em 2023–2024 e o ano 2025 aparece.
