"""Extração da "Etapa zero": a taxa de rendimento existe na Base dos Dados?

Fluxo (ver docs/COMO_FUNCIONA.md):
  1. Descobre as colunas da tabela de indicadores por escola (INFORMATION_SCHEMA).
  2. Seleciona as colunas de aprovação/reprovação/abandono.
  3. Conta, por ano, escolas e valores não nulos dessas colunas (UF e anos dados).
  4. Salva o resultado como snapshot datado (Parquet ou CSV) e registra em
     dados/metadados/snapshots.csv.
  5. Avalia o gate e devolve o código de saída.

Códigos de saída: 0 = gate aprovado; 1 = erro técnico; 2 = gate reprovado;
3 = a mesma consulta devolveu resultado diferente do snapshot anterior.

Uso:  python -m src.extracao_bd --uf RR --ano-inicio 2019 --ano-fim 2025
"""

import argparse
import logging
import random
import re
import sys
import time

import pandas as pd

from src import config
from src.snapshots import SnapshotDivergente, salvar_snapshot
from src.consultas import (
    montar_contagens_nao_nulos,
    renderizar,
    validar_anos,
    validar_dataset,
    codigo_uf,
    formatar_tolerancia,
    validar_identificador,
    validar_uf,
)

log = logging.getLogger("extracao_bd")

COLUNAS_OBRIGATORIAS = {"ano", "id_escola"}
# Usadas nas somas de consistência (aprovação + reprovação + abandono ≈ 100).
COLUNAS_SOMA = [f"taxa_{t}_{e}" for e in ("ef_anos_finais", "em")
                for t in ("aprovacao", "reprovacao", "abandono")]
# Desvio máximo linha a linha aceito na soma. Na BD de 2007–2022 o maior desvio
# é 1,4e-14 (ruído de ponto flutuante); no INEP, 3e-14.
TOLERANCIA_SOMA = 1e-6
# Colunas que alimentam os desfechos do projeto (abandono AF e EM em t+1; docs/CONTEXTO.md §2).
COLUNAS_ALVO = ["taxa_abandono_ef_anos_finais", "taxa_abandono_em"]
# Colunas exibidas no resumo (a tabela tem ~100 colunas de rendimento por série).
_RE_RESUMO = re.compile(r"^nn_taxa_(aprovacao|reprovacao|abandono)_(ef|ef_anos_iniciais|ef_anos_finais|em)$")
_RE_RENDIMENTO = re.compile(r"(aprov|reprov|abandon)")
TENTATIVAS = 4
ESPERA_BASE_S = 2.0


class ErroExtracao(Exception):
    """Falha que não adianta repetir (credencial, tabela inexistente, SQL inválido)."""


# --------------------------------------------------------------------------
# Execução no BigQuery com tratamento de erros
# --------------------------------------------------------------------------
def _cadeia_excecoes(exc: BaseException):
    """Percorre a exceção e suas causas (a basedosdados costuma embrulhar erros)."""
    visto = set()
    while exc is not None and id(exc) not in visto:
        visto.add(id(exc))
        yield exc
        exc = exc.__cause__ or exc.__context__


def classificar_erro(exc: BaseException) -> tuple[bool, str]:
    """Devolve (pode_repetir, mensagem_para_o_usuario)."""
    try:
        from google.api_core import exceptions as gexc
        from google.auth import exceptions as aexc
    except ImportError:  # pragma: no cover
        return False, f"Dependências do Google ausentes: {exc}"

    transitorios = (
        gexc.ServiceUnavailable,
        gexc.InternalServerError,
        gexc.TooManyRequests,
        gexc.DeadlineExceeded,
        gexc.GatewayTimeout,
        gexc.BadGateway,
        ConnectionError,
        TimeoutError,
    )
    for e in _cadeia_excecoes(exc):
        if isinstance(e, transitorios):
            return True, f"Falha temporária de conexão com o BigQuery: {e}"
        if isinstance(e, (aexc.DefaultCredentialsError, aexc.RefreshError, gexc.Unauthenticated)):
            return False, (
                "Credenciais do Google ausentes ou expiradas. Faça o login "
                "(a basedosdados abre o navegador na primeira execução) e tente de novo."
            )
        if isinstance(e, gexc.Forbidden):
            return False, (
                "Acesso negado (403). Confira se o projeto de faturamento existe, tem "
                "faturamento ativo e se a API do BigQuery está habilitada. Detalhe: "
                f"{e}"
            )
        if isinstance(e, gexc.NotFound):
            return False, f"Tabela ou dataset não encontrado (404): {e}"
        if isinstance(e, gexc.BadRequest):
            return False, f"Consulta SQL rejeitada pelo BigQuery (400): {e}"
    return False, f"Erro inesperado na consulta: {exc!r}"


