import pandas as pd
import pytest

from src import config, snapshots as sn


@pytest.fixture(autouse=True)
def isolar(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DIR_CACHE", tmp_path / "cache")
    monkeypatch.setattr(config, "DIR_METADADOS", tmp_path / "meta")
    monkeypatch.setattr(config, "ARQ_SNAPSHOTS", tmp_path / "meta" / "snapshots.csv")


def _arquivos():
    return sorted(p.name for p in config.DIR_CACHE.rglob("*.parquet"))


def test_mesmo_resultado_nao_grava_de_novo():
    df = pd.DataFrame({"ano": [2020], "x": [1.5]})
    p1 = sn.salvar_snapshot(df, "q", "SELECT 1")
    p2 = sn.salvar_snapshot(df.copy(), "q", "SELECT 1")
    assert p1 == p2 and len(_arquivos()) == 1 and len(sn.ler_registro()) == 1


def test_resultado_diferente_vai_para_divergente():
    sn.salvar_snapshot(pd.DataFrame({"x": [1.0]}), "q", "SELECT 1")
    with pytest.raises(sn.SnapshotDivergente):
        sn.salvar_snapshot(pd.DataFrame({"x": [2.0]}), "q", "SELECT 1")
    registro = sn.ler_registro()
    assert [l["status"] for l in registro] == ["ok", "divergente"]
    assert len(list((config.DIR_CACHE / "divergente").glob("*.parquet"))) == 1
    # o snapshot válido continua sendo o primeiro
    assert pd.read_parquet(sn.ultimo_snapshot("q"))["x"].tolist() == [1.0]


def test_aceitar_divergencia_adota_o_novo():
    sn.salvar_snapshot(pd.DataFrame({"x": [1.0]}), "q", "SELECT 1")
    sn.salvar_snapshot(pd.DataFrame({"x": [2.0]}), "q", "SELECT 1", aceitar_divergencia=True)
    assert pd.read_parquet(sn.ultimo_snapshot("q"))["x"].tolist() == [2.0]


def test_consulta_diferente_nao_e_divergencia():
    sn.salvar_snapshot(pd.DataFrame({"x": [1.0]}), "q", "SELECT 1")
    sn.salvar_snapshot(pd.DataFrame({"x": [2.0]}), "q", "SELECT 2")
    assert [l["status"] for l in sn.ler_registro()] == ["ok", "ok"]


def test_registro_registra_hashes_e_nao_credencial():
    sn.salvar_snapshot(pd.DataFrame({"x": [1.0]}), "q", "SELECT 1")
    linha = sn.ler_registro()[0]
    assert len(linha["sha256_resultado"]) == 64 and len(linha["sha256_arquivo"]) == 64
    assert "abandonoescolar1" not in config.ARQ_SNAPSHOTS.read_text(encoding="utf-8")


def test_migra_registro_antigo_e_deduplica():
    config.DIR_CACHE.mkdir(parents=True)
    config.DIR_METADADOS.mkdir(parents=True)
    df = pd.DataFrame({"x": [1.0]})
    df.to_parquet(config.DIR_CACHE / "q_1.parquet", index=False)
    df.to_parquet(config.DIR_CACHE / "q_2.parquet", index=False)
    config.ARQ_SNAPSHOTS.write_text(
        "snapshot_id,consulta,sha256_consulta,data_extracao_utc,n_linhas,n_colunas,versao_basedosdados,arquivo\n"
        "q_1,q,abc,2026-11-03T00:00:00+00:00,1,1,2.0.3,q_1.parquet\n"
        "q_2,q,abc,2026-11-03T00:01:00+00:00,1,1,2.0.3,q_2.parquet\n", encoding="utf-8")
    assert sn.deduplicar() == 1
    assert _arquivos() == ["q_1.parquet"]
    registro = sn.ler_registro()
    assert [l["snapshot_id"] for l in registro] == ["q_1"] and registro[0]["status"] == "ok"
