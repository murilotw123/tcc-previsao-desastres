# Previsão de Desastres Hidrológicos com Machine Learning — TCC

Projeto de ciência de dados desenvolvido como Trabalho de Conclusão de Curso (TCC).
O objetivo é construir um modelo capaz de **prever a ocorrência de desastres
hidrológicos (inundações, enxurradas e alagamentos) na região Sudeste do Brasil**
a partir de dados pluviométricos das estações automáticas do INMET e do registro
histórico de desastres do Atlas Digital de Desastres no Brasil.

---

## Dados

| Fonte | Conteúdo | Onde está |
|-------|----------|-----------|
| INMET | Pluviometria horária das estações automáticas | **Google Drive** (`TCC/INMET_consolidado3.csv`, 2,8 GB — grande demais para manter local) |
| Atlas Digital de Desastres (1991–2022) | Registros oficiais de desastres por município (COBRADE) | `data/raw/BD_Atlas_1991_2022.xlsx` |
| TOPODATA/INPE | Variáveis topográficas por município do Sudeste | `data/raw/topodata_sudeste_municipios.csv` |

**Recorte do projeto:** 2008–2022 (overlap entre a série das estações e o Atlas),
região Sudeste, COBRADEs hidrológicos `{12100, 12200, 12300}`.

> ⚠️ **Arquivos grandes NÃO ficam no GitHub nem nesta máquina** — a cópia
> canônica é a pasta compartilhada **TCC** do Google Drive (INMET consolidado,
> pluviometria Brasil 2025, versões antigas do pipeline em `export_tabelas_old`
> e `imputed_by_station_old/v2/v3`). O `.gitignore` bloqueia `data/raw/`,
> `data/archive/`, `*.parquet` e `models/`. Só vão para o git os arquivos
> pequenos: código, docs, metadados, tabela-alvo Y e relatórios.

## Estrutura do repositório

```
tccfiles/
├── README.md
├── requirements.txt
├── .gitignore
├── data/
│   ├── raw/            # dados originais (Drive; não versionados)
│   ├── metadata/       # metadados das estações, ponte estação↔município, exclusões
│   ├── processed/      # saídas do pipeline: Y de eventos + parquets imputados por estação
│   └── archive/        # versões antigas do pipeline (Drive; não versionadas)
├── docs/               # documentação metodológica (Semana 1 e 2), especificações de tarefas
├── notebooks/          # Jupyter notebooks de exploração e experimentos
├── src/                # código-fonte reutilizável (.py)
│   ├── data/           # coleta, limpeza e imputação
│   ├── features/       # criação e transformação de variáveis
│   └── models/         # treino, avaliação e previsão
├── models/             # modelos treinados salvos (não versionados)
└── reports/            # relatórios de imputação/validação e figuras
    └── figures/
```

## Código

- `src/data/processar_inmet.py` — consolida os CSVs anuais brutos do INMET
  (extrai os 8 campos do cabeçalho para colunas e concatena tudo).
- `src/data/atlas_consolidado.py` — pipeline da tabela-alvo Y (Atlas 1991–2025):
  filtra eventos hidro-SE, dedup por ibge×data, gera `y_eventos_*.csv`.
- `src/data/topodata_mosaico.py` — monta o mosaico GeoTIFF de declividade do
  Sudeste a partir dos rasters do TOPODATA.
- `src/features/merge_features_target.py` — cruza X (features diárias por município)
  com o Y por ibge×data → `dataset_modelagem_municipio.parquet` (rótulo evento 0/1).
- `src/features/comparar_versoes_features.py` — compara versões das features
  diárias (ex.: v3 vs v4) para escolher a canônica.
- `src/features/teste_sinal.py` — teste de sinal: separabilidade da precipitação
  entre dias de evento e dias normais (percentis, AUC, boxplots).
- `notebooks/01_extract_inmet.ipynb` — extração/consolidação da base INMET.
- `notebooks/02_extract_s2id.ipynb` — extração dos registros de desastres (S2iD/Atlas).
- `notebooks/TOPODATA_Sudeste.ipynb` — processamento das variáveis topográficas.

> A limpeza/imputação horária do INMET (pipeline DuckDB) foi feita em Colab da dupla
> (`TCC_AnaliseDuck.ipynb`, não versionado). O registro metodológico dessa etapa está
> em `docs/tratamento_dados_resumo.md` e `docs/guia_dataset_modelagem.md`.

## Pipeline (estado atual)

1. **Consolidação** da pluviometria do INMET (`src/data/processar_inmet.py` →
   `INMET_consolidado3.csv`, no Drive).
2. **Controle de qualidade e imputação por estação** — parquets por estação em
   `data/processed/imputed_by_station_final/` (142 estações); estações com falhas
   crônicas foram separadas em `imputed_by_station_excluidas_cronicas/`.
   Relatórios de cada rodada em `reports/imputation_report*.csv`.
3. **Metadados e exclusões** — `data/metadata/metadados_estacoes.csv` +
   `stations_exclude.csv` (estações com >30% de missing ou série curta;
   inclui a exclusão da estação C891/CRIOSFERA, na Antártida mas rotulada SP).
4. **Ponte estação ↔ município (IBGE)** — join espacial com a malha municipal,
   `data/metadata/bridge_estacao_municipio.csv` (141 estações mapeadas).
5. **Tabela-alvo (Y)** — eventos do Atlas filtrados por recorte:
   `data/processed/y_eventos_sudeste.csv` (todo o Sudeste, referência) e
   `data/processed/y_eventos_estacoes.csv` (**entregável**: só municípios com estação).
   Validação em `reports/relatorio_validacao_atlas.txt`.
   Especificação completa em `docs/TASK_atlas_consolidado.md`.
6. **Merge X + Y (tabela de modelagem)** — `src/features/merge_features_target.py`
   cruza as features diárias por município (`features_diarias_municipio_v4`, do Drive)
   com o Y por ibge×data → `data/processed/dataset_modelagem_municipio.parquet`
   (município-dia com rótulo `evento` 0/1). Relatório em
   `reports/relatorio_merge_modelagem.txt`; escolha da versão em
   `reports/comparacao_v3_v4.md`.
7. **Teste de sinal** — `src/features/teste_sinal.py`: a precipitação separa dias de
   evento de dias normais (AUC ≈ 0,82 para `precip_dia`). Resumo em
   `reports/teste_sinal.md`, figuras em `reports/figures/`.

## Como configurar o ambiente

```bash
git clone https://github.com/murilotw123/tcc-previsao-desastres.git
cd tcc-previsao-desastres

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
jupyter notebook
```

Depois de clonar, baixe os dados brutos da pasta **TCC** do Google Drive
compartilhado para `data/raw/` (a estrutura de pastas já existe no repo).

## Fluxo de trabalho da equipe

1. Sempre rode `git pull` antes de começar a mexer.
2. Trabalhem em notebooks/arquivos separados sempre que possível.
3. Para mudanças maiores, usem branches (`git checkout -b nome-da-tarefa`)
   e abram Pull Request para juntar o trabalho.
4. Nunca commitem arquivos de dados grandes — o `.gitignore` já bloqueia,
   mas confiram o `git status` antes do commit.


