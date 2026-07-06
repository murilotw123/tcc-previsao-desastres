# TAREFA: Montar o Atlas consolidado (Y) — filtrado por anos e por estações

Construir a tabela-alvo (Y) de eventos pluviométricos, restrita ao recorte do
projeto e aos municípios que têm estação meteorológica. Saída pronta pra dar
`left join` no painel estação×dia do X mais adiante.

> IMPORTANTE: esta tarefa NÃO usa o `INMET_consolidado3.csv` (2,8 GB). Só toca em
> arquivos pequenos. Não carregue o consolidado aqui.

---

## Parâmetros (editar aqui no topo)

```python
ANO_INI = 2008          # início do recorte (overlap X↔Y). Metadado começa em 2008-01-01.
ANO_FIM = 2022          # Atlas vai até 2022.
COBRADE_HIDRO = {12100, 12200, 12300}   # Inundações, Enxurradas, Alagamentos
ANO_MALHA_IBGE = 2022   # malha municipal do IBGE usada no join espacial
```

## Entradas (confirmar os caminhos reais no repo)
- `Metadados_estacoes/metadados_estacoes.csv` — 1 linha por estação. Colunas relevantes:
  `CODIGO_WMO, ESTACAO, UF, REGIAO, latitude, longitude, altitude, status_final, motivo_exclusao_final, qualidade_geral`
- `stations_exclude.csv` — coluna única `CODIGO_WMO`, estações a descartar (missing >30% / série curta).
- `BD_Atlas_1991_2022.xlsx` — aba **"Atlas - Valores Originais"**. Colunas relevantes:
  `protocolo, municipio, uf, data, cobrade, ibge, regiao, descricao_tipologia, grupo_de_desastre`.

## Saídas esperadas
- `bridge_estacao_municipio.csv` → `CODIGO_WMO, ESTACAO, ibge, municipio_ibge, uf, distancia_check`
- `y_eventos_sudeste.csv` → Atlas filtrado (todos os municípios do Sudeste) — para referência.
- `y_eventos_estacoes.csv` → **o entregável principal**: eventos só nos municípios que têm estação.
- Um relatório impresso no fim (ver seção "Validações").

---

## Passos

### 1. Estações incluídas
- Ler `metadados_estacoes.csv`.
- Manter `status_final == 'incluida'` e remover os `CODIGO_WMO` que estão no `stations_exclude.csv`.
- Guardar `CODIGO_WMO, ESTACAO, UF, latitude, longitude`.

### 2. Ponte estação → IBGE (join espacial)
- Baixar a malha municipal do IBGE. Sugestão: pacote `geobr`
  (`pip install geobr`; `geobr.read_municipality(code_muni="all", year=ANO_MALHA_IBGE)`),
  que retorna um GeoDataFrame com `code_muni` (IBGE 7 dígitos) e `geometry`.
- Transformar as estações em GeoDataFrame de pontos (CRS EPSG:4326) a partir de lat/long.
- `geopandas.sjoin` com predicado `within` → cada estação recebe o `code_muni` (IBGE) do
  polígono em que cai.
- **Conferência obrigatória:** comparar o nome do município encontrado com a coluna `ESTACAO`.
  Divergências são esperadas (estação pode estar em município vizinho ao que dá nome a ela),
  mas listar as divergências pra revisão manual. NÃO usar o nome como método de join, só como check.
- Se alguma estação não cair em nenhum polígono (ponto no mar/fronteira), usar o município
  mais próximo (`sjoin_nearest`) e marcar na coluna `distancia_check`.

### 3. Filtrar o Atlas
- Ler a aba "Atlas - Valores Originais".
- Normalizar: `df.columns = [c.strip().lower() for c in df.columns]`.
- `data` está em formato **americano (M/D/AAAA)** → `pd.to_datetime(df["data"], errors="coerce")`.
- `ibge` e `cobrade` → numérico (`Int64`).
- Filtrar: `regiao.str.lower() == 'sudeste'` **E** `cobrade in COBRADE_HIDRO` **E**
  `data.dt.year between ANO_INI e ANO_FIM`.
