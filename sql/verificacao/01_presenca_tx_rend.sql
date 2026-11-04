-- Etapa zero, passo 2 (gate de 02_DADOS.md, §3): a taxa de rendimento
-- (aprovação, reprovação, abandono) existe por escola-ano na BD?
--
-- Para cada ano devolve:
--   n_linhas, n_escolas  -> cobertura
--   n_duplicadas         -> deve ser 0 (chave escola-ano única)
--   nn_<coluna>          -> quantas escolas têm valor NÃO nulo na coluna
--   n_soma_fora_<etapa> -> linhas com as três taxas e |aprovação + reprovação +
--                          abandono − 100| acima da tolerância; deve ser 0.
--                          No INEP a soma fecha linha a linha (desvio ≤ 3e-14).
--   n_trio_parcial_<etapa> -> linhas com só uma ou duas das três taxas; deve ser 0.
--   (etapa: af = anos finais do fundamental, em = ensino médio)
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
  COUNTIF(ABS(taxa_aprovacao_ef_anos_finais + taxa_reprovacao_ef_anos_finais
              + taxa_abandono_ef_anos_finais - 100) > {{tolerancia}}) AS n_soma_fora_af,
  COUNTIF(ABS(taxa_aprovacao_em + taxa_reprovacao_em + taxa_abandono_em - 100)
          > {{tolerancia}}) AS n_soma_fora_em,
  COUNTIF((IF(taxa_aprovacao_ef_anos_finais IS NULL, 0, 1)
           + IF(taxa_reprovacao_ef_anos_finais IS NULL, 0, 1)
           + IF(taxa_abandono_ef_anos_finais IS NULL, 0, 1)) IN (1, 2)) AS n_trio_parcial_af,
  COUNTIF((IF(taxa_aprovacao_em IS NULL, 0, 1) + IF(taxa_reprovacao_em IS NULL, 0, 1)
           + IF(taxa_abandono_em IS NULL, 0, 1)) IN (1, 2)) AS n_trio_parcial_em,
  {{contagens_nao_nulos}}
FROM `{{dataset}}.{{tabela}}`
WHERE STARTS_WITH(CAST(id_escola AS STRING), '{{uf_codigo}}')
  AND ano BETWEEN {{ano_inicio}} AND {{ano_fim}}
GROUP BY ano
ORDER BY ano
