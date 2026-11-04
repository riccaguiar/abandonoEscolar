import pandas as pd
import pytest

from src import conferencia_rendimento as cr


def _inep(ano, escolas, valores):
    df = pd.DataFrame({"ANO": pd.array([ano] * len(escolas), dtype="Int64"),
                       "CO_ENTIDADE": pd.array(escolas, dtype="string")})
    for col in cr.MAPA_RENDIMENTO:
        df[col] = pd.array(valores, dtype="Float64")
    return df


def _bd(ano, escolas, valores, extra=None):
    df = pd.DataFrame({"ANO": pd.array([ano] * len(escolas), dtype="Int64"),
                       "CO_ENTIDADE": pd.array(escolas, dtype="string")})
    for col in cr.MAPA_RENDIMENTO.values():
        df[col] = pd.Series(valores, dtype="float64")
    for nome, v in (extra or {}).items():
        df[nome] = pd.Series(v, dtype="float64")
    return df


def test_normaliza_sufixo_ponto_zero():
    s, n = cr.normalizar_id_escola(pd.Series(["14000016.0", "14000032"]))
    assert s.tolist() == ["14000016", "14000032"] and n == 1
    with pytest.raises(ValueError):
        cr.normalizar_id_escola(pd.Series(["1400"]))


def test_comparar_conta_iguais_e_presenca():
    inep = _inep(2020, ["14000016", "14000032"], [1.5, None])
    bd = _bd(2020, ["14000016", "14000032"], [1.5, 2.0])
    t = cr.comparar(inep, bd)
    linha = t[t.coluna_inep == "ABANDONO_MED"].iloc[0]
    assert (linha.n_ambos, linha.n_iguais, linha.n_diferentes, linha.n_so_bd) == (1, 1, 0, 1)


def test_comparar_rejeita_chave_duplicada():
    inep = _inep(2020, ["14000016", "14000016"], [1.0, 1.0])
    with pytest.raises(pd.errors.MergeError):
        cr.comparar(inep, _bd(2020, ["14000016"], [1.0]))


def test_localiza_coluna_deslocada():
    # Na BD, o valor certo do abandono do EM está numa coluna 2 posições adiante.
    inep = _inep(2023, ["14000016", "14000032"], [3.0, 7.0])
    bd = _bd(2023, ["14000016", "14000032"], [9.0, 9.0])
    bd["outra_a"] = [0.1, 0.2]
    bd["ied_x"] = [3.0, 7.0]
    d = cr.localizar_deslocamento(inep, bd, 2023)
    linha = d[d.coluna_inep == "ABANDONO_MED"].iloc[0]
    assert linha.coluna_bd_encontrada == "ied_x"
    assert linha.deslocamento_posicoes == list(bd.columns).index("ied_x") - list(bd.columns).index("taxa_abandono_em")
