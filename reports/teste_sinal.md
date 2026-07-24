# Teste de sinal — precipitação vs ocorrência de evento (v4)

Gerado em 2026-07-24. Base: `data/processed/dataset_modelagem_municipio.parquet`
(v4 canônico). Compara a distribuição de chuva entre dias de desastre (`evento=1`)
e dias normais (`evento=0`), por município-dia.

Métrica de separabilidade: **AUC = P(um dia de evento ter chuva maior que um dia
normal)**. 0,5 = sem sinal; 1,0 = separação perfeita. Percentis e AUC ignoram NaN
(dias sem janela válida para o acumulado).

## Cenário A — todos os positivos (323) vs todos os negativos

| variável | grupo | n | mediana | p75 | p90 | p99 |
|---|---|---:|---:|---:|---:|---:|
| precip_dia | evento=1 | 310 | **19,0** | 51,3 | 93,9 | 181,6 |
| precip_dia | evento=0 | 548.025 | 0,0 | 1,2 | 11,4 | 50,0 |
| precip_24h | evento=1 | 311 | 8,6 | 31,8 | 59,0 | 121,9 |
| precip_24h | evento=0 | 547.983 | 0,0 | 1,2 | 11,4 | 50,2 |
| precip_48h | evento=1 | 311 | 21,2 | 52,0 | 101,6 | 185,9 |
| precip_48h | evento=0 | 549.130 | 0,2 | 6,0 | 24,2 | 76,8 |
| precip_72h | evento=1 | 312 | 34,3 | 71,7 | 137,6 | 248,1 |
| precip_72h | evento=0 | 549.902 | 0,5 | 11,8 | 35,2 | 98,6 |

**Separabilidade (AUC):**

| variável | AUC |
|---|---:|
| **precip_dia** | **0,816** |
| precip_72h | 0,763 |
| precip_48h | 0,760 |
| precip_24h | 0,755 |

Boxplot: `reports/figures/teste_sinal_boxplots.png`

## Cenário B — só janela_valida=True (positivos = 298, negativos = 521.748)

| variável | grupo | n | mediana | p75 | p90 | p99 |
|---|---|---:|---:|---:|---:|---:|
| precip_dia | evento=1 | 298 | **20,1** | 52,6 | 98,6 | 182,2 |
| precip_dia | evento=0 | 521.737 | 0,0 | 1,2 | 11,6 | 50,6 |
| precip_24h | evento=1 | 298 | 8,8 | 33,2 | 59,4 | 122,3 |
| precip_24h | evento=0 | 521.748 | 0,0 | 1,2 | 11,6 | 50,6 |
| precip_48h | evento=1 | 298 | 21,5 | 51,4 | 99,9 | 189,0 |
| precip_48h | evento=0 | 521.748 | 0,2 | 6,2 | 24,6 | 77,4 |
| precip_72h | evento=1 | 298 | 34,7 | 70,8 | 137,3 | 248,8 |
| precip_72h | evento=0 | 521.748 | 0,6 | 12,4 | 36,0 | 99,2 |

**Separabilidade (AUC):**

| variável | AUC |
|---|---:|
| **precip_dia** | **0,823** |
| precip_72h | 0,768 |
| precip_48h | 0,763 |
| precip_24h | 0,760 |

Boxplot: `reports/figures/teste_sinal_boxplots_janela_valida.png`

Filtrar por `janela_valida=True` **quase não muda** os resultados (AUC sobe ~0,005).
O sinal é robusto — não depende das janelas incompletas.

## Conclusões

1. **Sim, os dias de evento têm chuva claramente maior que os dias normais.**
   A mediana de `precip_dia` num dia de desastre é **19–20 mm**, contra **0 mm**
   num dia normal. No p90 a diferença é ~94 mm vs ~11 mm. A separação é visível em
   todas as quatro variáveis nos boxplots.

2. **A variável que melhor separa os grupos é `precip_dia`** (chuva do próprio dia),
   com AUC ≈ **0,82** — bem acima das três acumuladas (24h/48h/72h ≈ 0,76). Ou seja,
   o desastre está fortemente associado à **chuva intensa do dia do registro**, mais
   do que ao acúmulo dos dias anteriores. Entre as acumuladas, `precip_72h` é a
   melhor (0,76), e `precip_24h` a pior (0,755) — as janelas móveis diluem um pouco
   o pico do dia.

3. **Implicação para a modelagem:** há sinal real e explorável (AUC 0,82 de uma
   única feature é forte), mas o problema é **muito desbalanceado** (prevalência
   0,056%). `precip_dia` deve ser o preditor de base; as acumuladas agregam
   informação de contexto, mas isoladamente separam menos. Vale testar interações
   e considerar reamostragem / pesos de classe no treino.
