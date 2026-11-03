-- Série histórica da taxa de abandono nas escolas públicas: UF escolhida x Brasil.
-- Média simples entre escolas (cada escola pesa 1), o mesmo critério da base
-- longitudinal. Não é a taxa oficial agregada do INEP, que pondera por matrícula.
--
-- soma_af / soma_em = aprovação + reprovação + abandono; deve ficar ~100.
-- Anos longe disso têm colunas inconsistentes na BD e não devem ser plotados.
-- UF pelo prefixo do código INEP da escola (id_municipio é nulo em 2022 na BD).
WITH base AS (
  SELECT
    ano,
    STARTS_WITH(CAST(id_escola AS STRING), '{{uf_codigo}}') AS na_uf,
    taxa_abandono_ef_anos_finais AS ab_af,
    taxa_abandono_em AS ab_em,
    taxa_aprovacao_ef_anos_finais + taxa_reprovacao_ef_anos_finais
      + taxa_abandono_ef_anos_finais AS soma_af,
    taxa_aprovacao_em + taxa_reprovacao_em + taxa_abandono_em AS soma_em
  FROM `{{dataset}}.{{tabela}}`
  WHERE rede IN ('estadual', 'municipal', 'federal')
    AND ano BETWEEN {{ano_inicio}} AND {{ano_fim}}
)
SELECT
  ano, '{{uf}}' AS recorte,
  COUNT(ab_af) AS n_af, ROUND(AVG(ab_af), 2) AS abandono_af,
  COUNT(ab_em) AS n_em, ROUND(AVG(ab_em), 2) AS abandono_em,
  ROUND(AVG(soma_af), 1) AS soma_af, ROUND(AVG(soma_em), 1) AS soma_em
FROM base
WHERE na_uf
GROUP BY ano
UNION ALL
SELECT
  ano, 'BR' AS recorte,
  COUNT(ab_af), ROUND(AVG(ab_af), 2),
  COUNT(ab_em), ROUND(AVG(ab_em), 2),
  ROUND(AVG(soma_af), 1), ROUND(AVG(soma_em), 1)
FROM base
GROUP BY ano
ORDER BY recorte, ano
