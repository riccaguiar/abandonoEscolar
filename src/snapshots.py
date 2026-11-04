"""Snapshots das consultas: gravação, registro e detecção de divergência.

O hash da consulta prova o que foi pedido; o hash do resultado prova o que
voltou. A nuvem pode devolver dados diferentes para a mesma consulta, e é isso
que este módulo detecta (02_DADOS.md, §13):

- mesma consulta, mesmo resultado  -> não grava de novo; reaproveita o snapshot;
- mesma consulta, resultado novo   -> grava em dados/cache/divergente/, registra
  com status "divergente" e levanta SnapshotDivergente (código de saída 3);
- consulta nova                    -> grava normalmente.

Registro: dados/metadados/snapshots.csv (versionado). Nunca grava credencial nem
o ID do projeto de faturamento.

Uso direto (manutenção):
  python -m src.snapshots --deduplicar   remove snapshots repetidos (mesma consulta e resultado)
"""

import argparse
import csv
import hashlib
import logging
import shutil
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

import pandas as pd

from src import config

log = logging.getLogger("snapshots")

CAMPOS = ["snapshot_id", "consulta", "sha256_consulta", "data_extracao_utc", "n_linhas",
          "n_colunas", "versao_basedosdados", "arquivo", "sha256_resultado", "sha256_arquivo", "status"]
CODIGO_SAIDA_DIVERGENTE = 3


class SnapshotDivergente(Exception):
    """A mesma consulta devolveu um resultado diferente do snapshot anterior."""

    codigo_saida = CODIGO_SAIDA_DIVERGENTE


def sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def ler_snapshot(caminho: Path) -> pd.DataFrame:
    return pd.read_parquet(caminho) if caminho.suffix == ".parquet" else pd.read_csv(caminho)


def sha256_resultado(caminho: Path) -> str:
    """Hash do conteúdo (não dos bytes do arquivo), lido de volta do disco.

    Ler de volta faz o hash depender só do que está gravado, e não de metadados
    do Parquet que mudam entre versões de biblioteca.
    """
    df = ler_snapshot(caminho)
    texto = df.to_csv(index=False, lineterminator="\n", float_format="%.17g")
    return sha256_bytes(f"{list(df.columns)}\n{texto}".encode("utf-8"))


