"""Renderização segura de consultas SQL.

Regra do projeto (02_DADOS.md, §11): nenhum valor externo entra no SQL sem
validação. Os arquivos .sql usam placeholders {{nome}}; este módulo valida
cada valor e só então faz a substituição. Não usar f-string com entrada livre.
"""

import re
from pathlib import Path

from src.config import DIR_SQL

# Código IBGE da UF = 2 primeiros dígitos do código INEP da escola (id_escola).
# A tabela de indicadores por escola não tem sigla_uf, então o filtro usa esse prefixo.
CODIGO_IBGE_UF = {
    "AC": "12", "AL": "27", "AP": "16", "AM": "13", "BA": "29", "CE": "23",
    "DF": "53", "ES": "32", "GO": "52", "MA": "21", "MT": "51", "MS": "50",
    "MG": "31", "PA": "15", "PB": "25", "PR": "41", "PE": "26", "PI": "22",
    "RJ": "33", "RN": "24", "RS": "43", "RO": "11", "RR": "14", "SC": "42",
    "SP": "35", "SE": "28", "TO": "17",
}
UFS_VALIDAS = frozenset(CODIGO_IBGE_UF)
_RE_IDENTIFICADOR = re.compile(r"^[a-z][a-z0-9_]*$")
_RE_DATASET = re.compile(r"^[a-z][a-z0-9_-]*\.[a-z][a-z0-9_]*$")
_RE_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def validar_uf(uf: str) -> str:
    uf = str(uf).strip().upper()
    if uf not in UFS_VALIDAS:
        raise ValueError(f"UF inválida: {uf!r}")
    return uf


def codigo_uf(uf: str) -> str:
    """Código IBGE de 2 dígitos da UF (validada)."""
    return CODIGO_IBGE_UF[validar_uf(uf)]


def validar_anos(ano_inicio: int, ano_fim: int) -> tuple[int, int]:
    ano_inicio, ano_fim = int(ano_inicio), int(ano_fim)
    if not (2000 <= ano_inicio <= ano_fim <= 2100):
        raise ValueError(f"Intervalo de anos inválido: {ano_inicio}-{ano_fim}")
    return ano_inicio, ano_fim


def validar_identificador(nome: str) -> str:
    """Nome de tabela/coluna: minúsculas, dígitos e '_' (vem do INFORMATION_SCHEMA)."""
    if not _RE_IDENTIFICADOR.match(str(nome)):
        raise ValueError(f"Identificador SQL inválido: {nome!r}")
    return nome


def validar_dataset(dataset: str) -> str:
    """Formato projeto.dataset, ex.: basedosdados.br_inep_indicadores_educacionais."""
    if not _RE_DATASET.match(str(dataset)):
        raise ValueError(f"Dataset inválido: {dataset!r}")
    return dataset


def formatar_tolerancia(tol: float) -> str:
    """Literal decimal para SQL (sem notação científica), só para 0 < tol < 1."""
    tol = float(tol)
    if not 0 < tol < 1:
        raise ValueError(f"Tolerância inválida: {tol!r}")
    return f"{tol:.12f}"


def montar_contagens_nao_nulos(colunas: list[str]) -> str:
    """Uma expressão COUNTIF(col IS NOT NULL) AS nn_col por coluna."""
    if not colunas:
        raise ValueError("Nenhuma coluna para contar.")
    return ",\n  ".join(
        f"COUNTIF({validar_identificador(c)} IS NOT NULL) AS nn_{c}" for c in colunas
    )


def renderizar(arquivo: str, **params: str) -> str:
    """Lê sql/<arquivo> e substitui os placeholders {{chave}}.

    Os valores devem ter sido validados por quem chama (use os validar_*).
    Levanta erro se sobrar placeholder sem valor ou se um valor não for usado
    por nenhum placeholder (indica erro de digitação).
    """
    caminho = Path(DIR_SQL) / arquivo
    texto = caminho.read_text(encoding="utf-8")
    # Placeholder em comentário seria preenchido e poderia "vazar" para fora dele
    # (um valor com várias linhas sai do comentário e vira SQL).
    for n, linha in enumerate(texto.splitlines(), 1):
        if linha.lstrip().startswith("--") and _RE_PLACEHOLDER.search(linha):
            raise ValueError(f"{arquivo}:{n}: placeholder dentro de comentário")
    usados = set(_RE_PLACEHOLDER.findall(texto))
    faltando = usados - params.keys()
    if faltando:
        raise ValueError(f"{arquivo}: faltam parâmetros {sorted(faltando)}")
    sobrando = params.keys() - usados
    if sobrando:
        raise ValueError(f"{arquivo}: parâmetros não usados {sorted(sobrando)}")
    return _RE_PLACEHOLDER.sub(lambda m: str(params[m.group(1)]), texto)
