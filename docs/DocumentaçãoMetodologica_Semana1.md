# Documentação Metodológica — Construção da Variável-Alvo (Y) a partir do Atlas Digital de Desastres e Investigação de sua Granularidade

**Responsável:** Pessoa B — Construção do Y (Atlas) e investigação de granularidade
**Fonte de dados:** Atlas Digital de Desastres no Brasil (BD 1991–2022) e metadados das estações automáticas do INMET, região Sudeste
**Ferramentas:** Python, pandas, geopandas, geobr
**Data:** 05/07/2026

Este documento consolida a construção da tabela-alvo (Y) de eventos pluviométricos — ocorrências de desastres hidrológicos por município × dia — restrita ao recorte do projeto e aos municípios que possuem estação meteorológica, e a investigação da granularidade real do banco do Atlas. Serve como material de apoio para a redação da seção de metodologia e para eventuais perguntas de banca sobre a variável dependente do modelo.

---

## 1. Objetivo da etapa

Extrair do Atlas Digital de Desastres a variável-alvo do modelo de classificação binária (ocorrência/não ocorrência de evento pluviométrico extremo por município e dia), garantindo:

- Recorte reproduzível por tipologia (COBRADE), região e janela temporal;
- Vínculo espacial explícito e auditável entre cada estação meteorológica do X e o município do Y;
- Caracterização honesta da granularidade e das limitações do registro oficial de desastres, que condicionam o que o modelo pode e não pode aprender.

A saída principal (`y_eventos_estacoes.csv`) contém apenas os dias **com** evento. Os dias sem evento (classe negativa) nascem na etapa seguinte, ao cruzar com o painel estação × dia do X.

---

## 2. Fontes e definições do recorte

| Parâmetro | Valor | Justificativa |
| --- | --- | --- |
| Fonte do Y | BD_Atlas_1991_2022.xlsx, aba "Atlas - Valores Originais" (62.273 registros) | Base oficial consolidada dos registros do S2ID |
| Tipologias (COBRADE) | 12100 Inundações, 12200 Enxurradas, 12300 Alagamentos | Grupo hidrológico, diretamente associável a precipitação |
| Região | Sudeste (MG, ES, RJ, SP) | Escopo do projeto |
| Janela temporal | 2008–2022 | Overlap com o X: o painel de estações inicia em 2008-01-01 (ver pendência na Seção 8) |
| Malha municipal | IBGE 2022, via pacote `geobr` | Compatível com o código IBGE de 7 dígitos usado pelo Atlas |
| Chave de junção | `ibge` (7 dígitos) × `data` (dia) | Granularidade nativa do Atlas (ver Seção 5) |

---

## 3. Construção da ponte estação → município

O Y é registrado por município; o X, por estação. A ponte entre os dois foi feita por **join espacial**, nunca por nome:

1. Partiu-se das **142 estações** com `status_final = "incluida"` no metadado consolidado da etapa de tratamento de ausentes (152 brutas; as estações da lista `stations_exclude.csv` já constavam com status de exclusão).
2. Cada estação (ponto lat/long, EPSG:4326) foi atribuída ao polígono municipal da malha IBGE 2022 em que está contida (`sjoin`, predicado *within*).
3. Para pontos fora de qualquer polígono, previu-se fallback por município mais próximo (`sjoin_nearest`, distância em metros via EPSG:5880), com a distância registrada na coluna `distancia_check` para auditoria.
4. O nome do município encontrado foi comparado ao nome da estação **apenas como conferência** — 26 divergências foram listadas e revisadas manualmente; todas correspondem a sub-localidades (ex.: "SÃO PAULO - INTERLAGOS") ou a estações fisicamente situadas em município vizinho ao que lhes dá nome (ex.: SOROCABA → Iperó; MONTE VERDE → Camanducaia; TRÊS MARIAS → São Gonçalo do Abaeté), casos esperados e legítimos.

**Resultado:** 141 estações mapeadas para **133 municípios distintos** (mais de uma estação pode cair no mesmo município, ex.: capitais). A ponte está materializada em `bridge_estacao_municipio.csv`.

---

## 4. Achado 1 — Estação da Antártida rotulada como São Paulo (C891 CRIOSFERA)

