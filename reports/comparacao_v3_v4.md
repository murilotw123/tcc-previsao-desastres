# Comparação features_diarias_municipio: v3 vs v4

Gerado em 2026-07-24. Fonte: pasta `imports_tratadas_usar_esse` (Google Drive).

Objetivo: entender o que muda entre as versões v3 e v4 das features diárias por
município antes de fixar a versão canônica para a modelagem.

## Estrutura — idêntica nas duas versões

| Item | v3 | v4 |
|---|---|---|
| Linhas (município-dia) | 578.226 | 578.226 |
| Municípios | 133 | 133 |
| Período | 2008-01-01 → 2022-12-31 | idem |
| Colunas | 12 (mesmos nomes/tipos) | 12 |
| `n_estacoes` | — | idêntico (0 linhas diferentes) |

O **merge com o Y é invariante à versão**: nas duas, 323 positivos (`evento=1`),
78 eventos do Y sem linha de feature (todos fora da cobertura da série da estação).
A versão **não muda o grão nem o rótulo** — só os valores das features de chuva.

## O que muda de v3 → v4 (valores)

| Coluna | Linhas alteradas | Direção da mudança |
|---|---:|---|
| `janela_valida` | 22.118 | sempre `True`(v3) → `False`(v4). Nenhuma no sentido inverso. |
| `precip_72h` | 4.454 | v4 **sempre ≤** v3 (dif. min −303,6 mm; média abs. 9,8 mm) |
| `precip_48h` | 3.330 | v4 ≤ v3 |
| `precip_24h` | 2.334 | v4 ≤ v3 |
| `precip_dia` | 2.336 | v4 ≤ v3 |
| `precip_max_horaria` | 643 | v4 ≤ v3 |

Transição de `janela_valida`:

| v3 | v4 | n |
|---|---|---:|
| False | False | 34.062 |
| True | False | 22.118 |
| True | True | 522.046 |

## Interpretação

No **v3** os acumulados 24/48/72h estavam **inflados**: janelas com dias
faltantes/incompletos eram somadas como se os dias ausentes tivessem chuva válida,
gerando acumulados irreais (ex.: Unaí, 17/01/2011 → 519 mm em 72h no v3, 250 mm no v4;
Santa Leopoldina, 10/01/2022 → 444 mm → 141 mm).

O **v4 corrigiu**: quando a janela não tem os 3 dias completos, o acumulado é
recalculado (fica menor) e `janela_valida` passa a `False`. As 22.118 linhas que
viraram `False` são exatamente essas janelas antes contadas como válidas.

Efeito nos positivos (eventos): v3 = 308 válidos / 15 inválidos;
v4 = **298 / 25** — 10 eventos que pareciam ter janela boa no v3 têm janela
incompleta reconhecida no v4.

## Decisão

**v4 é a versão canônica** (`data/processed/dataset_modelagem_municipio.parquet`):
acumulados de chuva realistas e `janela_valida` confiável. O v3 superestima
acumulados em ~4.500 dias e foi arquivado em
`data/archive/dataset_modelagem_municipio_v3.parquet` (não deletado).