def executar_sql(sql: str, billing_project_id: str) -> pd.DataFrame:
    """Executa uma consulta via basedosdados com repetição em falhas temporárias."""
    import basedosdados as bd  # import tardio: só exigido quando de fato consulta

    for tentativa in range(1, TENTATIVAS + 1):
        try:
            return bd.read_sql(sql, billing_project_id=billing_project_id)
        except Exception as exc:  # noqa: BLE001 - classificamos abaixo
            pode_repetir, msg = classificar_erro(exc)
            if not pode_repetir:
                raise ErroExtracao(msg) from exc
            if tentativa == TENTATIVAS:
                raise ErroExtracao(f"{msg} (desisti após {TENTATIVAS} tentativas)") from exc
            espera = ESPERA_BASE_S * 2 ** (tentativa - 1) + random.uniform(0, 1)
            log.warning("%s Nova tentativa %d/%d em %.1fs", msg, tentativa + 1, TENTATIVAS, espera)
            time.sleep(espera)
    raise AssertionError("inalcançável")  # pragma: no cover


# --------------------------------------------------------------------------
# Etapa zero
# --------------------------------------------------------------------------
def descobrir_colunas(dataset: str, tabela: str, billing: str) -> list[str]:
    sql = renderizar("verificacao/00_colunas_indicadores_escola.sql", dataset=dataset, tabela=tabela)
    df = executar_sql(sql, billing)
    if df.empty:
        raise ErroExtracao(
            f"A tabela {dataset}.{tabela} não existe ou não tem colunas visíveis. "
            "Confira o nome no catálogo da Base dos Dados e ajuste src/config.py."
        )
    return [c.lower() for c in df["column_name"]]


def avaliar_gate(df: pd.DataFrame, colunas_rend: list[str], ano_inicio: int, ano_fim: int) -> list[str]:
    """Devolve a lista de problemas; vazia significa gate aprovado."""
    problemas = []
    esperados = set(range(ano_inicio, ano_fim + 1))
    presentes = set(df["ano"].astype(int)) if not df.empty else set()
    if esperados - presentes:
        problemas.append(f"Anos sem nenhuma linha: {sorted(esperados - presentes)}")
    if not df.empty and (df["n_duplicadas"] > 0).any():
        anos = sorted(df.loc[df["n_duplicadas"] > 0, "ano"].astype(int))
        problemas.append(f"Chave (id_escola, ano) duplicada nos anos {anos}")
    ausentes = [c for c in COLUNAS_ALVO if c not in colunas_rend]
    if ausentes:
        problemas.append(f"Colunas dos alvos ausentes na tabela: {ausentes}")
    # Para cada alvo presente, nenhum ano pode vir totalmente nulo.
    for c in (c for c in COLUNAS_ALVO if c in colunas_rend):
        sem_dado = [int(a) for a, n in zip(df["ano"], df[f"nn_{c}"]) if n == 0]
        if sem_dado:
            problemas.append(f"{c} é nula em todas as escolas nos anos {sem_dado}")
    # Linha a linha: aprovação + reprovação + abandono fecha 100 em cada escola,
    # e as três taxas vêm juntas. Uma média boa pode esconder linhas ruins.
    for etapa in ("af", "em"):
        for col, descricao in ((f"n_soma_fora_{etapa}", "soma das três taxas longe de 100"),
                               (f"n_trio_parcial_{etapa}", "só uma ou duas das três taxas")):
            if col in df:
                ruins = {int(a): int(n) for a, n in zip(df["ano"], df[col]) if n > 0}
                if ruins:
                    problemas.append(f"{etapa.upper()}: {descricao} (escolas por ano: {ruins})")
    return problemas


