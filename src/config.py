"""Configuração central do projeto: caminhos, projeto de faturamento e tabela da BD."""

import os
from pathlib import Path

try:  # .env é opcional; sem python-dotenv usa só as variáveis do sistema
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

RAIZ = Path(__file__).resolve().parent.parent
DIR_SQL = RAIZ / "sql"
DIR_CACHE = RAIZ / "dados" / "cache"
DIR_METADADOS = RAIZ / "dados" / "metadados"
ARQ_SNAPSHOTS = DIR_METADADOS / "snapshots.csv"

# Projeto do Google Cloud que recebe a cobrança das consultas.
# A variável de ambiente tem prioridade sobre o padrão do projeto.
BILLING_PROJECT_ID = os.environ.get("BD_BILLING_PROJECT_ID", "abandonoescolar1")

# Tabela de indicadores por escola na Base dos Dados.
# ATENÇÃO: nomes assumidos, ainda não confirmados no catálogo. Se estiverem
# errados, o passo 1 da verificação falha com "tabela não encontrada".
DATASET_INDICADORES = "basedosdados.br_inep_indicadores_educacionais"
TABELA_ESCOLA = "escola"

UF_PADRAO = "RR"
ANO_INICIO_PADRAO = 2019
ANO_FIM_PADRAO = 2025
