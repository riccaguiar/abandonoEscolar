-- Etapa zero, passo 2 (gate de 02_DADOS.md, §3): a taxa de rendimento
-- (aprovação, reprovação, abandono) existe por escola-ano na BD?
--
-- Para cada ano devolve:
--   n_linhas, n_escolas  -> cobertura
--   n_duplicadas         -> deve ser 0 (chave escola-ano única)
--   nn_<coluna>          -> quantas escolas têm valor NÃO nulo na coluna
--   soma_af, soma_em     -> média de aprovação + reprovação + abandono; deve ser ~100.
--                           Longe de 100 indica colunas trocadas na fonte.
--
-- O placeholder de contagens (abaixo, no SELECT) vira uma linha COUNTIF(<col> IS NOT NULL) por coluna
-- de rendimento encontrada no passo 1. Os nomes vêm do INFORMATION_SCHEMA e
-- são validados em src/consultas.py (apenas [a-z0-9_]).
-- A tabela não tem sigla_uf. A UF é filtrada pelos 2 primeiros dígitos do código
-- INEP da escola (= código IBGE da UF; RR = 14). id_municipio não serve: está
-- nulo em todo o ano de 2022 na BD (verificado em 03/11/2026).
SELECT
  ano,
  COUNT(*) AS n_linhas,
  COUNT(DISTINCT id_escola) AS n_escolas,
  COUNT(*) - COUNT(DISTINCT id_escola) AS n_duplicadas,
  ROUND(AVG(taxa_aprovacao_ef_anos_finais + taxa_reprovacao_ef_anos_finais
            + taxa_abandono_ef_anos_finais), 1) AS soma_af,
  ROUND(AVG(taxa_aprovacao_em + taxa_reprovacao_em + taxa_abandono_em), 1) AS soma_em,
  {{contagens_nao_nulos}}
FROM `{{dataset}}.{{tabela}}`
WHERE STARTS_WITH(CAST(id_escola AS STRING), '{{uf_codigo}}')
  AND ano BETWEEN {{ano_inicio}} AND {{ano_fim}}
GROUP BY ano
ORDER BY ano