### 4.1 Sintoma observado

No join espacial, uma única estação não caiu em nenhum polígono municipal e foi capturada pelo fallback `sjoin_nearest` — atribuída a Cananéia-SP a uma distância de **6.637 km**.

### 4.2 Investigação e causa raiz

A estação **C891 CRIOSFERA** consta no metadado do INMET com UF = SP e região SE, mas com coordenadas lat −84,0 / lon −79,5: trata-se do módulo científico **Criosfera 1, na Antártida**, vinculado administrativamente a São Paulo pelo INMET. O rótulo administrativo (UF/região) não corresponde à localização física — mais um caso, junto aos achados da etapa de ausentes, de que **metadados oficiais não podem ser aceitos sem validação**.

### 4.3 Correção

Sem a checagem de distância, a estação injetaria os 4 eventos de Cananéia no Y indevidamente. Adotou-se a regra: *match por `sjoin_nearest` com distância > 10 km implica estação fora da região de estudo e descarte da ponte*. A C891 foi descartada e adicionada ao `stations_exclude.csv` (que passou a conter S122, A560, A767, C891). A estação também possuía apenas 1 ano de série válida (2020) e qualidade geral "baixa".

> **Impacto cruzado:** a exclusão reduz o dataset de estações de 142 para **141** — a contagem reportada na Documentação da Semana 2 (Pessoa A) deve ser atualizada em conjunto.

---

## 5. Achado 2 — Granularidade real do Atlas

Investigação conduzida sobre a base completa (62.273 registros) e sobre o recorte hidrológico do Sudeste 1991–2022 (5.177 registros), **antes** de qualquer deduplicação.

### 5.1 Granularidade temporal: o dia, sem duração

- O campo `data` carrega apenas o dia (hora sempre 00:00) e **não existe campo de data-fim ou duração**: cada registro é um desastre reconhecido em uma data única. Eventos que se estenderam por vários dias aparecem como um único dia — o Y, portanto, marca o **início/registro** do evento, não sua extensão.
- `protocolo` é único em 100% da base (62.273/62.273): não há relatos duplicados do mesmo protocolo.
- Registros sucessivos no mesmo município são eventos genuinamente distintos: apenas 0,5% ocorrem a ≤ 3 dias do anterior (1,5% a ≤ 7 dias) — não há indício de um mesmo evento "espalhado" em dias consecutivos.

### 5.2 Granularidade espacial: o município inteiro

O evento é georreferenciado apenas pelo código IBGE de 7 dígitos (100% dos registros do recorte). Não há coordenada do ponto atingido: chuvas localizadas em municípios extensos (ex.: Campos dos Goytacazes, 4.032 km²) são indistinguíveis de eventos generalizados. A resolução máxima possível para o modelo é, portanto, **município × dia** — o que valida a chave de junção pactuada.

### 5.3 Multiplicidade por dia

No recorte hidrológico do Sudeste, 50 pares município × dia (de 5.125) têm mais de um registro (máximo 3) — em geral, tipologias distintas decretadas no mesmo dia (ex.: enxurrada + alagamento). Como a variável-alvo é binária (houve/não houve evento pluviométrico), esses casos foram **deduplicados para uma única linha** por `ibge × data` (45 duplicatas removidas no recorte final), decisão sem perda de informação para o problema formulado.

---

## 6. Achado 3 — Vieses do registro administrativo

Dois padrões do Atlas refletem o processo burocrático de registro, não o fenômeno físico, e devem ser declarados como limitação:

1. **Viés de dia da semana:** sábados e domingos concentram cerca de metade dos registros dos dias úteis (428 e 472 eventos vs. 726–972 de segunda a sexta, no recorte hidro-SE). Precipitação não tem sazonalidade semanal — a `data` reflete parcialmente o dia do decreto/registro. As janelas de precipitação acumulada de 24/48/72h previstas para a engenharia de atributos (Semana 2) absorvem parte desse deslocamento de ±1–2 dias.
2. **Quebra estrutural na série:** o volume anual de eventos no Sudeste cai de 238–478 (2008–2013) para 37–110 (2014–2019), recuperando-se parcialmente depois. A magnitude e a abruptez são incompatíveis com variabilidade climática e coincidem com mudanças nas regras/sistemática de registro do S2ID — ou seja, a densidade da classe positiva do Y **não é estacionária** por razões administrativas. Isso reforça a necessidade de validação temporal (time series split) em vez de validação aleatória.