- Deduplicar por `ibge × data` (mais de um registro no mesmo município/dia = 1 evento).
- Marcar `evento = 1`. Salvar como `y_eventos_sudeste.csv`.

### 4. Restringir aos municípios com estação
- Filtrar `y_eventos_sudeste` mantendo só as linhas cujo `ibge` está no conjunto de IBGEs
  da ponte (passo 2).
- Salvar como `y_eventos_estacoes.csv`. **Este é o Y que casa com o X.**

### 5. Validações (imprimir no terminal)
- Nº de estações incluídas e quantas mapearam pra IBGE (e quantas por `sjoin_nearest`).
- Lista de divergências nome-estação vs município do join.
- Nº de municípios distintos com estação.
- Eventos: total no Sudeste vs total retido nos municípios com estação (e % retido).
- Eventos por ano e por UF.
- Top 15 municípios com mais eventos.
- Alerta se algum ano do recorte ficar com 0 eventos.

---

## Cuidados / gotchas já conhecidos
- `regiao` no Atlas é **"Sudeste"**; no metadado é **"SE"** — encodings diferentes, não comparar direto.
- IBGE no Atlas é 7 dígitos (ex.: 4215406) e bate com `code_muni` do `geobr`.
- O Atlas só tem dias COM evento. Os dias `0` (sem evento) **não** são gerados aqui — nascem
  ao cruzar com o painel estação×dia do X (tarefa seguinte).
- Não commitar arquivos de dados no git (só o código). Definir versão canônica dos consolidados
  com a dupla antes de rodar.

## Esqueleto de referência (verificar nomes de coluna reais antes de rodar)

```python
import pandas as pd, geopandas as gpd, geobr

# 1) estações incluídas
meta = pd.read_csv("Metadados_estacoes/metadados_estacoes.csv")
excl = pd.read_csv("stations_exclude.csv")["CODIGO_WMO"].tolist()
est = meta[(meta.status_final == "incluida") & (~meta.CODIGO_WMO.isin(excl))].copy()

# 2) ponte espacial
mun = geobr.read_municipality(code_muni="all", year=2022).to_crs(4326)
gest = gpd.GeoDataFrame(
    est, geometry=gpd.points_from_xy(est.longitude, est.latitude), crs=4326)
bridge = gpd.sjoin(gest, mun[["code_muni", "name_muni", "geometry"]],
                   how="left", predicate="within")
# TODO: sjoin_nearest para os que ficaram sem match; check nome vs ESTACAO

# 3) filtrar Atlas
atlas = pd.read_excel("BD_Atlas_1991_2022.xlsx", sheet_name="Atlas - Valores Originais")
atlas.columns = [c.strip().lower() for c in atlas.columns]
atlas["data"] = pd.to_datetime(atlas["data"], errors="coerce")
atlas["ibge"] = pd.to_numeric(atlas["ibge"], errors="coerce").astype("Int64")
atlas["cobrade"] = pd.to_numeric(atlas["cobrade"], errors="coerce").astype("Int64")
m = ((atlas.regiao.str.lower() == "sudeste")
     & (atlas.cobrade.isin({12100, 12200, 12300}))
     & (atlas.data.dt.year.between(2008, 2022)))
y = (atlas[m].dropna(subset=["ibge", "data"])
     .drop_duplicates(["ibge", "data"]).assign(evento=1))
y.to_csv("y_eventos_sudeste.csv", index=False, encoding="utf-8-sig")

# 4) restringir a municípios com estação
ibges = set(bridge["code_muni"].dropna().astype("Int64"))
y_est = y[y.ibge.isin(ibges)]
y_est.to_csv("y_eventos_estacoes.csv", index=False, encoding="utf-8-sig")
```
