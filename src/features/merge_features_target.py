#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Merge X (features diarias por municipio) + Y (eventos do Atlas) -> tabela de
modelagem municipio-dia com rotulo evento 0/1.

X: features_diarias_municipio_v4.parquet (Drive: imports_tratadas_usar_esse),
   precipitacao diaria consolidada por municipio (ja agrega multiplas estacoes).
Y: y_eventos_estacoes.csv, eventos hidro-SE 2008-2022, COBRADE {12100,12200,12300},
   dedup ibge x data.

Metodo: LEFT JOIN a partir do X (mantem TODOS os municipio-dia com feature).
Chave = CODIGO_MUNICIPIO_IBGE x data_local = ibge x data.
evento = 1 se ha registro de desastre naquele municipio-dia, senao 0.
Eventos cuja data cai fora da cobertura da serie da estacao nao tem linha de
feature -> nao entram (positivos inobservaveis pelo X); sao listados a parte.

Saidas:
  data/processed/dataset_modelagem_municipio.parquet
  reports/relatorio_merge_modelagem.txt
  reports/eventos_sem_feature_municipio.csv
"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[2]
X = ROOT / "data/raw/features_diarias_municipio_v4.parquet"
Y = ROOT / "data/processed/y_eventos_estacoes.csv"
OUT = ROOT / "data/processed/dataset_modelagem_municipio.parquet"
OUT_REL = ROOT / "reports/relatorio_merge_modelagem.txt"
OUT_LOST = ROOT / "reports/eventos_sem_feature_municipio.csv"


def main():
    con = duckdb.connect()
    con.execute(f"CREATE VIEW xf AS SELECT * FROM read_parquet('{X.as_posix()}');")
    con.execute(f"""
        CREATE VIEW yf AS
        SELECT CAST(ibge AS BIGINT) AS ibge, CAST(data AS DATE) AS dt,
               protocolo, cobrade, descricao_tipologia, grupo_de_desastre
        FROM read_csv_auto('{Y.as_posix()}');
    """)

    # dedup check (evita fan-out): Y deve ter 1 linha por ibge x data
    n_y, n_par = con.execute(
        "SELECT count(*), count(DISTINCT (ibge, dt)) FROM yf"
    ).fetchone()
    assert n_y == n_par, f"Y tem duplicata ibge x data: {n_y} linhas, {n_par} pares"

    con.execute(f"""
        COPY (
          SELECT x.*,
                 CASE WHEN y.ibge IS NOT NULL THEN 1 ELSE 0 END AS evento,
                 y.protocolo, y.cobrade, y.descricao_tipologia, y.grupo_de_desastre
          FROM xf x
          LEFT JOIN yf y
            ON CAST(x.CODIGO_MUNICIPIO_IBGE AS BIGINT) = y.ibge
           AND x.data_local = y.dt
        ) TO '{OUT.as_posix()}' (FORMAT parquet, COMPRESSION zstd);
    """)

    # eventos sem linha de feature (fora da cobertura da serie)
    con.execute(f"""
        COPY (
          SELECT y.protocolo, y.dt AS data, y.ibge, y.cobrade, y.descricao_tipologia
          FROM yf y
          LEFT JOIN xf x
            ON CAST(x.CODIGO_MUNICIPIO_IBGE AS BIGINT) = y.ibge AND x.data_local = y.dt
          WHERE x.CODIGO_MUNICIPIO_IBGE IS NULL
          ORDER BY y.dt
        ) TO '{OUT_LOST.as_posix()}' (HEADER, DELIMITER ',');
    """)

    tot = con.execute(f"SELECT count(*) FROM read_parquet('{OUT.as_posix()}')").fetchone()[0]
    pos = con.execute(f"SELECT sum(evento) FROM read_parquet('{OUT.as_posix()}')").fetchone()[0]
    perdidos = n_y - pos
    jv = con.execute(
        f"SELECT janela_valida, count(*) FROM read_parquet('{OUT.as_posix()}') "
        "WHERE evento=1 GROUP BY 1 ORDER BY 1"
    ).fetchall()
    tipo = con.execute(
        f"SELECT descricao_tipologia, count(*) FROM read_parquet('{OUT.as_posix()}') "
        "WHERE evento=1 GROUP BY 1 ORDER BY 2 DESC"
    ).fetchall()

    rel = f"""RELATORIO DO MERGE - TABELA DE MODELAGEM (municipio-dia)
========================================================================
Fontes:
  X: {X.name} (Drive/imports_tratadas_usar_esse)
  Y: {Y.name} ({n_y} eventos, dedup ibge x data)

Saida: {OUT.name} (Parquet ZSTD)
  Linhas (municipio-dia): {tot:,}
  Positivos (evento=1):   {pos:,}  (prevalencia {pos/tot*100:.3f}%)
  Negativos:              {tot-pos:,}

Positivos nao incorporados: {perdidos} de {n_y}
  Eventos cuja data cai fora da cobertura da serie da estacao (sem feature).
  Lista: {OUT_LOST.name}
  {n_y} eventos no Y -> {pos} com feature (evento=1) + {perdidos} sem feature.

Qualidade dos positivos:
  por janela_valida: {dict(jv)}
  por tipologia:     {dict(tipo)}
"""
    OUT_REL.write_text(rel, encoding="utf-8")
    print(rel)
    print("OK:", OUT.name, OUT_REL.name, OUT_LOST.name)


if __name__ == "__main__":
    main()
