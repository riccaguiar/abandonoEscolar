-- Fase 3.1: todas as colunas da tabela de indicadores por escola, para uma UF,
-- uma linha por escola-ano. Insumo da conferência escola a escola contra o INEP
-- (src/conferencia_rendimento.py).
--
-- Traz todas as colunas (e não só as 12 de rendimento) porque o diagnóstico de
-- 2023–2024 procura em que coluna foi parar cada valor.
-- UF pelo prefixo do código INEP da escola (id_municipio é nulo em 2022).
SELECT *
FROM `{{dataset}}.{{tabela}}`
WHERE STARTS_WITH(CAST(id_escola AS STRING), '{{uf_codigo}}')
  AND ano BETWEEN {{ano_inicio}} AND {{ano_fim}}
ORDER BY ano, id_escola