Distribuição anual dos eventos (município × dia, hidro-SE):

| Ano | 2008 | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Sudeste | 238 | 478 | 307 | 335 | 273 | 273 | 37 | 30 | 110 | 52 | 104 | 53 | 122 | 114 | 146 |
| Municípios c/ estação | 35 | 66 | 49 | 47 | 30 | 52 | 3 | 4 | 12 | 4 | 21 | 8 | 23 | 24 | 29 |

---

## 7. Resultado consolidado

| Métrica | Valor |
| --- | --- |
| Registros na aba "Atlas - Valores Originais" | 62.273 |
| Registros região Sudeste | 13.686 |
| + COBRADE hidrológico (12100/12200/12300) | 5.177 |
| + janela 2008–2022 | 2.717 |
| Eventos após deduplicação `ibge × data` (**y_eventos_sudeste.csv**) | **2.672** |
| Estações na ponte / municípios com estação | 141 / 133 |
| Eventos retidos em municípios com estação (**y_eventos_estacoes.csv**) | **403 (15,1%)** |
| Distribuição por tipologia (retidos) | Enxurradas 156, Inundações 150, Alagamentos 101 |

Nenhum ano do recorte ficou com zero eventos retidos. Arquivos gerados: `bridge_estacao_municipio.csv`, `y_eventos_sudeste.csv`, `y_eventos_estacoes.csv`, `relatorio_validacao_atlas.txt`.

---

## 8. Limitações e pendências de sincronização

1. **Cobertura do Y limitada à rede de estações:** apenas 15,1% dos eventos do Sudeste ocorrem em municípios com estação — o modelo descreve municípios instrumentados, não o Sudeste inteiro. Generalização espacial deve ser discutida como tal.
2. **O Y marca o registro, não o fenômeno:** granularidade dia × município, sem duração nem localização intra-municipal (Seção 5), com vieses administrativos (Seção 6).
3. **PENDÊNCIA — recorte temporal:** o plano de trabalho menciona 2012–2022; esta etapa e a Documentação da Semana 2 usam **2008–2022** (início do painel de estações). Com 2012–2022 restariam ~1.260 eventos no Sudeste, capturando quase integralmente o "vale" administrativo de 2014–2019; 2008–2022 dobra a classe positiva. Decisão a travar em conjunto; o filtro é trivial de aplicar a posteriori.
4. **PENDÊNCIA — contagem de estações:** exclusão da C891 (Seção 4) reduz o dataset final de 142 para 141 estações; atualizar a documentação da Pessoa A.

---

## 9. Sugestões de tabelas e gráficos para o TCC

- **Mapa:** municípios do Sudeste coloridos por presença de estação + pontos das 141 estações — evidencia a cobertura espacial (limitação 1).
- **Gráfico de barras por ano:** eventos no Sudeste vs. eventos retidos (tabela da Seção 6) — evidencia a quebra estrutural de 2014.
- **Gráfico de barras por dia da semana:** contagem de eventos — evidencia o viés administrativo de registro.
- **Tabela:** as 26 divergências nome-estação vs. município do join espacial — transparência do método da ponte.

---

## 10. Referências

BRASIL. Ministério da Integração Nacional. **Instrução Normativa nº 1, de 24 de agosto de 2012** — institui a Codificação Brasileira de Desastres (COBRADE). Diário Oficial da União, Brasília, 2012.

CEPED/UFSC — Centro Universitário de Estudos e Pesquisas sobre Desastres. **Atlas Digital de Desastres no Brasil.** Brasília: MIDR, 2023. Disponível em: https://atlasdigital.mdr.gov.br/.

PEREIRA, Rafael H. M.; GONÇALVES, Caio Nogueira et al. **geobr: Download Official Spatial Data Sets of Brazil.** IPEA, 2019. Disponível em: https://github.com/ipeaGIT/geobr.

IBGE — Instituto Brasileiro de Geografia e Estatística. **Malha Municipal Digital da Federação, edição 2022.** Rio de Janeiro: IBGE, 2022.
