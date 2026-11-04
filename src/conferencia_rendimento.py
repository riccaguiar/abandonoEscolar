"""Fase 3.1: conferência escola a escola do rendimento da BD contra o INEP.

Compara, por (escola, ano), as 12 taxas de rendimento (aprovação, reprovação e
abandono do fundamental, anos iniciais, anos finais e médio) da tabela
`br_inep_indicadores_educacionais.escola` da Base dos Dados com a base do INEP
harmonizada pelo grupo (`gustavo/saida/base_atual.parquet`, repositório
GustavoGGI/Dados-do-Projeto).

Nos anos em que a BD diverge, procura em qual coluna da BD cada taxa do INEP
foi parar (mesmo valor na mesma escola) e mede o deslocamento em posições.

Saídas (geradas por código; regra 9 do grupo):
  docs/conferencia/rendimento_por_ano_coluna.csv
  docs/conferencia/rendimento_deslocamento.csv
  docs/conferencia/rendimento_metadados.json

Uso:
  python -m src.conferencia_rendimento --base-inep <caminho>/base_atual.parquet
  python -m src.conferencia_rendimento --base-inep ... --extrair   (consulta a BD de novo)
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src import config
from src.consultas import codigo_uf, renderizar, validar_anos, validar_dataset, validar_identificador, validar_uf
from src.extracao_bd import ErroExtracao, executar_sql, salvar_snapshot

log = logging.getLogger("conferencia_rendimento")

DIR_SAIDA = config.RAIZ / "docs" / "conferencia"
PREFIXO_SNAPSHOT = "escolas_rr_todas_colunas"
TOLERANCIA = 1e-9  # mesmo valor; diferenças de ponto flutuante ficam em 1e-13

# Coluna da base do INEP (grupo) -> coluna da BD
MAPA_RENDIMENTO = {
    f"{tipo}_{etapa}": f"taxa_{tipo_bd}_{etapa_bd}"
    for tipo, tipo_bd in (("APROVACAO", "aprovacao"), ("REPROVACAO", "reprovacao"), ("ABANDONO", "abandono"))
    for etapa, etapa_bd in (("FUN", "ef"), ("FUN_AI", "ef_anos_iniciais"),
                            ("FUN_AF", "ef_anos_finais"), ("MED", "em"))
}


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def normalizar_id_escola(serie: pd.Series) -> tuple[pd.Series, int]:
    """Código INEP com 8 dígitos, como string.

    Em 2022 a BD grava o código como número convertido em texto ("14000016.0").
    Devolve a série normalizada e quantos valores precisaram de correção.
    """
    s = serie.astype("string")
    corrigir = s.str.fullmatch(r"\d{8}\.0").fillna(False)
    s = s.str.replace(r"\.0$", "", regex=True)
    invalidos = ~s.str.fullmatch(r"\d{8}").fillna(False)
    if invalidos.any():
        raise ValueError(f"id_escola fora do padrão de 8 dígitos: {s[invalidos].head().tolist()}")
    return s, int(corrigir.sum())


def comparar(inep: pd.DataFrame, bd: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por ano × coluna, com contagens de presença e igualdade."""
    juntos = inep[["ANO", "CO_ENTIDADE", *MAPA_RENDIMENTO]].merge(
        bd[["ANO", "CO_ENTIDADE", *MAPA_RENDIMENTO.values()]],
        on=["ANO", "CO_ENTIDADE"], how="outer", validate="1:1",
    )
    linhas = []
    for ano, g in juntos.groupby("ANO"):
        for col_inep, col_bd in MAPA_RENDIMENTO.items():
            x, y = g[col_inep].astype("float64"), g[col_bd].astype("float64")
            ambos = x.notna() & y.notna()
            dif = (x - y).abs()[ambos]
            linhas.append({
                "ano": int(ano), "coluna_inep": col_inep, "coluna_bd": col_bd,
                "n_inep": int(x.notna().sum()), "n_bd": int(y.notna().sum()),
                "n_ambos": int(ambos.sum()), "n_iguais": int((dif <= TOLERANCIA).sum()),
                "n_diferentes": int((dif > TOLERANCIA).sum()),
                "max_dif_abs": float(dif.max()) if len(dif) else float("nan"),
                "n_so_inep": int((x.notna() & y.isna()).sum()),
                "n_so_bd": int((y.notna() & x.isna()).sum()),
            })
    return pd.DataFrame(linhas)


