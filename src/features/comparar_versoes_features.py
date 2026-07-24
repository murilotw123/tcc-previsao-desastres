#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Compara duas versoes das features diarias por municipio (ex.: v3 vs v4) para
entender o que muda entre elas antes de fixar a versao canonica.

Confere: estrutura (linhas, municipios, periodo, colunas), municipio-dias
presentes em um e ausentes no outro, e quantas linhas mudam em cada coluna de
precipitacao / janela_valida (join por municipio x dia).

Entradas (ajuste os caminhos conforme onde estao as versoes):
  data/raw/features_diarias_municipio_v4.parquet      (canonica)
  data/archive/features_diarias_municipio_v3.parquet  (antiga, arquivada)

Saida:
  reports/comparacao_v3_v4.md  (o texto interpretativo e mantido a mao neste .md;
  este script imprime os numeros que embasam esse relatorio).
"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]
V_NOVA = ROOT / "data/raw/features_diarias_municipio_v4.parquet"
V_ANTIGA = ROOT / "data/archive/features_diarias_municipio_v3.parquet"

COLS = ["precip_dia", "precip_24h", "precip_48h", "precip_72h",
        "precip_max_horaria", "janela_valida", "n_estacoes"]


def stats(con, p, tag):
    n = con.execute(f"SELECT count(*) FROM read_parquet('{p}')").fetchone()[0]
    nmun = con.execute(f"SELECT count(DISTINCT CODIGO_MUNICIPIO_IBGE) FROM read_parquet('{p}')").fetchone()[0]
    dmin, dmax = con.execute(f"SELECT min(data_local), max(data_local) FROM read_parquet('{p}')").fetchone()
    print(f"[{tag}] linhas={n:,} municipios={nmun} periodo={dmin}..{dmax}")


def main():
    con = duckdb.connect()
    a = V_ANTIGA.as_posix()
    b = V_NOVA.as_posix()
    stats(con, a, V_ANTIGA.name)
    stats(con, b, V_NOVA.name)
    con.execute(f"CREATE VIEW xa AS SELECT * FROM read_parquet('{a}');")
    con.execute(f"CREATE VIEW xb AS SELECT * FROM read_parquet('{b}');")

    only_a = con.execute("SELECT count(*) FROM (SELECT CODIGO_MUNICIPIO_IBGE,data_local FROM xa EXCEPT SELECT CODIGO_MUNICIPIO_IBGE,data_local FROM xb)").fetchone()[0]
    only_b = con.execute("SELECT count(*) FROM (SELECT CODIGO_MUNICIPIO_IBGE,data_local FROM xb EXCEPT SELECT CODIGO_MUNICIPIO_IBGE,data_local FROM xa)").fetchone()[0]
    print(f"municipio-dia so na antiga: {only_a}   so na nova: {only_b}")

    print("\nlinhas com valor diferente (join por municipio-dia):")
    for c in COLS:
        d = con.execute(
            f"SELECT sum(CASE WHEN a.{c} IS DISTINCT FROM b.{c} THEN 1 ELSE 0 END) "
            "FROM xa a JOIN xb b USING (CODIGO_MUNICIPIO_IBGE, data_local)"
        ).fetchone()[0]
        print(f"  {c:20s} {d}")

    print("\ntransicao de janela_valida (antiga -> nova):")
    for r in con.execute(
        "SELECT a.janela_valida, b.janela_valida, count(*) "
        "FROM xa a JOIN xb b USING (CODIGO_MUNICIPIO_IBGE, data_local) "
        "GROUP BY 1,2 ORDER BY 1,2"
    ).fetchall():
        print(f"  {r[0]} -> {r[1]} : {r[2]:,}")


if __name__ == "__main__":
    main()
