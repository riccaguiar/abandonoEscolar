import pytest

from src import consultas as c


def test_validar_uf():
    assert c.validar_uf("rr") == "RR"
    with pytest.raises(ValueError):
        c.validar_uf("RR'; DROP TABLE x;--")


def test_validar_anos():
    assert c.validar_anos("2019", 2025) == (2019, 2025)
    with pytest.raises(ValueError):
        c.validar_anos(2025, 2019)


def test_identificador_rejeita_injecao():
    assert c.validar_identificador("taxa_abandono_em") == "taxa_abandono_em"
    for ruim in ["a b", "x; DROP", "1abc", "A", "a`b"]:
        with pytest.raises(ValueError):
            c.validar_identificador(ruim)


def test_renderizar_verificacao():
    sql = c.renderizar(
        "verificacao/01_presenca_tx_rend.sql",
        dataset="basedosdados.br_inep_indicadores_educacionais",
        tabela="escola", uf_codigo=c.codigo_uf("RR"), ano_inicio=2019, ano_fim=2025,
        tolerancia=c.formatar_tolerancia(1e-6),
        contagens_nao_nulos=c.montar_contagens_nao_nulos(["taxa_abandono_em"]),
    )
    assert "{{" not in sql.replace("{{contagens_nao_nulos}}", "")
    assert "STARTS_WITH(CAST(id_escola AS STRING), '14')" in sql
    assert "COUNTIF(taxa_abandono_em IS NOT NULL) AS nn_taxa_abandono_em" in sql
    assert "> 0.000001000000) AS n_soma_fora_em" in sql


def test_formatar_tolerancia():
    assert c.formatar_tolerancia(1e-6) == "0.000001000000"
    for ruim in (0, 1, -1e-6, "x"):
        with pytest.raises(ValueError):
            c.formatar_tolerancia(ruim)


def test_renderizar_param_faltando_ou_sobrando():
    with pytest.raises(ValueError):
        c.renderizar("verificacao/00_colunas_indicadores_escola.sql", dataset="a.b")
    with pytest.raises(ValueError):
        c.renderizar("verificacao/00_colunas_indicadores_escola.sql",
                     dataset="a.b", tabela="t", extra="x")


def test_placeholder_em_comentario_e_rejeitado(tmp_path, monkeypatch):
    (tmp_path / "x.sql").write_text("-- usa {{a}}\nSELECT {{a}}", encoding="utf-8")
    monkeypatch.setattr(c, "DIR_SQL", tmp_path)
    with pytest.raises(ValueError, match="comentário"):
        c.renderizar("x.sql", a="1")
