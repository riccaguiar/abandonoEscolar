-- Etapa zero, passo 1: descobrir as colunas da tabela de indicadores por escola.
-- Consulta apenas metadados (INFORMATION_SCHEMA): não varre dados e
-- praticamente não consome cota do BigQuery.
-- Placeholders {{...}} são preenchidos por src/consultas.py (valores validados).
SELECT
  column_name,
  data_type
FROM `{{dataset}}.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = '{{tabela}}'
ORDER BY ordinal_position