def etapa_zero(uf: str, ano_inicio: int, ano_fim: int, billing: str, formato: str,
               aceitar_divergencia: bool = False) -> int:
    uf = validar_uf(uf)
    ano_inicio, ano_fim = validar_anos(ano_inicio, ano_fim)
    dataset = validar_dataset(config.DATASET_INDICADORES)
    tabela = validar_identificador(config.TABELA_ESCOLA)

    log.info("Passo 1: descobrindo colunas de %s.%s", dataset, tabela)
    colunas = descobrir_colunas(dataset, tabela, billing)
    faltam = COLUNAS_OBRIGATORIAS - set(colunas)
    if faltam:
        raise ErroExtracao(
            f"Colunas obrigatórias ausentes na tabela: {sorted(faltam)}. "
            f"Colunas encontradas: {colunas}. Ajuste as consultas em sql/verificacao/."
        )
    faltam_soma = [c for c in COLUNAS_SOMA if c not in colunas]
    if faltam_soma:
        print(f"GATE REPROVADO: colunas de rendimento dos alvos ausentes: {faltam_soma}")
        return 2
    colunas_rend = [c for c in colunas if _RE_RENDIMENTO.search(c)]
    log.info("Colunas de rendimento encontradas (%d): %s", len(colunas_rend), colunas_rend)
    if not colunas_rend:
        print("GATE REPROVADO: nenhuma coluna de aprovação/reprovação/abandono na tabela.")
        print(f"Colunas existentes: {colunas}")
        return 2

    log.info("Passo 2: contando valores por ano (%s, %d-%d)", uf, ano_inicio, ano_fim)
    sql = renderizar(
        "verificacao/01_presenca_tx_rend.sql",
        dataset=dataset, tabela=tabela, uf_codigo=codigo_uf(uf),
        ano_inicio=ano_inicio, ano_fim=ano_fim, tolerancia=formatar_tolerancia(TOLERANCIA_SOMA),
        contagens_nao_nulos=montar_contagens_nao_nulos(colunas_rend),
    )
    df = executar_sql(sql, billing)
    caminho = salvar_snapshot(df, "check_tx_rend", sql, formato, aceitar_divergencia)
    log.info("Snapshot: %s", caminho)

    with pd.option_context("display.width", 200, "display.max_columns", None):
        resumo = ["ano", "n_linhas", "n_escolas", "n_duplicadas", "n_soma_fora_af", "n_soma_fora_em",
                  "n_trio_parcial_af", "n_trio_parcial_em"] + [
            c for c in df.columns if _RE_RESUMO.match(c)]
        print(df[resumo].to_string(index=False))
    problemas = avaliar_gate(df, colunas_rend, ano_inicio, ano_fim)
    if problemas:
        print("\nGATE REPROVADO:")
        for p in problemas:
            print(f" - {p}")
        return 2
    print("\nGATE APROVADO: rendimento presente e consistente linha a linha em todos os anos.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Etapa zero: verifica tx_rend na Base dos Dados.")
    ap.add_argument("--uf", default=config.UF_PADRAO)
    ap.add_argument("--ano-inicio", type=int, default=config.ANO_INICIO_PADRAO)
    ap.add_argument("--ano-fim", type=int, default=config.ANO_FIM_PADRAO)
    ap.add_argument("--formato", choices=["parquet", "csv"], default="parquet")
    ap.add_argument("--billing-project", default=config.BILLING_PROJECT_ID,
                    help="Projeto de faturamento (padrão: BD_BILLING_PROJECT_ID ou abandonoescolar1)")
    ap.add_argument("--aceitar-divergencia", action="store_true",
                    help="Adota o resultado novo quando difere do snapshot anterior da mesma consulta")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        return etapa_zero(args.uf, args.ano_inicio, args.ano_fim, args.billing_project, args.formato,
                          args.aceitar_divergencia)
    except SnapshotDivergente as e:
        log.error("%s", e)
        return e.codigo_saida
    except (ErroExtracao, ValueError) as e:
        log.error("%s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
