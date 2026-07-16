# Refresh do Y com o Atlas novo (`BD_Atlas_1991_2025_v1.xlsx`)

**Data:** 2026-07-15
**Autor da execução:** pipeline `src/data/atlas_consolidado.py`
**Motivação:** o Atlas usado até então (`BD_Atlas_1991_2022.xlsx`) era o arquivo errado.
O correto é `BD_Atlas_1991_2025_v1.xlsx`. Este documento registra o refresh do Y,
as divergências de estrutura encontradas, as decisões tomadas e como o código foi feito.

---

## 1. Resumo executivo

| Métrica | Antigo (1991–2022) | Novo (1991–2025_v1) | Δ |
|---|---|---|---|
| Registros na base | 62.273 | 76.191 | — |
| Hidro-SE 2008–2022 (dedup ibge×data) | 2.672 | **2.659** | −13 |
| Retidos em municípios com estação | 403 | **401** | −2 |
| Enxurradas / Inundações / Alagamentos | 153 / 149 / 101 | 153 / **147** / 101 | −2 |

O Y encolheu levemente (o Atlas novo **revisou** registros antigos, não só acrescentou
2023+). A única revisão grande dentro do recorte foi **2022: 146 → 161 (+15)**.

Potencial fora do recorte (2023–2025, **não** entra no Y porque o X vai só até 2022-12-31):
**203** eventos hidro-SE, dos quais **30** em municípios com estação.

---

## 2. O que mudou na estrutura do arquivo (validação — Passo 2)

Não se assumiu que o arquivo novo fosse igual ao antigo. Divergências encontradas:

| Item | Antigo | Novo |
|---|---|---|
| Aba principal | `Atlas - Valores Originais` | `Atlas Valores Originais` (sem hífens) |
| Nº de colunas | ~9 úteis | **70** colunas |
| `data` | 1 coluna, texto M/D/AAAA (americano) | **2 colunas** `datetime` nativas: `Data_Evento`, `Data_Registro` |
| `protocolo` | `protocolo` | `Protocolo_S2iD` |
| `municipio` | `municipio` | `Nome_Municipio` |
| `uf` | `uf` | `Sigla_UF` |
| `cobrade` | `cobrade` | `Cod_Cobrade` |
| `ibge` | `ibge` | `Cod_IBGE_Mun` |
| `regiao`, `descricao_tipologia`, `grupo_de_desastre` | iguais | iguais |

As outras ~60 colunas são detalhamento de danos (`DH_*`, `DM_*`, `DA_*`, `PEPL_*`,
`PEPR_*`) — irrelevantes para o Y.

Por haver divergência relevante, o pipeline foi **parado e reportado** antes de adaptar
o código (conforme a task), e as decisões abaixo foram confirmadas com a dupla.

---

## 3. Decisões tomadas

1. **Data do evento = `Data_Evento`** (não `Data_Registro`).
   Semanticamente é a data em que o desastre ocorreu — a que deve casar com a chuva
   diária do X. `Data_Registro` é data burocrática de cadastro no S2iD.
   - Impacto no dedup 2008–2022: `Data_Evento` = 2.659 vs `Data_Registro` = 2.675.

2. **Descarte das 88 linhas com `Data_Registro` em 2026.**
   São registros lançados em 2026 referentes a eventos anteriores (registro futuro ao
   evento) — irrelevantes para o Y. Universo de trabalho: 76.191 − 88 = **76.103**.

3. **Reutilizar a bridge existente** (`bridge_estacao_municipio.csv`, 141 estações /
   133 municípios). Não recriar o join espacial — a ponte estação→IBGE independe do Atlas.

---

## 4. Como o código foi feito

Código: **`src/data/atlas_consolidado.py`** (rodar com o Python do Anaconda, que tem
pandas/openpyxl: `/opt/anaconda3/bin/python src/data/atlas_consolidado.py`).

Fluxo:

1. **Carga** — lê a aba `Atlas Valores Originais`, normaliza os nomes de coluna para
   minúsculo/sem espaço (`c.strip().lower()`).

2. **Datas** — `Data_Evento` e `Data_Registro` já vêm como `datetime` do Excel; só se
   aplica `pd.to_datetime(..., errors="coerce")` por segurança.

3. **Descarte 2026** — remove linhas com `data_registro.dt.year == 2026` (as 88).

4. **Tipos das chaves** — `cobrade` e `ibge` → `Int64`; `regiao` normalizada para
   minúsculo em coluna auxiliar `regiao_l`.