# --------------------------------------------------------------------------
# Registro
# --------------------------------------------------------------------------
def ler_registro() -> list[dict]:
    """Lê o registro e migra linhas antigas (sem hash do resultado) na leitura."""
    if not config.ARQ_SNAPSHOTS.exists():
        return []
    with open(config.ARQ_SNAPSHOTS, newline="", encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for linha in linhas:
        for campo in CAMPOS:
            linha.setdefault(campo, "")
            if linha[campo] is None:
                linha[campo] = ""
        caminho = _caminho_do_registro(linha)
        if not linha["sha256_resultado"] and caminho.exists():
            linha["sha256_resultado"] = sha256_resultado(caminho)
            linha["sha256_arquivo"] = sha256_arquivo(caminho)
        linha["status"] = linha["status"] or "ok"
    return linhas


def gravar_registro(linhas: list[dict]) -> None:
    config.DIR_METADADOS.mkdir(parents=True, exist_ok=True)
    temporario = config.ARQ_SNAPSHOTS.with_suffix(".tmp")
    with open(temporario, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)
    temporario.replace(config.ARQ_SNAPSHOTS)


def _caminho_do_registro(linha: dict) -> Path:
    pasta = config.DIR_CACHE / "divergente" if linha.get("status") == "divergente" else config.DIR_CACHE
    return pasta / linha["arquivo"]


# --------------------------------------------------------------------------
# Gravação
# --------------------------------------------------------------------------
def salvar_snapshot(df: pd.DataFrame, nome: str, sql: str, formato: str = "parquet",
                    aceitar_divergencia: bool = False) -> Path:
    """Grava o resultado da consulta, ou reaproveita o snapshot igual.

    Levanta SnapshotDivergente se a mesma consulta já tem snapshot com resultado
    diferente (a menos que aceitar_divergencia=True, que registra o novo como ok).
    """
    if formato not in ("parquet", "csv"):
        raise ValueError(f"Formato inválido: {formato!r}")
    agora = datetime.now(timezone.utc)
    snapshot_id = f"{nome}_{agora:%Y%m%dT%H%M%SZ}"
    sha_consulta = sha256_bytes(sql.encode("utf-8"))

    config.DIR_CACHE.mkdir(parents=True, exist_ok=True)
    temporario = config.DIR_CACHE / f".{snapshot_id}.tmp.{formato}"
    if formato == "parquet":
        df.to_parquet(temporario, index=False)
    else:
        df.to_csv(temporario, index=False, encoding="utf-8")
    sha_res = sha256_resultado(temporario)

    registro = ler_registro()
    anteriores = [l for l in registro if l["consulta"] == nome and l["sha256_consulta"] == sha_consulta
                  and l["status"] == "ok" and _caminho_do_registro(l).exists()]
    anterior = anteriores[-1] if anteriores else None

    if anterior and anterior["sha256_resultado"] == sha_res:
        temporario.unlink()
        caminho = _caminho_do_registro(anterior)
        log.info("Resultado idêntico ao snapshot %s; nada gravado.", anterior["snapshot_id"])
        gravar_registro(registro)  # persiste a migração das linhas antigas, se houver
        return caminho

    divergente = anterior is not None and not aceitar_divergencia
    pasta = config.DIR_CACHE / "divergente" if divergente else config.DIR_CACHE
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{snapshot_id}.{formato}"
    shutil.move(temporario, caminho)

    try:
        versao = metadata.version("basedosdados")
    except metadata.PackageNotFoundError:
        versao = "desconhecida"
    registro.append({
        "snapshot_id": snapshot_id, "consulta": nome, "sha256_consulta": sha_consulta,
        "data_extracao_utc": agora.isoformat(timespec="seconds"), "n_linhas": len(df),
        "n_colunas": df.shape[1], "versao_basedosdados": versao, "arquivo": caminho.name,
        "sha256_resultado": sha_res, "sha256_arquivo": sha256_arquivo(caminho),
        "status": "divergente" if divergente else "ok",
    })
    gravar_registro(registro)

    if divergente:
        raise SnapshotDivergente(
            f"A consulta '{nome}' devolveu um resultado diferente do snapshot "
            f"{anterior['snapshot_id']}. O novo foi gravado em {caminho} e NÃO substitui o "
            "anterior. Compare os dois; para adotar o novo, rode de novo com --aceitar-divergencia."
        )
    return caminho


def ultimo_snapshot(nome: str) -> Path | None:
    """Caminho do snapshot válido mais recente de uma consulta."""
    validos = [l for l in ler_registro() if l["consulta"] == nome and l["status"] == "ok"
               and _caminho_do_registro(l).exists()]
    return _caminho_do_registro(validos[-1]) if validos else None


def deduplicar() -> int:
    """Remove snapshots repetidos (mesma consulta e mesmo resultado), mantendo o mais antigo."""
    registro = ler_registro()
    vistos, manter, removidos = set(), [], 0
    for linha in registro:
        chave = (linha["consulta"], linha["sha256_consulta"], linha["sha256_resultado"], linha["status"])
        caminho = _caminho_do_registro(linha)
        if linha["sha256_resultado"] and chave in vistos:
            if caminho.exists():
                caminho.unlink()
            removidos += 1
            log.info("Removido snapshot repetido %s", linha["snapshot_id"])
            continue
        vistos.add(chave)
        manter.append(linha)
    gravar_registro(manter)
    return removidos


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Manutenção dos snapshots.")
    ap.add_argument("--deduplicar", action="store_true", help="Remove snapshots repetidos")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.deduplicar:
        print(f"Snapshots repetidos removidos: {deduplicar()}")
    else:
        gravar_registro(ler_registro())
        print("Registro migrado para o formato atual.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
