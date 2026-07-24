#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de sinal: a precipitacao separa dias de evento (evento=1) de dias normais
(evento=0)? Roda sobre a tabela de modelagem municipio-dia (v4 canonica).

Para precip_dia, precip_24h, precip_48h, precip_72h calcula:
  - mediana, p75, p90, p99 em cada grupo (evento 0/1);
  - AUC = P(um dia de evento ter chuva > um dia normal) como medida de
    separabilidade (0,5 = sem sinal; 1,0 = separacao perfeita);
  - boxplots (escala symlog) evento vs normal.
Refaz a mesma analise restringindo a janela_valida=True nos dois grupos.

Saidas:
  reports/figures/teste_sinal_boxplots.png
  reports/figures/teste_sinal_boxplots_janela_valida.png
  reports/teste_sinal.md  (tabelas + conclusao; texto interpretativo a mao)
"""
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/processed/dataset_modelagem_municipio.parquet"
FIGDIR = ROOT / "reports/figures"

VARS = ["precip_dia", "precip_24h", "precip_48h", "precip_72h"]
PCTS = [50, 75, 90, 99]


def auc(pos, neg):
    """AUC de Mann-Whitney (rank-based), ignorando NaN."""
    pos, neg = pos.dropna(), neg.dropna()
    n1, n2 = len(pos), len(neg)
    if n1 == 0 or n2 == 0:
        return np.nan
    r = pd.concat([pos, neg]).rank(method="average")
    return (r.iloc[:n1].sum() - n1 * (n1 + 1) / 2) / (n1 * n2)


def tabela(d, titulo):
    print("\n###", titulo)
    for v in VARS:
        for grp, lab in [(1, "evento=1"), (0, "evento=0")]:
            s = d.loc[d.evento == grp, v].dropna()
            q = np.percentile(s, PCTS)
            print(f"  {v:11s} {lab:9s} n={len(s):>7d}  med={q[0]:6.1f} p75={q[1]:6.1f} p90={q[2]:6.1f} p99={q[3]:6.1f}")
    print("  -- separabilidade (AUC) --")
    for v in VARS:
        print(f"  {v:11s} AUC={auc(d.loc[d.evento==1,v], d.loc[d.evento==0,v]):.4f}")


def boxfig(d, fname, sup):
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.5))
    for ax, v in zip(axes, VARS):
        g0 = d.loc[d.evento == 0, v].dropna()
        g1 = d.loc[d.evento == 1, v].dropna()
        ax.boxplot([g0, g1], tick_labels=["normal\n(ev=0)", "evento\n(ev=1)"],
                   showfliers=True, widths=0.6,
                   flierprops=dict(marker='.', markersize=3, alpha=0.3,
                                   markerfacecolor='gray', markeredgecolor='none'),
                   medianprops=dict(color='crimson', linewidth=2),
                   boxprops=dict(color='steelblue'), whiskerprops=dict(color='steelblue'))
        ax.set_yscale("symlog")
        ax.set_title(v)
        ax.set_ylabel("mm (symlog)")
        ax.grid(axis='y', alpha=0.3)
    fig.suptitle(sup, fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(fname, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print("salvo:", fname)


def main():
    FIGDIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    df = con.execute(
        f"SELECT precip_dia,precip_24h,precip_48h,precip_72h,janela_valida,evento "
        f"FROM read_parquet('{DATASET.as_posix()}')"
    ).fetchdf()

    tabela(df, "A) todos os positivos vs todos os negativos")
    boxfig(df, FIGDIR / "teste_sinal_boxplots.png",
           "Precipitacao: dias de evento vs dias normais (todos os positivos)")

    dfB = df[df.janela_valida == True]
    tabela(dfB, "B) so janela_valida=True")
    boxfig(dfB, FIGDIR / "teste_sinal_boxplots_janela_valida.png",
           "Precipitacao: evento vs normal - so janela_valida=True")


if __name__ == "__main__":
    main()
