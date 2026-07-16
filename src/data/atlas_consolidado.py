#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pipeline do Y (Atlas consolidado) — versao BD_Atlas_1991_2025_v1.xlsx.

Reaproveita a bridge estacao->IBGE existente (NAO recria).
Data do evento = Data_Evento (decisao da dupla, 2026-07-15).
Descarta linhas com Data_Registro em 2026 (registro futuro ao evento).

Saidas:
  data/processed/y_eventos_sudeste.csv
  data/processed/y_eventos_estacoes.csv
  reports/relatorio_validacao_atlas.txt
"""
import io
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "data/raw/BD_Atlas_1991_2025_v1.xlsx"
BRIDGE = ROOT / "data/metadata/bridge_estacao_municipio.csv"
OUT_SE = ROOT / "data/processed/y_eventos_sudeste.csv"
OUT_EST = ROOT / "data/processed/y_eventos_estacoes.csv"
OUT_REL = ROOT / "reports/relatorio_validacao_atlas.txt"

ABA = "Atlas Valores Originais"
ANO_INI, ANO_FIM = 2008, 2022
COBRADE_HIDRO = {12100, 12200, 12300}
COBRADE_NOME = {12100: "Inundacoes", 12200: "Enxurradas", 12300: "Alagamentos"}

# Mapeamento das colunas do Atlas novo -> nomes canonicos do pipeline antigo:
#   protocolo_s2id->protocolo | nome_municipio->municipio | sigla_uf->uf
#   cod_cobrade->cobrade | cod_ibge_mun->ibge | data_evento->data (data escolhida)
#   regiao, descricao_tipologia, grupo_de_desastre ja batem.
# Na pratica so as 3 colunas de texto sao renomeadas via `TXT` (abaixo); cobrade/ibge/data
# ja sao criadas com o nome canonico durante o processamento.
OUT_COLS = ["protocolo", "municipio", "uf", "data", "cobrade", "ibge",
            "regiao", "descricao_tipologia", "grupo_de_desastre", "evento"]

buf = io.StringIO()
def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    buf.write(s + "\n")

# ------------------------------------------------------------------ carga
raw = pd.read_excel(ATLAS, sheet_name=ABA)
raw.columns = [str(c).strip().lower() for c in raw.columns]
n_total = len(raw)

# datas nativas do Excel
raw["data_evento"] = pd.to_datetime(raw["data_evento"], errors="coerce")
raw["data_registro"] = pd.to_datetime(raw["data_registro"], errors="coerce")

# descartar registros com Data_Registro em 2026 (futuro ao evento, irrelevante pro Y)
mask_2026 = raw["data_registro"].dt.year == 2026
n_desc2026 = int(mask_2026.sum())
atlas = raw.loc[~mask_2026].copy()
n_universo = len(atlas)

# tipos das chaves
atlas["cobrade"] = pd.to_numeric(atlas["cod_cobrade"], errors="coerce").astype("Int64")
atlas["ibge"] = pd.to_numeric(atlas["cod_ibge_mun"], errors="coerce").astype("Int64")
atlas["regiao_l"] = atlas["regiao"].astype(str).str.strip().str.lower()

# recorte hidro-SE (sem filtro de ano) — base para analises (a) e (b)
hidro_se = atlas[atlas["regiao_l"].eq("sudeste") & atlas["cobrade"].isin(COBRADE_HIDRO)].copy()

# ------------------------------------------------------- Y (Data_Evento)
def build_y(df, date_col, lo, hi):
    d = df[date_col]
    m = df["regiao_l"].eq("sudeste") & df["cobrade"].isin(COBRADE_HIDRO) & d.dt.year.between(lo, hi)
    sub = df.loc[m].copy()
    sub["data"] = d[m]
    sub = sub.dropna(subset=["ibge", "data"]).drop_duplicates(["ibge", "data"])
    return sub

y = build_y(atlas, "data_evento", ANO_INI, ANO_FIM)
y["evento"] = 1
# renomear so as colunas de texto (cobrade/ibge/data ja estao canonicas)
TXT = {"protocolo_s2id": "protocolo", "nome_municipio": "municipio", "sigla_uf": "uf"}
y_out = y.rename(columns=TXT)[OUT_COLS].sort_values(["ibge", "data"])
y_out.to_csv(OUT_SE, index=False, encoding="utf-8-sig")

# municipios com estacao (REUSA a bridge existente)
bridge = pd.read_csv(BRIDGE)
ibges_est = set(pd.to_numeric(bridge["ibge"], errors="coerce").dropna().astype(int))
n_mun_est = len(ibges_est)

y_est = y_out[y_out["ibge"].astype("Int64").isin(ibges_est)].copy()
y_est.to_csv(OUT_EST, index=False, encoding="utf-8-sig")

# ===================================================================
# RELATORIO
# ===================================================================
log("=" * 70)
log("RELATORIO DE VALIDACAO — Atlas consolidado (Y)  [BD_Atlas_1991_2025_v1]")
log("Gerado: 2026-07-15 | data do evento = Data_Evento | dedup ibge x data")
log("=" * 70)

log(f"\n[0] Fonte: {ATLAS.name}")
log(f"    Aba: '{ABA}'  ({raw.shape[1]} colunas)")
log(f"    Linhas na aba: {n_total:,}")
log(f"    Descartadas (Data_Registro em 2026): {n_desc2026}")
log(f"    Universo de trabalho: {n_universo:,}")

log(f"\n[1] Bridge reutilizada: {BRIDGE.name}  ({len(bridge)} estacoes | {n_mun_est} municipios distintos com estacao)")

# funil
n_se = int(atlas["regiao_l"].eq("sudeste").sum())
n_se_hidro = len(hidro_se)
n_se_hidro_anos = int((hidro_se["data_evento"].dt.year.between(ANO_INI, ANO_FIM)).sum())
log(f"\n[2] Funil (por Data_Evento):")
log(f"    Universo {n_universo:,} -> Sudeste {n_se:,} -> + COBRADE hidro {n_se_hidro:,}"
    f" -> + anos {ANO_INI}-{ANO_FIM} {n_se_hidro_anos:,}")
log(f"    Apos dedup (ibge x data): {len(y_out):,} eventos "
    f"({n_se_hidro_anos - len(y_out)} duplicatas removidas)")
log(f"\n[3] Eventos Sudeste: {len(y_out):,} | retidos em municipios com estacao: "
    f"{len(y_est):,} ({100*len(y_est)/len(y_out):.1f}%)")

# por ano
yr_se = y_out.assign(ano=pd.to_datetime(y_out["data"]).dt.year).groupby("ano").size()
yr_est = y_est.assign(ano=pd.to_datetime(y_est["data"]).dt.year).groupby("ano").size()
tab = pd.DataFrame({"sudeste": yr_se, "c_estacao": yr_est}).reindex(range(ANO_INI, ANO_FIM+1)).fillna(0).astype(int)
log(f"\n[4] Eventos por ano (Sudeste vs c/ estacao):")
log(tab.to_string())
zeros = tab.index[tab["sudeste"].eq(0)].tolist()
log("    OK: nenhum ano com 0 eventos." if not zeros else f"    ALERTA: anos com 0 eventos: {zeros}")

# por UF
uf = pd.DataFrame({
    "sudeste": y_out.groupby("uf").size(),
    "c_estacao": y_est.groupby("uf").size()}).fillna(0).astype(int)
log(f"\n[5] Eventos por UF:")
log(uf.to_string())

# por tipologia (retidos)
tip = y_est["cobrade"].map(COBRADE_NOME).value_counts()
log(f"\n[6] Distribuicao por tipologia (retidos c/ estacao): {tip.to_dict()}")

# ------------------------------------------------------------------
# RELATORIO COMPARATIVO (antigo vs novo)  -- Secao 4 da task
# ------------------------------------------------------------------
OLD = {
    "total": 62273, "hidro_se_dedup": 2672, "c_estacao": 403,
    "ano": {2008:238,2009:478,2010:307,2011:335,2012:273,2013:273,2014:37,
            2015:30,2016:110,2017:52,2018:104,2019:53,2020:122,2021:114,2022:146},
    "tip": {"Enxurradas":153,"Inundacoes":149,"Alagamentos":101},
}
log("\n" + "=" * 70)
log("COMPARATIVO  ANTIGO (1991-2022)  ->  NOVO (1991-2025_v1)")
log("=" * 70)
log(f"  Registros totais na base : {OLD['total']:,}  ->  {n_total:,}")
log(f"  Hidro-SE 2008-2022 dedup : {OLD['hidro_se_dedup']:,}  ->  {len(y_out):,}  "
    f"(delta {len(y_out)-OLD['hidro_se_dedup']:+d})")
log(f"  Em municipios c/ estacao : {OLD['c_estacao']:,}  ->  {len(y_est):,}  "
    f"(delta {len(y_est)-OLD['c_estacao']:+d})")

log("\n  Distribuicao por ano lado a lado (Sudeste dedup):")
log("    ano   antigo   novo   delta   flag")
for a in range(ANO_INI, ANO_FIM+1):
    o = OLD["ano"].get(a, 0); nnew = int(tab.loc[a, "sudeste"])
    d = nnew - o
    flag = "" if d == 0 else ("<-- MUDOU" if a < 2023 else "")
    log(f"    {a}   {o:5d}   {nnew:5d}   {d:+5d}   {flag}")

log("\n  Distribuicao por tipologia (retidos c/ estacao):")
for k in ["Enxurradas", "Inundacoes", "Alagamentos"]:
    o = OLD["tip"].get(k, 0); nnew = int(tip.get(k, 0))
    log(f"    {k:12s}: {o:4d}  ->  {nnew:4d}  ({nnew-o:+d})")

# ------------------------------------------------------------------
# Secao 5 da task — potencial 2023-2025 (NAO entra no Y)
# ------------------------------------------------------------------
log("\n" + "=" * 70)
log("POTENCIAL 2023-2025 (por Data_Evento; NAO incluido no Y — X so vai ate 2022-12-31)")
log("=" * 70)
y_fut = build_y(atlas, "data_evento", 2023, 2025)
y_fut_est = y_fut[y_fut["ibge"].astype("Int64").isin(ibges_est)]
fut_tab = pd.DataFrame({
    "sudeste": y_fut.assign(ano=y_fut["data"].dt.year).groupby("ano").size(),
    "c_estacao": y_fut_est.assign(ano=y_fut_est["data"].dt.year).groupby("ano").size(),
}).reindex([2023, 2024, 2025]).fillna(0).astype(int)
log(fut_tab.to_string())
log(f"    TOTAL 2023-2025: Sudeste {len(y_fut):,} | c/ estacao {len(y_fut_est):,}")
log(f"    -> {len(y_fut_est):,} positivos novos potenciais se o X for estendido a 2025.")

# ------------------------------------------------------------------
# ADICAO (a) — vies de dia-da-semana: Data_Evento vs Data_Registro
# ------------------------------------------------------------------
log("\n" + "=" * 70)
log("(a) VIES DE DIA-DA-SEMANA — hidro-SE 2008-2022 (registros, sem dedup)")
log("=" * 70)
dias = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"]
def dow_report(df, date_col, label):
    d = df[date_col]
    sub = df[d.dt.year.between(ANO_INI, ANO_FIM)]
    wd = sub[date_col].dt.dayofweek  # 0=Seg ... 6=Dom
    cnt = wd.value_counts().reindex(range(7)).fillna(0).astype(int)
    n = int(cnt.sum())
    wk = int(cnt[5] + cnt[6])                      # sab+dom
    obs_wknd = 100 * wk / n if n else 0
    esp_wknd = 100 * 2 / 7
    # deficit relativo: quanto o fim de semana esta abaixo do esperado 2/7
    deficit = 100 * (esp_wknd - obs_wknd) / esp_wknd
    log(f"\n  [{label}]  n={n:,}")
    log("    " + "  ".join(f"{dias[i]}:{cnt[i]}" for i in range(7)))
    log(f"    fim de semana observado: {obs_wknd:.1f}%  | esperado: {esp_wknd:.1f}%  "
        f"| deficit relativo: {deficit:+.1f}%")
    return deficit
def_evt = dow_report(hidro_se, "data_evento", "Data_Evento")
def_reg = dow_report(hidro_se, "data_registro", "Data_Registro")
log(f"\n  CONCLUSAO: deficit de fim de semana  Registro={def_reg:+.1f}%  Evento={def_evt:+.1f}%")
if def_evt < def_reg:
    log(f"    -> O deficit DIMINUI ao usar Data_Evento ({def_reg:+.1f}% -> {def_evt:+.1f}%),"
        f" reducao de {def_reg-def_evt:.1f} p.p.")
else:
    log(f"    -> O deficit NAO diminui com Data_Evento.")

# ------------------------------------------------------------------
# ADICAO (b) — quebra estrutural de 2014 na serie por Data_Evento
# ------------------------------------------------------------------
log("\n" + "=" * 70)
log("(b) QUEBRA ESTRUTURAL 2014 — serie anual hidro-SE dedup (Data_Evento)")
log("=" * 70)
serie = tab["sudeste"]
antes = serie.loc[2008:2013]
depois = serie.loc[2014:2022]
m_antes, m_depois = antes.mean(), depois.mean()
queda = 100 * (m_antes - m_depois) / m_antes
log("    " + "  ".join(f"{a}:{int(serie[a])}" for a in range(ANO_INI, ANO_FIM+1)))
log(f"    media 2008-2013: {m_antes:.1f}/ano | media 2014-2022: {m_depois:.1f}/ano "
    f"| queda: {queda:.1f}%")
log(f"    2013->2014: {int(serie[2013])} -> {int(serie[2014])} "
    f"({100*(serie[2014]-serie[2013])/serie[2013]:+.0f}%)")
if queda > 30 and serie[2014] < 0.6 * m_antes:
    log("    -> A quebra de 2014 PERSISTE na serie por Data_Evento "
        "(queda abrupta e sustentada apos 2013).")
else:
    log("    -> A quebra de 2014 se ATENUA/DESAPARECE na serie por Data_Evento.")

log("\n" + "=" * 70)
log(f"Saidas: {OUT_SE.relative_to(ROOT)} | {OUT_EST.relative_to(ROOT)}")
log("=" * 70)

OUT_REL.write_text(buf.getvalue(), encoding="utf-8")
print(f"\n[OK] relatorio salvo em {OUT_REL}")
print(f"[OK] {OUT_SE.name}: {len(y_out)} linhas | {OUT_EST.name}: {len(y_est)} linhas")
