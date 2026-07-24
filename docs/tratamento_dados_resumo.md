# Resumo do tratamento de dados — limpeza, imputação e estruturação (INMET)

> Log metodológico do pipeline DuckDB/INMET (origem: Colab `TCC_AnaliseDuck.ipynb`,
> pasta Drive `imports_tratadas_usar_esse`). Registra **o que** foi feito, **por quê**
> e **o que falta** — base para a seção de metodologia/qualidade de dados do TCC.
> O notebook original é Colab da dupla e não está versionado; este doc é o registro
> dessa etapa dentro do repo.

## 1. Ponto de partida
Fonte bruta: `INMET_consolidado3.csv`, carregado via DuckDB (`read_csv_auto`) para a
tabela `chuvas`. Pipeline de tratamento no notebook:

- `chuvas` (bruta)
- → `chuvas_limpa` (dedup via `SELECT DISTINCT`)
- → `chuvas_tratado` (tipagem, parsing de `HORA_UTC` corrigido, criação de `dt_utc`)
- → `chuvas_2008_2022` / `chuvas_2008_2022_valid` (recorte temporal + exclusão de estações problemáticas)
- → imputação por estação (interpolação ≤6h, ffill/bfill 6–48h, mantém NaN para gaps >48h)
- → decisão de segmentação/exclusão por tier de completude (A/B/C)
- → exclusão final de estações cronicamente instáveis
- → `imputed_by_station_final/` (parquets por estação, 142 arquivos antes da exclusão adicional)
- → `metadados_estacoes.csv` (identidade + geo + qualidade por estação)

## 2. Exportação consolidada
Problema: o pipeline reprocessava tudo do zero a cada sessão do Colab, e o DuckDB
local (`chuvas.duckdb`) não persiste entre sessões. Solução: duas tabelas finais em
Parquet + ZSTD (tipagem preservada, mais compacto/rápido que CSV):

- **`chuvas_tratado_final.parquet`** — todas as variáveis meteorológicas, limpas e
  tipadas, SEM imputação. Equivale a `chuvas_tratado` do DuckDB.
- **`dataset_modelagem_final.parquet`** — só precipitação, PÓS-imputação e
  pós-exclusão de estações problemáticas, já com metadados de estação via join.

Checagens de qualidade antes de cada exportação: duplicatas residuais
(`CODIGO_WMO`, data, hora); linhas sem metadado casado no join (join órfão);
contagem do consolidado == soma dos arquivos individuais (garante que o join não duplicou).

**IMPORTANTE** — só `precip_mm` foi imputado. As demais variáveis (temperatura,
umidade, pressão, radiação) NÃO passaram por tratamento de ausentes nem pela exclusão
de estações instáveis. Se forem entrar no modelo, precisam de imputação própria.

## 3. Geocodificação: estação → município
Os dados tinham UF e REGIAO, mas não MUNICIPIO, só lat/lon.

- **Método 1**: join espacial point-in-polygon com `geobr` (limites municipais IBGE),
  fallback `sjoin_nearest` (EPSG:5880) com threshold de 100 km.
- **Método 2** (já existia): `bridge_estacao_municipio.csv` (CODIGO_WMO → município
  IBGE, 141 estações). A coluna `distancia_check` **NÃO é confiável** (0.0 em todas
  as 141 linhas, std=0 — impossível para checagem real). Não usar como evidência de qualidade.
- **Validação cruzada**: geobr vs bridge → **100% de concordância (141/141)**. Boa
  evidência de metodologia para citar no TCC.
- **Decisão**: MUNICIPIO usa o bridge como fonte primária; geobr mantido como coluna
  de auditoria (`MUNICIPIO_geobr_auditoria`).

## 4. Duas estações problemáticas
- **S122 (EB_PEF_BONFIM)**, UF cadastrada = MG. geobr geocodificou para Bonfim/RR;
  o nome já continha "BONFIM" → UF do cadastro provavelmente errada (deveria ser RR).
  Impacto: NENHUM — já estava na exclusão original (`stations_exclude`).
- **C891 (CRIOSFERA)**, UF cadastrada = SP. É estação real do PROANTAR na **Antártica**
  (84°S). Regime antártico incompatível com o escopo. Impacto: SIGNIFICATIVO — NÃO
  estava na exclusão original. **Ação**: excluída (`status_final = 'excluida_fora_territorio'`);
  parquet movido para `imputed_by_station_excluidas_cronicas/`; dataset regenerado sem ela.

## 5. Incidente: perda e recuperação de colunas em `metadados_estacoes.csv`
Durante a geocodificação o CSV foi sobrescrito com um subconjunto de colunas,
descartando as de qualidade/período. Recuperado a partir de backup íntegro
(`TCC/Metadados_estacoes/metadados_estacoes.csv`, 152 linhas, 19 colunas, 04/07/2026)
+ MUNICIPIO do bridge + reaplicação da exclusão do C891.

**Lição**: há pastas duplicadas no Drive (`imports_tratadas/`, `imports_tratadas_usar_esse/`,
`Metadados_estacoes/`) com versões diferentes de `metadados_estacoes.csv` — risco de bug
silencioso. Pasta oficial: **`imports_tratadas_usar_esse/`**.

## 6. Estado final validado (`dataset_modelagem_final.parquet`)
- 141 estações (152 − 11 excluídas, incluindo C891)
- 133 municípios (5 concentram >1 estação: RJ=4, BH=3, Campos dos Goytacazes/SP/Resende=2)
- 4 UFs (MG, SP, RJ, ES); período 2008–2022
- 14.600.886 linhas (granularidade estação-hora); 0 sem MUNICIPIO; 0 do C891

## 7. O que ainda falta
1. Agregação estação-hora → estação-dia (soma diária + acumulados 24/48/72h **anteriores** à data de referência, sem vazamento).
2. Regra de agregação estação → município nos 5 municípios com múltiplas estações (média/máximo/mais próxima) — documentar.
3. Join com S2ID por (MUNICIPIO, data) → variável-alvo binária.
4. Nomear as fontes do "cruzamento de fontes" (provável CEMADEN) contra subnotificação do S2ID.
5. Imputação das demais variáveis meteorológicas, se forem entrar no modelo.

## 8. Pontos de metodologia a formalizar no texto
- Definição operacional do alvo: `y=1` se S2ID registra inundação OU alagamento OU
  enxurrada para o município na data (sinal único de "chance de evento").
- Nota de limitação sobre heterogeneidade física do alvo combinado.
- Calibração (Brier / reliability) além de F1/PR-AUC — o objetivo é estimar probabilidade.
- Validação temporal: walk-forward / expanding window (15 anos, eventos raros).
- Achados de qualidade (S122, C891, `distancia_check`, concordância geobr×bridge) são
  material para a seção de qualidade de dados.
