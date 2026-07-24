# Guia de uso — base de precipitação tratada (X) e derivados

> Guia da base de preditores gerada pelo pipeline de limpeza/imputação
> (`imports_tratadas_usar_esse` no Drive). Documenta granularidade, esquema e
> cuidados de uso — inclui os avisos anti-vazamento que valem para o merge com o Y.

## O que a base é (e o que não é)
- **É**: série temporal de precipitação horária, tratada (imputada) e consolidada,
  com metadados de estação anexados. É o conjunto de PREDITORES de base (X).
- **NÃO é** rótulo: os registros de desastre (S2ID/Atlas) são cruzados por
  (MUNICIPIO, data) num passo posterior — ver `src/features/merge_features_target.py`.
- **NÃO é** dado diário: a granularidade de `dataset_modelagem_final.parquet` é
  **estação-hora**. Precisa agregar para estação-dia (e depois consolidar por
  município) antes dos acumulados 24/48/72h e do cruzamento com o alvo.

## Granularidade e tamanho (`dataset_modelagem_final.parquet`, horário)
1 linha = 1 estação em 1 hora. Estações: 141; Municípios: 133; UFs: 4 (MG, SP, RJ, ES);
Período: 2008-01-01 a 2022-12-31; 14.600.886 linhas; Parquet ZSTD.

## Esquema (22 colunas)
- **Temporal**: `CODIGO_WMO`, `dt_utc` (chave composta).
- **Meteorológica**: `precip_mm` (única variável imputada hoje).
- **Qualidade por linha**: `orig_missing`, `gap_hours`, `gap_classe`
  (curto/medio/longo/extremo/nao_aplicavel), `imputed_flag`, `imputation_method`
  (`linear_6h` / `fb_48h` / None).
- **Identidade/geo da estação** (fixo): `ESTACAO`, `UF`, `REGIAO`, `MUNICIPIO`
  (fonte bridge, validado 100% contra geobr/IBGE), `CODIGO_MUNICIPIO_IBGE`,
  `latitude`, `longitude`, `altitude`.
- **Qualidade/status da estação** (fixo): `status_final`, `qualidade_geral`,
  `pct_imputado`, `periodo_valido_inicio/fim`, `motivo_exclusao_final`.

## Derivados diários (nesta versão do pipeline)
As features diárias por município (`features_diarias_municipio_v4.parquet`) já saem
da agregação estação-hora → município-dia, com `precip_dia`, `precip_24h/48h/72h`,
`precip_max_horaria`, `n_estacoes`, `horas_imputadas_72h`, `janela_valida`. É esse
arquivo que entra no merge com o Y (ver `src/features/merge_features_target.py`).

## Cuidados ao usar
1. **Não confunda linha ausente originalmente com observada** — filtre/pondere por
   `orig_missing` / `imputed_flag` / `pct_imputado` em estatísticas descritivas.
2. **Municípios com múltiplas estações** (RJ=4, BH=3, Campos dos Goytacazes/SP/Resende=2)
   precisam de regra de agregação explícita estação→município.
3. **Acumulados 24/48/72h**: use janelas estritamente ANTERIORES à data prevista —
   nunca inclua a janela do próprio dia do evento (principal fonte de data leakage).
4. **Split treino/teste**: priorize corte temporal (walk-forward / expanding window),
   não split aleatório — série temporal autocorrelacionada, eventos raros.
5. **Sem covariáveis além de precipitação** — temperatura/umidade/pressão/radiação
   estão em `chuvas_tratado_final.parquet`, mas SEM tratamento de ausentes.
6. **C891 (Criosfera, antártica)** foi excluída por estar fora do escopo geográfico;
   se reprocessar do zero, adicionar `C891` à exclusão (junto de `S122`, `A560`, `A767`).

## Próximo passo no pipeline
Agregação diária → acumulados 24/48/72h (lag correto) → agregação estação→município →
join com o alvo por (MUNICIPIO, data) → dataset de modelagem (X diário + y). Já
implementado o merge município-dia em `src/features/merge_features_target.py`.
