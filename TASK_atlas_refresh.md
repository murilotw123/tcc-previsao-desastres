# TAREFA: Refazer o Y com o Atlas novo (BD_Atlas_1991_2025_v1.xlsx)

O Atlas usado até agora (`BD_Atlas_1991_2022.xlsx`) era o errado. O correto é
**`BD_Atlas_1991_2025_v1.xlsx`** (atenção ao sufixo `_v1`). Refazer o pipeline do Y
apontando pro arquivo novo, arquivando os derivados do Atlas antigo em `dados_old/`.

---

## 0. O que NÃO muda (não tocar, não arquivar)
- `bridge_estacao_municipio.csv` — ponte estação→IBGE, independe do Atlas. Continua válida.
- `metadados_estacoes.csv`, `stations_exclude.csv` (com a C891 incluída).
- O script `atlas_consolidado.py` — reaproveitar, só muda o input (e o que a Seção 2 pedir).

## 1. Arquivar em `dados_old/` (derivados do Atlas antigo)
Mover (não deletar): `y_eventos_sudeste.csv`, `y_eventos_estacoes.csv`,
`relatorio_validacao_atlas.txt`. O Atlas antigo já está lá.

## 2. Validar a estrutura do arquivo novo ANTES de rodar
Não assumir que é igual ao antigo. Conferir e reportar:
- Nomes das abas (`pd.ExcelFile(...).sheet_names`). A aba pode não se chamar mais
  "Atlas - Valores Originais".
- Colunas da aba principal vs. as esperadas:
  `protocolo, municipio, uf, data, cobrade, ibge, regiao, descricao_tipologia, grupo_de_desastre`.
- Formato da data (no antigo era M/D/AAAA americano — conferir se mantém).
- Total de linhas (antigo: 62.273; novo deve ser maior).
- Se algo divergir de forma relevante, PARAR e reportar antes de adaptar o código.

## 3. Re-rodar o pipeline do Y
Mesmos parâmetros (ANO_INI=2008, ANO_FIM=2022, COBRADE {12100,12200,12300},
Sudeste, dedup por ibge×data), reutilizando a bridge existente. Gerar:
- `y_eventos_sudeste.csv` (novo)
- `y_eventos_estacoes.csv` (novo)
- `relatorio_validacao_atlas.txt` (novo)

## 4. Relatório comparativo (antigo vs novo) — imprimir no final
- Registros totais na base: 62.273 → ?
- Eventos hidro-SE 2008–2022 dedup: 2.672 → ?
- Eventos em municípios com estação: 403 → ?
- Distribuição por ano lado a lado (2008–2022): sinalizar qualquer ano cuja contagem
  mudou (o Atlas novo pode ter revisado registros antigos, não só adicionado 2023+).
- Distribuição por tipologia: Enxurradas 156 / Inundações 150 / Alagamentos 101 → ?

## 5. Reportar separadamente: o potencial de 2023–2025
SEM incluir no Y final (o X só cobre até 2022-12-31), contar e reportar:
- Eventos hidro-SE em 2023, 2024, 2025 (dedup ibge×data);
- Quantos desses caem em municípios com estação (usar a bridge).
Isso alimenta a decisão de sync: vale estender o X até 2024/2025 pra capturar esses
positivos? (2023–2024 tiveram desastres grandes no Sudeste — pode ser muito positivo novo.)

## 6. Não fazer
- Não deletar nada (mover pra dados_old, sempre).
- Não estender ANO_FIM sem decisão explícita da dupla/orientadora.
- Não recriar a bridge (reutilizar a existente).
