-- Série histórica da taxa de abandono nas escolas públicas: UF escolhida x Brasil.
-- Média simples entre escolas (cada escola pesa 1), o mesmo critério da base
-- longitudinal. Não é a taxa oficial agregada do INEP, que pondera por matrícula.
--
-- n_inconsistente_af / _em = linhas em que aprovação + reprovação + abandono
-- não fecha 100 (acima da tolerância) ou só parte das três taxas existe.
-- Essas linhas ficam fora da média e da contagem n_af / n_em.
-- O script do gráfico omite o ano quando elas passam de 1% (src/grafico_abandono.py).
-- UF pelo prefixo do código INEP da escola (id_municipio é nulo em 2022 na BD).
WITH base AS (
  SELECT
    ano,
    STARTS_WITH(CAST(id_escola AS STRING), '{{uf_codigo}}') AS na_uf,
    taxa_abandono_ef_anos_finais AS ab_af,
    taxa_abandono_em AS ab_em,
    (IF(taxa_aprovacao_ef_anos_finais IS NULL, 0, 1) + IF(taxa_reprovacao_ef_anos_finais IS NULL, 0, 1)
      + IF(taxa_abandono_ef_anos_finais IS NULL, 0, 1)) IN (1, 2)
      OR ABS(taxa_aprovacao_ef_anos_finais + taxa_reprovacao_ef_anos_finais
             + taxa_abandono_ef_anos_finais - 100) > {{tolerancia}} AS inconsistente_af,
    (IF(taxa_aprovacao_em IS NULL, 0, 1) + IF(taxa_reprovacao_em IS NULL, 0, 1)
      + IF(taxa_abandono_em IS NULL, 0, 1)) IN (1, 2)
      OR ABS(taxa_aprovacao_em + taxa_reprovacao_em + taxa_abandono_em - 100) > {{tolerancia}}
      AS inconsistente_em
  FROM `{{dataset}}.{{tabela}}`
  WHERE rede IN ('estadual', 'municipal', 'federal')
    AND ano BETWEEN {{ano_inicio}} AND {{ano_fim}}
)
SELECT
  ano, '{{uf}}' AS recorte,
  COUNTIF(ab_af IS NOT NULL AND NOT IFNULL(inconsistente_af, FALSE)) AS n_af,
  ROUND(AVG(IF(IFNULL(inconsistente_af, FALSE), NULL, ab_af)), 2) AS abandono_af,
  COUNTIF(ab_em IS NOT NULL AND NOT IFNULL(inconsistente_em, FALSE)) AS n_em,
  ROUND(AVG(IF(IFNULL(inconsistente_em, FALSE), NULL, ab_em)), 2) AS abandono_em,
  COUNTIF(inconsistente_af) AS n_inconsistente_af, COUNTIF(inconsistente_em) AS n_inconsistente_em
FROM base
WHERE na_uf
GROUP BY ano
UNION ALL
SELECT
  ano, 'BR' AS recorte,
  COUNTIF(ab_af IS NOT NULL AND NOT IFNULL(inconsistente_af, FALSE)),
  ROUND(AVG(IF(IFNULL(inconsistente_af, FALSE), NULL, ab_af)), 2),
  COUNTIF(ab_em IS NOT NULL AND NOT IFNULL(inconsistente_em, FALSE)),
  ROUND(AVG(IF(IFNULL(inconsistente_em, FALSE), NULL, ab_em)), 2),
  COUNTIF(inconsistente_af), COUNTIF(inconsistente_em)
FROM base
GROUP BY ano
ORDER BY recorte, ano
