import pandas as pd
import pytest
from google.api_core import exceptions as gexc

from src import config, extracao_bd as ex


@pytest.fixture(autouse=True)
def isolar(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DIR_CACHE", tmp_path / "cache")
    monkeypatch.setattr(config, "DIR_METADADOS", tmp_path / "meta")
    monkeypatch.setattr(config, "ARQ_SNAPSHOTS", tmp_path / "meta" / "snapshots.csv")
    monkeypatch.setattr(ex, "ESPERA_BASE_S", 0)


def _fake_bd(monkeypatch, respostas):
    """Instala um módulo basedosdados falso que devolve/levanta em sequência."""
    import sys, types
    m = types.ModuleType("basedosdados")
    chamadas = []

    def read_sql(sql, billing_project_id=None):
        chamadas.append(billing_project_id)
        r = respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    m.read_sql = read_sql
    monkeypatch.setitem(sys.modules, "basedosdados", m)
    return chamadas


def test_retry_em_erro_transitorio(monkeypatch):
    df = pd.DataFrame({"a": [1]})
    chamadas = _fake_bd(monkeypatch, [gexc.ServiceUnavailable("x"), df])
    assert ex.executar_sql("select 1", "abandonoescolar1").equals(df)
    assert chamadas == ["abandonoescolar1", "abandonoescolar1"]


def test_sem_retry_em_erro_permanente(monkeypatch):
    chamadas = _fake_bd(monkeypatch, [gexc.Forbidden("negado")])
    with pytest.raises(ex.ErroExtracao, match="403"):
        ex.executar_sql("select 1", "p")
    assert len(chamadas) == 1


def test_desiste_apos_tentativas(monkeypatch):
    _fake_bd(monkeypatch, [gexc.ServiceUnavailable("x")] * ex.TENTATIVAS)
    with pytest.raises(ex.ErroExtracao, match="desisti"):
        ex.executar_sql("select 1", "p")


def test_erro_embrulhado_e_classificado(monkeypatch):
    try:
        try:
            raise gexc.NotFound("sem tabela")
        except gexc.NotFound as e:
            raise RuntimeError("wrapper") from e
    except RuntimeError as exc:
        pode, msg = ex.classificar_erro(exc)
    assert not pode and "404" in msg


def test_etapa_zero_aprovada(monkeypatch):
    nomes = ["ano", "id_escola"] + ex.COLUNAS_SOMA
    colunas = pd.DataFrame({"column_name": nomes, "data_type": ["INT64"] * len(nomes)})
    contagem = pd.DataFrame({
        "ano": [2019, 2020], "n_linhas": [10, 10], "n_escolas": [10, 10],
        "n_duplicadas": [0, 0], "nn_taxa_abandono_em": [8, 9],
        "nn_taxa_abandono_ef_anos_finais": [5, 6],
        "soma_af": [100.0, 100.0], "soma_em": [100.0, 99.9],
    })
    _fake_bd(monkeypatch, [colunas, contagem])
    assert ex.etapa_zero("RR", 2019, 2020, "p", "csv") == 0
    assert len(list(config.DIR_CACHE.glob("check_tx_rend_*.csv"))) == 1
    assert config.ARQ_SNAPSHOTS.exists()


def test_etapa_zero_reprovada_sem_colunas(monkeypatch):
    colunas = pd.DataFrame({"column_name": ["ano", "id_municipio", "id_escola", "tdi_ef"],
                            "data_type": ["INT64"] * 4})
    _fake_bd(monkeypatch, [colunas])
    assert ex.etapa_zero("RR", 2019, 2020, "p", "csv") == 2


def test_gate_detecta_ano_ausente_e_nulos():
    df = pd.DataFrame({"ano": [2019], "n_linhas": [5], "n_escolas": [5],
                       "n_duplicadas": [0], "nn_taxa_abandono_em": [0],
                       "nn_taxa_abandono_ef_anos_finais": [3]})
    problemas = ex.avaliar_gate(df, ex.COLUNAS_ALVO, 2019, 2020)
    assert len(problemas) == 2  # ano 2020 ausente + abandono_em nulo em 2019


def test_gate_detecta_soma_inconsistente():
    df = pd.DataFrame({"ano": [2023], "n_linhas": [5], "n_escolas": [5], "n_duplicadas": [0],
                       "nn_taxa_abandono_em": [3], "nn_taxa_abandono_ef_anos_finais": [3],
                       "soma_af": [120.0], "soma_em": [100.0]})
    problemas = ex.avaliar_gate(df, ex.COLUNAS_ALVO, 2023, 2023)
    assert problemas == ["soma_af longe de 100% nos anos [2023]: colunas de rendimento inconsistentes"]
