"""Gráfico da série histórica de abandono (UF x Brasil) a partir da Base dos Dados.

Consulta sql/exploracao/01_abandono_por_ano.sql, salva o snapshot e gera um HTML
autocontido (sem dependências externas) em docs/figuras/.

Escolas em que aprovação + reprovação + abandono não fecha 100 (ou só parte das
três taxas existe) ficam fora da média. Se passarem de 1% das escolas do ano,
o ano é marcado como inconsistente e NÃO entra nas linhas (ver docs/COMO_FUNCIONA.md).

Uso:  python -m src.grafico_abandono --uf RR --ano-inicio 2007 --ano-fim 2024
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

import pandas as pd

from src import config
from src.consultas import (codigo_uf, formatar_tolerancia, renderizar, validar_anos, validar_dataset,
                           validar_identificador, validar_uf)
from src.extracao_bd import TOLERANCIA_SOMA, ErroExtracao, executar_sql
from src.snapshots import SnapshotDivergente, salvar_snapshot

log = logging.getLogger("grafico_abandono")
DIR_FIGURAS = config.RAIZ / "docs" / "figuras"
LIMITE_INCONSISTENTES = 0.01  # fração de escolas do ano; acima disso o ano sai do gráfico


def preparar(df: pd.DataFrame) -> list[dict]:
    """Uma linha por (recorte, ano), com valores nulos onde a fonte é inconsistente."""
    linhas = []
    for r in df.sort_values(["recorte", "ano"]).itertuples(index=False):
        reg = {"recorte": r.recorte, "ano": int(r.ano)}
        for etapa in ("af", "em"):
            n_ok, n_ruim = int(getattr(r, f"n_{etapa}")), int(getattr(r, f"n_inconsistente_{etapa}"))
            ok = n_ruim <= LIMITE_INCONSISTENTES * (n_ok + n_ruim)
            valor = getattr(r, f"abandono_{etapa}")
            reg[etapa] = float(valor) if ok and pd.notna(valor) else None
            reg[f"n_{etapa}"] = int(getattr(r, f"n_{etapa}"))
            reg[f"ok_{etapa}"] = bool(ok)
        linhas.append(reg)
    return linhas


def gerar_html(linhas: list[dict], uf: str, snapshot: str, ano_inicio: int, ano_fim: int) -> str:
    dados = {
        "uf": uf, "snapshot": snapshot, "anoInicio": ano_inicio, "anoFim": ano_fim,
        "gerado": datetime.now(timezone.utc).strftime("%d/%m/%Y"), "linhas": linhas,
    }
    return _MODELO_HTML.replace("__DADOS__", json.dumps(dados, ensure_ascii=False)).replace("__UF__", uf)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Gráfico de abandono escolar (Base dos Dados).")
    ap.add_argument("--uf", default=config.UF_PADRAO)
    ap.add_argument("--ano-inicio", type=int, default=2007)
    ap.add_argument("--ano-fim", type=int, default=2025)
    ap.add_argument("--billing-project", default=config.BILLING_PROJECT_ID)
    ap.add_argument("--aceitar-divergencia", action="store_true",
                    help="Adota o resultado novo quando difere do snapshot anterior da mesma consulta")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        uf = validar_uf(args.uf)
        ano_inicio, ano_fim = validar_anos(args.ano_inicio, args.ano_fim)
        sql = renderizar(
            "exploracao/01_abandono_por_ano.sql",
            dataset=validar_dataset(config.DATASET_INDICADORES),
            tabela=validar_identificador(config.TABELA_ESCOLA),
            uf=uf, uf_codigo=codigo_uf(uf), ano_inicio=ano_inicio, ano_fim=ano_fim,
            tolerancia=formatar_tolerancia(TOLERANCIA_SOMA),
        )
        df = executar_sql(sql, args.billing_project)
    except (ErroExtracao, ValueError) as e:
        log.error("%s", e)
        return 1
    if df.empty:
        log.error("Consulta não devolveu linhas.")
        return 1
    try:
        caminho = salvar_snapshot(df, "abandono_por_ano", sql, "parquet", args.aceitar_divergencia)
    except SnapshotDivergente as e:
        log.error("%s", e)
        return e.codigo_saida
    linhas = preparar(df)
    inconsistentes = sorted({l["ano"] for l in linhas if not (l["ok_af"] and l["ok_em"])})
    if inconsistentes:
        log.warning("Anos com rendimento inconsistente (fora do gráfico): %s", inconsistentes)
    DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    saida = DIR_FIGURAS / f"abandono_{uf.lower()}.html"
    saida.write_text(gerar_html(linhas, uf, caminho.stem, ano_inicio, ano_fim), encoding="utf-8")
    log.info("Gráfico salvo em %s", saida)
    return 0


_MODELO_HTML = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Abandono escolar __UF__</title>
<style>
:root {
  color-scheme: light;
  --surface: #fcfcfb; --surface-2: #f3f2ef; --text: #0b0b0b; --text-2: #52514e; --muted: #7a7974;
  --grid: #e4e3df; --axis: #b9b8b2; --hatch: #c9c8c2;
  --s1: #2a78d6; --s2: #eb6834;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --surface: #1a1a19; --surface-2: #242422; --text: #f0efec; --text-2: #c3c2b7; --muted: #8f8e88;
    --grid: #33332f; --axis: #55544f; --hatch: #4a4945;
    --s1: #3987e5; --s2: #d95926;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface: #1a1a19; --surface-2: #242422; --text: #f0efec; --text-2: #c3c2b7; --muted: #8f8e88;
  --grid: #33332f; --axis: #55544f; --hatch: #4a4945;
  --s1: #3987e5; --s2: #d95926;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface); color: var(--text);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 16px 40px; }
h1 { font-size: 20px; margin: 0 0 4px; font-weight: 650; }
.sub { color: var(--text-2); margin: 0 0 16px; max-width: 75ch; }
.legenda { display: flex; gap: 18px; flex-wrap: wrap; margin: 0 0 8px; color: var(--text-2); font-size: 13px; }
.legenda span { display: inline-flex; align-items: center; gap: 6px; }
.legenda i { width: 16px; height: 2px; border-radius: 1px; display: inline-block; }
.legenda .hach { width: 14px; height: 12px; border: 1px solid var(--hatch);
  background: repeating-linear-gradient(45deg, var(--hatch) 0 1.5px, transparent 1.5px 5px); }
.paineis { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 24px; }
.painel h2 { font-size: 15px; margin: 0 0 6px; font-weight: 600; }
.painel svg { width: 100%; height: auto; display: block; overflow: visible; }
.tick { fill: var(--muted); font-size: 11px; }
.rotulo { font-size: 12px; font-weight: 600; fill: var(--text); }
.nota-area { fill: var(--muted); font-size: 10.5px; }
#dica { position: fixed; pointer-events: none; background: var(--surface-2); color: var(--text);
  border: 1px solid var(--grid); border-radius: 8px; padding: 8px 10px; font-size: 12px;
  box-shadow: 0 4px 14px rgba(0,0,0,.12); display: none; min-width: 170px; z-index: 5; }
#dica b { display: block; margin-bottom: 4px; }
#dica .l { display: flex; justify-content: space-between; gap: 12px; }
#dica .sw { display: inline-block; width: 10px; height: 2px; margin-right: 6px; vertical-align: middle; }
.notas { color: var(--text-2); font-size: 12.5px; margin-top: 20px; max-width: 85ch; }
.notas li { margin-bottom: 4px; }
details { margin-top: 16px; }
summary { cursor: pointer; color: var(--text-2); }
table { border-collapse: collapse; margin-top: 8px; font-size: 12.5px; font-variant-numeric: tabular-nums; }
th, td { padding: 4px 10px; text-align: right; border-bottom: 1px solid var(--grid); }
th:first-child, td:first-child { text-align: left; }
.na { color: var(--muted); }
</style>
</head>
<body>
<main>
  <h1>Taxa de abandono escolar nas escolas públicas — __UF__ e Brasil</h1>
  <p class="sub" id="sub"></p>
  <div class="legenda" id="legenda"></div>
  <div class="paineis" id="paineis"></div>
  <ul class="notas" id="notas"></ul>
  <details><summary>Ver tabela de dados</summary><div id="tabela"></div></details>
</main>
<div id="dica" role="tooltip"></div>
<script>
const D = __DADOS__;
const SERIES = [
  { recorte: D.uf, nome: D.uf === "RR" ? "Roraima" : D.uf, cor: "var(--s1)" },
  { recorte: "BR", nome: "Brasil", cor: "var(--s2)" },
];
const ETAPAS = [
  { chave: "af", titulo: "Anos finais do fundamental (6º ao 9º)" },
  { chave: "em", titulo: "Ensino médio" },
];
const fmt = v => v == null ? "—" : v.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
const anos = []; for (let a = D.anoInicio; a <= D.anoFim; a++) anos.push(a);
const porChave = {}; D.linhas.forEach(l => porChave[l.recorte + "|" + l.ano] = l);
const anosComLinha = new Set(D.linhas.map(l => l.ano));
const inconsist = new Set(D.linhas.filter(l => !(l.ok_af && l.ok_em)).map(l => l.ano));
const semDado = anos.filter(a => !anosComLinha.has(a));

document.getElementById("sub").textContent =
  `Média simples da taxa de abandono entre as escolas públicas (estaduais, municipais e federais), ` +
  `por ano. Fonte: Base dos Dados, tabela br_inep_indicadores_educacionais.escola (dados do INEP).`;
document.getElementById("legenda").innerHTML =
  SERIES.map(s => `<span><i style="background:${s.cor}"></i>${s.nome}</span>`).join("") +
  `<span><i class="hach"></i>Sem dado utilizável</span>`;

const maxV = Math.max(...D.linhas.flatMap(l => [l.af, l.em]).filter(v => v != null));
const yMax = Math.ceil(maxV / 2) * 2 + 2;
const dica = document.getElementById("dica");

ETAPAS.forEach(et => {
  const W = 520, H = 300, m = { t: 14, r: 64, b: 30, l: 36 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const x = a => m.l + (a - D.anoInicio) / (D.anoFim - D.anoInicio) * iw;
  const y = v => m.t + ih - v / yMax * ih;
  const passo = iw / (D.anoFim - D.anoInicio);
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${et.titulo}: taxa de abandono por ano">`;
  s += `<defs><pattern id="h-${et.chave}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="6" stroke="var(--hatch)" stroke-width="1.5"/></pattern></defs>`;
  // Faixas de anos sem dado utilizável (inconsistentes ou não publicados)
  const faltando = anos.filter(a => inconsist.has(a) || !anosComLinha.has(a));
  const grupos = []; faltando.forEach(a => { const g = grupos[grupos.length - 1];
    if (g && a === g[1] + 1) g[1] = a; else grupos.push([a, a]); });
  grupos.forEach(([a0, a1]) => {
    const x0 = Math.max(m.l, x(a0) - passo / 2), x1 = Math.min(m.l + iw, x(a1) + passo / 2);
    s += `<rect x="${x0}" y="${m.t}" width="${x1 - x0}" height="${ih}" fill="url(#h-${et.chave})" opacity=".7"/>`;
  });
  for (let v = 0; v <= yMax; v += 2) {
    s += `<line x1="${m.l}" x2="${m.l + iw}" y1="${y(v)}" y2="${y(v)}" stroke="var(--grid)" stroke-width="1"/>`;
    s += `<text class="tick" x="${m.l - 6}" y="${y(v) + 4}" text-anchor="end">${v}%</text>`;
  }
  s += `<line x1="${m.l}" x2="${m.l + iw}" y1="${y(0)}" y2="${y(0)}" stroke="var(--axis)"/>`;
  anos.forEach(a => { if ((a - D.anoInicio) % 3 === 0 || a === D.anoFim)
    s += `<text class="tick" x="${x(a)}" y="${H - 10}" text-anchor="middle">${a}</text>`; });
  // Linhas: quebram onde não há dado (não ligam por cima de anos inconsistentes)
  const rotulos = [];
  SERIES.forEach(se => {
    let d = "", aberto = false, ultimo = null;
    anos.forEach(a => { const l = porChave[se.recorte + "|" + a]; const v = l ? l[et.chave] : null;
      if (v == null) { aberto = false; return; }
      d += (aberto ? "L" : "M") + x(a).toFixed(1) + " " + y(v).toFixed(1); aberto = true; ultimo = [a, v]; });
    s += `<path d="${d}" fill="none" stroke="${se.cor}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
    if (ultimo) { s += `<circle cx="${x(ultimo[0])}" cy="${y(ultimo[1])}" r="4" fill="${se.cor}" stroke="var(--surface)" stroke-width="2"/>`;
      rotulos.push({ ano: ultimo[0], v: ultimo[1], yy: y(ultimo[1]), nome: se.nome }); }
  });
  rotulos.sort((a, b) => a.yy - b.yy);
  for (let i = 1; i < rotulos.length; i++) if (rotulos[i].yy - rotulos[i - 1].yy < 28) rotulos[i].yy = rotulos[i - 1].yy + 28;
  rotulos.forEach(r => {
    s += `<text class="rotulo" x="${x(r.ano) + 8}" y="${r.yy - 2}">${r.nome}</text>`;
    s += `<text class="tick" x="${x(r.ano) + 8}" y="${r.yy + 11}">${fmt(r.v)} (${r.ano})</text>`;
  });
  grupos.forEach(([a0, a1]) => {
    const faixa = anos.filter(a => a >= a0 && a <= a1), nSem = faixa.filter(a => semDado.includes(a)).length;
    const motivo = nSem === faixa.length ? "sem dado" : nSem === 0 ? "inconsistente" : "sem dado utilizável";
    s += `<text class="nota-area" x="${(Math.max(m.l, x(a0) - passo / 2) + Math.min(m.l + iw, x(a1) + passo / 2)) / 2}" y="${m.t + 12}" text-anchor="middle">${motivo}</text>`;
  });
  s += `<line id="cruz-${et.chave}" y1="${m.t}" y2="${m.t + ih}" stroke="var(--axis)" stroke-dasharray="3 3" visibility="hidden"/>`;
  s += `<rect x="${m.l - passo / 2}" y="${m.t}" width="${iw + passo}" height="${ih}" fill="transparent" class="alvo"/>`;
  s += `</svg>`;
  const div = document.createElement("section"); div.className = "painel";
  div.innerHTML = `<h2>${et.titulo}</h2>` + s;
  document.getElementById("paineis").appendChild(div);

  const svg = div.querySelector("svg"), cruz = div.querySelector(`#cruz-${et.chave}`);
  const mover = ev => {
    const pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse());
    const a = Math.round(D.anoInicio + (p.x - m.l) / passo);
    if (a < D.anoInicio || a > D.anoFim) return sair();
    cruz.setAttribute("x1", x(a)); cruz.setAttribute("x2", x(a)); cruz.setAttribute("visibility", "visible");
    let h = `<b>${a} · ${et.chave === "af" ? "Anos finais" : "Ensino médio"}</b>`;
    SERIES.forEach(se => { const l = porChave[se.recorte + "|" + a];
      const txt = !l ? "sem dado" : l["ok_" + et.chave] ? fmt(l[et.chave]) : "inconsistente";
      h += `<div class="l"><span><span class="sw" style="background:${se.cor}"></span>${se.nome}</span><span>${txt}</span></div>`; });
    const l = porChave[D.uf + "|" + a];
    if (l) h += `<div class="l" style="color:var(--muted)"><span>escolas em ${D.uf}</span><span>${l["n_" + et.chave]}</span></div>`;
    dica.innerHTML = h; dica.style.display = "block";
    const r = dica.getBoundingClientRect();
    dica.style.left = Math.min(ev.clientX + 14, innerWidth - r.width - 8) + "px";
    dica.style.top = Math.max(8, ev.clientY - r.height - 12) + "px";
  };
  const sair = () => { dica.style.display = "none"; cruz.setAttribute("visibility", "hidden"); };
  const alvo = div.querySelector(".alvo");
  alvo.addEventListener("pointermove", mover); alvo.addEventListener("pointerleave", sair);
});

const notas = [];
if (inconsist.size) notas.push(`<b>${[...inconsist].sort().join(" e ")}:</b> fora das linhas. Na tabela por escola da Base dos Dados, as colunas desses anos estão deslocadas (docs/conferencia/RESULTADO_FASE_3_1.md), em todo o Brasil. O número não é confiável até a BD corrigir.`);
if (semDado.length) notas.push(`<b>${semDado.join(", ")}:</b> ainda não publicado na tabela por escola da Base dos Dados.`);
notas.push(`Escolas em que aprovação + reprovação + abandono não fecha 100% ficam fora da média; o ano sai do gráfico quando passam de 1% das escolas.`);
notas.push(`A média simples entre escolas difere da taxa oficial do INEP, que pondera pelo número de alunos. Use para ver a tendência, não para citar a taxa oficial.`);
notas.push(`Snapshot: <code>${D.snapshot}</code> · gerado em ${D.gerado}.`);
document.getElementById("notas").innerHTML = notas.map(n => `<li>${n}</li>`).join("");

let t = `<table><thead><tr><th>Ano</th>` + SERIES.flatMap(se => ETAPAS.map(et =>
  `<th>${se.nome} · ${et.chave === "af" ? "AF" : "EM"}</th>`)).join("") + `</tr></thead><tbody>`;
anos.forEach(a => { t += `<tr><td>${a}</td>` + SERIES.flatMap(se => ETAPAS.map(et => {
  const l = porChave[se.recorte + "|" + a];
  if (!l) return `<td class="na">sem dado</td>`;
  return l["ok_" + et.chave] ? `<td>${fmt(l[et.chave])}</td>` : `<td class="na">inconsistente</td>`;
})).join("") + `</tr>`; });
document.getElementById("tabela").innerHTML = t + `</tbody></table>`;
</script>
</body>
</html>
"""

if __name__ == "__main__":
    sys.exit(main())
