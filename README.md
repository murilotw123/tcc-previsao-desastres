# Previsão de Desastres Naturais

Projeto de ciência de dados desenvolvido como Trabalho de Conclusão de Curso (TCC).
O objetivo é construir um modelo capaz de **prever a ocorrência de desastres naturais**
a partir de dados históricos, climáticos e geográficos.

> **Personalize esta seção:** descreva qual desastre vocês vão prever (enchente,
> deslizamento, seca, queimada, etc.), a região de estudo e a pergunta central do trabalho.

---

## Objetivos

- **Geral:** desenvolver um modelo preditivo para [tipo de desastre] na região de [local].
- **Específicos:**
  - Coletar e tratar dados históricos de [fonte].
  - Realizar análise exploratória para identificar padrões e variáveis relevantes.
  - Treinar e comparar diferentes modelos de machine learning.
  - Avaliar o desempenho e discutir os resultados.

---

## Estrutura do projeto

```
tcc-previsao-desastres/
├── README.md               # este arquivo
├── requirements.txt        # bibliotecas necessárias
├── .gitignore              # arquivos que NÃO vão para o GitHub
├── data/
│   ├── raw/                # dados originais, nunca alterados manualmente
│   └── processed/          # dados já limpos e tratados
├── notebooks/              # Jupyter notebooks de exploração e experimentos
├── src/                    # código-fonte reutilizável (.py)
│   ├── data/               # scripts de coleta e limpeza de dados
│   ├── features/           # criação e transformação de variáveis
│   └── models/             # treino, avaliação e previsão
├── models/                 # modelos treinados salvos (.pkl, .joblib)
└── reports/
    └── figures/            # gráficos e imagens gerados para o relatório
```

**Regra importante:** os dados em `data/` NÃO são versionados no GitHub (veja o `.gitignore`).
Combine com a equipe de guardar os datasets em um local compartilhado (ex.: Google Drive)
e documente abaixo de onde baixá-los.

---

## Como configurar o ambiente

1. Clone o repositório:
   ```bash
   git clone https://github.com/SEU-USUARIO/tcc-previsao-desastres.git
   cd tcc-previsao-desastres
   ```

2. (Recomendado) Crie um ambiente virtual:
   ```bash
   python -m venv venv
   # Linux/Mac:
   source venv/bin/activate
   # Windows:
   venv\Scripts\activate
   ```

3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

4. Inicie o Jupyter para explorar os notebooks:
   ```bash
   jupyter notebook
   ```

---

## Fontes de dados

| Fonte | Descrição | Link |
|-------|-----------|------|
| EM-DAT | Base internacional de desastres | https://www.emdat.be |
| INMET | Dados meteorológicos do Brasil | https://portal.inmet.gov.br |
| INPE | Queimadas e dados de satélite | https://www.gov.br/inpe |
| NASA / NOAA | Dados climáticos e de satélite | — |

> Preencha esta tabela com as fontes que vocês realmente usarem e onde os arquivos
> estão guardados (link do Drive, etc.).

---

## Equipe

- [Nome 1] — [usuário GitHub]
- [Nome 2] — [usuário GitHub]

**Orientador(a):** [Nome]
**Instituição / Curso:** [preencher]

---

## Fluxo de trabalho da equipe

Para evitar conflitos ao trabalhar em dupla:

1. Sempre rode `git pull` antes de começar a mexer.
2. Trabalhem em notebooks/arquivos separados sempre que possível.
3. Para mudanças maiores, usem branches:
   ```bash
   git checkout -b nome-da-sua-tarefa
   ```
   e depois abram um Pull Request no GitHub para juntar o trabalho.
4. Façam `git push` ao terminar, com mensagens de commit claras.