def localizar_deslocamento(inep: pd.DataFrame, bd: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Para cada taxa do INEP, a coluna da BD com o mesmo valor na mesma escola.

    Só aceita coluna em que TODOS os pares são iguais e a presença (nulo/não nulo)
    coincide em todas as escolas do ano.
    """
    colunas_bd = list(bd.columns)
    numericas = [c for c in colunas_bd if pd.api.types.is_float_dtype(bd[c])]
    k = inep[inep["ANO"] == ano].merge(bd[bd["ANO"] == ano], on=["ANO", "CO_ENTIDADE"],
                                        how="inner", validate="1:1")
    linhas = []
    for col_inep, col_bd in MAPA_RENDIMENTO.items():
        x = k[col_inep].astype("float64")
        achadas = []
        for c in numericas:
            y = k[c].astype("float64")
            ambos = x.notna() & y.notna()
            if ambos.sum() == 0 or not (x.notna() == y.notna()).all():
                continue
            if ((x - y).abs()[ambos] <= TOLERANCIA).all():
                achadas.append(c)
        achada = achadas[0] if len(achadas) == 1 else None
        linhas.append({
            "ano": ano, "coluna_inep": col_inep, "coluna_bd_esperada": col_bd,
            "coluna_bd_encontrada": achada or ("; ".join(achadas) if achadas else ""),
            "n_escolas": int(x.notna().sum()),
            "deslocamento_posicoes": (colunas_bd.index(achada) - colunas_bd.index(col_bd)) if achada else None,
        })
    return pd.DataFrame(linhas)


def carregar_bd(extrair: bool, billing: str, ano_inicio: int, ano_fim: int) -> tuple[pd.DataFrame, Path]:
    if extrair:
        sql = renderizar(
            "verificacao/02_escolas_uf_todas_colunas.sql",
            dataset=validar_dataset(config.DATASET_INDICADORES),
            tabela=validar_identificador(config.TABELA_ESCOLA),
            uf_codigo=codigo_uf(validar_uf(config.UF_PADRAO)), ano_inicio=ano_inicio, ano_fim=ano_fim,
        )
        caminho = salvar_snapshot(executar_sql(sql, billing), PREFIXO_SNAPSHOT, sql)
    else:
        candidatos = sorted(config.DIR_CACHE.glob(f"{PREFIXO_SNAPSHOT}_*.parquet"))
        if not candidatos:
            raise ErroExtracao("Nenhum snapshot da BD em dados/cache/. Rode com --extrair.")
        caminho = candidatos[-1]
    return pd.read_parquet(caminho), caminho


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Conferência escola a escola do rendimento: BD x INEP.")
    ap.add_argument("--base-inep", default=os.environ.get("INEP_BASE_ATUAL"),
                    help="Caminho do base_atual.parquet do grupo (ou variável INEP_BASE_ATUAL)")
    ap.add_argument("--extrair", action="store_true", help="Consulta a BD de novo em vez de usar o último snapshot")
    ap.add_argument("--ano-inicio", type=int, default=2007)
    ap.add_argument("--ano-fim", type=int, default=2024)
    ap.add_argument("--billing-project", default=config.BILLING_PROJECT_ID)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        if not args.base_inep or not Path(args.base_inep).exists():
            raise ErroExtracao("Informe --base-inep com o base_atual.parquet do grupo.")
        ano_inicio, ano_fim = validar_anos(args.ano_inicio, args.ano_fim)
        bd, caminho_bd = carregar_bd(args.extrair, args.billing_project, ano_inicio, ano_fim)
    except (ErroExtracao, ValueError) as e:
        log.error("%s", e)
        return 1

    caminho_inep = Path(args.base_inep)
    inep = pd.read_parquet(caminho_inep)
    inep = inep[inep["ANO"].between(ano_inicio, ano_fim)].copy()
    inep["CO_ENTIDADE"] = inep["CO_ENTIDADE"].astype("string")
    inep["ANO"] = inep["ANO"].astype("Int64")
    bd["CO_ENTIDADE"], n_corrigidos = normalizar_id_escola(bd["id_escola"])
    bd["ANO"] = bd["ano"].astype("Int64")
    bd = bd.drop(columns=["id_escola", "ano"])

    tabela = comparar(inep, bd)
    anos_div = sorted(tabela.loc[tabela["n_diferentes"] > 0, "ano"].unique())
    desloc = pd.concat([localizar_deslocamento(inep, bd, a) for a in anos_div], ignore_index=True) \
        if anos_div else pd.DataFrame()

    DIR_SAIDA.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(DIR_SAIDA / "rendimento_por_ano_coluna.csv", index=False, encoding="utf-8")
    desloc.to_csv(DIR_SAIDA / "rendimento_deslocamento.csv", index=False, encoding="utf-8")
    meta = {
        "gerado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "snapshot_bd": caminho_bd.name, "sha256_snapshot_bd": sha256_arquivo(caminho_bd),
        "base_inep": caminho_inep.name, "sha256_base_inep": sha256_arquivo(caminho_inep),
        "anos": [ano_inicio, ano_fim], "tolerancia": TOLERANCIA,
        "id_escola_corrigidos_sufixo_ponto_zero": n_corrigidos,
    }
    (DIR_SAIDA / "rendimento_metadados.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    resumo = tabela.groupby("ano")[["n_ambos", "n_iguais", "n_diferentes", "n_so_inep", "n_so_bd"]].sum()
    print(resumo.to_string())
    if not desloc.empty:
        print("\nDeslocamento nos anos divergentes (posições na tabela da BD):")
        print(desloc.groupby("ano")["deslocamento_posicoes"].agg(["min", "max", "count"]).to_string())
    print(f"\nid_escola corrigidos (sufixo '.0'): {n_corrigidos}. Saídas em {DIR_SAIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