5. **Construção do Y** (`build_y`): filtra `regiao == 'sudeste'` **E**
   `cobrade ∈ {12100, 12200, 12300}` **E** `ano(Data_Evento) ∈ [2008, 2022]`; remove
   `NaN` de `ibge`/`data`; **deduplica por `ibge × data`** (mesmo município/dia = 1 evento);
   marca `evento = 1`.

6. **Schema de saída idêntico ao antigo** — renomeia só as 3 colunas de texto
   (`protocolo_s2id→protocolo`, `nome_municipio→municipio`, `sigla_uf→uf`); `cobrade`,
   `ibge` e `data` já estão canônicas. Colunas finais:
   `protocolo, municipio, uf, data, cobrade, ibge, regiao, descricao_tipologia, grupo_de_desastre, evento`.
   Assim o `left join` futuro no painel estação×dia do X continua funcionando sem mudanças.

7. **Restrição a municípios com estação** — filtra o Y mantendo só `ibge` presentes no
   conjunto derivado da bridge → `y_eventos_estacoes.csv` (o entregável principal).

8. **Relatório** — tudo é escrito num buffer e salvo em
   `reports/relatorio_validacao_atlas.txt`, incluindo o comparativo antigo→novo, o
   potencial 2023–2025 e as duas análises adicionais (abaixo).

### Detalhe importante do código (bug corrigido durante a execução)
Ao renomear `cod_ibge_mun → ibge`, colidia com a coluna `ibge` já derivada em `Int64`
(idem `cobrade`). A correção foi **não** renomear as chaves (elas já estavam canônicas) e
renomear apenas as 3 colunas de texto.

### Saídas
- `data/processed/y_eventos_sudeste.csv` — 2.659 linhas
- `data/processed/y_eventos_estacoes.csv` — 401 linhas
- `reports/relatorio_validacao_atlas.txt`

---

## 5. Análises adicionais pedidas

### (a) Viés de dia-da-semana — `Data_Evento` vs `Data_Registro` (hidro-SE 2008–2022)

Mede a fração de eventos no fim de semana (esperado ≈ 28,6% = 2/7) e o *déficit relativo*.

| Data usada | Fim de semana observado | Déficit relativo |
|---|---|---|
| `Data_Registro` | 13,4% | **+53,0%** |
| `Data_Evento` | 17,2% | **+39,9%** |

**Conclusão:** o déficit de fim de semana **diminui** com `Data_Evento` (−13,1 p.p.) —
parte do viés era burocrático (registro concentrado em dia útil). Mas **não some**: sobra
um déficit real de ~40%, indicando subnotificação genuína de desastres hidrológicos no
fim de semana mesmo pela data do evento.

### (b) Quebra estrutural de 2014 (série anual hidro-SE dedup, `Data_Evento`)

Série 2008–2022: `238, 476, 303, 333, 271, 271, 37, 30, 110, 51, 100, 52, 118, 108, 161`.

- Média 2008–2013: **315,3/ano** → média 2014–2022: **85,2/ano** (queda **73%**).
- 2013→2014: 271 → 37 (**−86%**).

**Conclusão:** a quebra de 2014 **PERSISTE** por `Data_Evento` — não é artefato da data
de registro; é uma queda abrupta e sustentada na própria base.

---

## 6. Organização dos arquivos

### Repositório local (`~/tccfiles/`)
| Caminho | Conteúdo |
|---|---|
| `data/raw/BD_Atlas_1991_2025_v1.xlsx` | Atlas novo (canônico) |
| `data/processed/y_eventos_*.csv` | Y novo (fonte principal) |
| `data/archive/` | derivados antigos + `BD_Atlas_1991_2022.xlsx` (só local, não sobem) |
| `src/data/atlas_consolidado.py` | código do pipeline |
| `reports/relatorio_validacao_atlas.txt` | relatório da rodada |

### Google Drive (`TCC/`)
| Caminho | Conteúdo |
|---|---|
| `atlas_refresh_2026-07-15/` | resultados novos (2 CSV + relatório) |
| `dados_old/` | versão 403 obsoleta, renomeada `*_v403.*` + Atlas 1991-2022 |
| raiz da TCC | limpa (sem `y_eventos_*` nem relatório soltos) |

---

## 7. Como reproduzir

```bash
cd ~/tccfiles
/opt/anaconda3/bin/python src/data/atlas_consolidado.py
```

Parâmetros no topo do script: `ANO_INI=2008`, `ANO_FIM=2022`,
`COBRADE_HIDRO={12100,12200,12300}`. Para estender o X e capturar os positivos de
2023–2025, **não** basta mudar `ANO_FIM` aqui — precisa de decisão explícita da
dupla/orientadora (a extensão depende do X cobrir o período correspondente).
