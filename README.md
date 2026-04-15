# Framework de Explicabilidade de Indicadores de Qualidade de Telecomunicações

Framework analítico para segmentação e explicabilidade de municípios brasileiros com base em indicadores de qualidade de serviços de telecomunicações (RQUAL/Anatel) cruzados com dados socioeconômicos e geográficos do IBGE.

## Objetivo

Identificar padrões e agrupamentos entre os **5.570 municípios brasileiros** combinando:
- **Indicadores RQUAL** (Anatel): 8 indicadores de qualidade de telecomunicações
- **Dados IBGE**: PIB, população, densidade, urbanização, IDHM, coordenadas geográficas

O resultado é uma segmentação hierárquica (K-Means → HDBSCAN) que permite interpretar o contexto socioeconômico e territorial associado à qualidade do serviço de telecomunicações em cada município.

---

## Resultados: 5 perfis de municípios

O modelo identificou **5 clusters** com características distintas de qualidade e contexto socioeconômico:

| Cluster | Municípios | Perfil |
|---------|-----------|--------|
| **C0 — Urbano-Avançado** | 216 (3,9%) | Alto PIB, alto IDHM, excelente upload — Sul/Sudeste |
| **C1 — Intermediário** | 3.054 (54,8%) | Desempenho médio nacional — padrão de referência |
| **C2 — Nordeste Periférico** | 2.057 (36,9%) | Infraestrutura existe, mas SLA fraco — Nordeste |
| **C3 — Norte/Amazônico** | 216 (3,9%) | Pior atendimento e resolução — municípios remotos |
| **C4 — Capitais/Destaques** | 27 (0,5%) | Benchmark nacional — 1 município por UF |

### Perfil médio por cluster (z-scores)

![Heatmap de perfil dos clusters](3-KMeans+HDBSCAN/fig_perfil_clusters_heatmap.png)

O heatmap mostra os valores médios padronizados (z-score) de cada cluster nos indicadores RQUAL e nas variáveis socioeconômicas do IBGE. Valores positivos (verde) indicam desempenho acima da média nacional; negativos (vermelho), abaixo.

**Destaques:**
- **C3 (Norte/Amazônico)** apresenta IND4 = −1,70σ e IND5 = −2,09σ — os piores índices de atendimento e resolução de todo o país
- **C4 (Capitais)** lidera em densidade demográfica (+2,06σ), PIB industrial (+1,99σ) e IDHM (+1,63σ)
- **C0 (Urbano-Avançado)** se destaca em throughput de upload (+1,24σ) e velocidade de download (+0,54σ)

---

### Comparação dos indicadores RQUAL por cluster

![Radar dos clusters](3-KMeans+HDBSCAN/fig_radar_clusters.png)

O radar evidencia a separação entre os clusters: C3 (vermelho) afunda em IND4 e IND5, enquanto C0 e C4 (azul e roxo) dominam em INF4-UP e IND9.

---

### Composição regional

![Distribuição regional por cluster](3-KMeans+HDBSCAN/fig_distribuicao_regional.png)

A segmentação reflete fortemente a estrutura regional do Brasil:
- **C0** é 67% Sudeste
- **C1** é 48% Sudeste + 38% Sul
- **C2** é 84% Nordeste
- **C3** é 68% Norte
- **C4** distribui-se por todas as regiões (1 capital por UF)

---

### Distribuição dos indicadores por cluster

![Boxplots dos indicadores](3-KMeans+HDBSCAN/fig_boxplot_indicadores.png)

---

## Interpretação dos clusters

### C0 — Urbano-Avançado (216 municípios)
Municípios com maior desenvolvimento socioeconômico e melhor infraestrutura de telecom. Concentrados em SP, MG, RJ, RS e PR. A qualidade do serviço acompanha o nível de renda e urbanização: alta taxa de resolução no prazo, poucas reclamações e throughput de upload excepcionalmente elevado.

### C1 — Intermediário (3.054 municípios)
O cluster da "maioria silenciosa" — municípios com serviços adequados, sem problemas críticos. Representa o padrão de referência para políticas de manutenção de qualidade. Dominado por Sul e Sudeste, com desempenho próximo da média nacional em todos os indicadores.

### C2 — Nordeste Periférico (2.057 municípios)
A infraestrutura de telecomunicações chegou (INF1 acima da média), mas a qualidade operacional é inferior: taxa de resolução de problemas no prazo (IND5) abaixo da média e mais reclamações (IND2). Reflete o desafio de expansão sem maturidade operacional. PIB per capita e IDHM significativamente abaixo da média.

### C3 — Norte/Amazônico (216 municípios)
Municípios de **alta vulnerabilidade** de telecomunicações. Municípios imensos (área +1,89σ), rurais (+1,12σ) e com economia primária (+0,79σ no VAB agropecuário) criam barreiras severas à qualidade. IND5 = −2,09σ: o prazo de resolução de problemas é crítico. **Prioridade máxima para políticas regulatórias.**

### C4 — Capitais/Destaques (27 municípios)
Exatamente 1 município por UF — as capitais estaduais. Representam o benchmark de qualidade: maior densidade (+2,06σ), maior upload (+1,38σ) e menor taxa de reclamações (−0,68σ). Servem como referência do que é tecnicamente possível quando há investimento e densidade econômica suficientes.

---

## Implicações para políticas públicas

| Eixo | Clusters-alvo | Problema | Indicadores-alvo |
|------|--------------|----------|-----------------|
| **Expansão de Qualidade** | C3 — Norte/Amazônico | SLA crítico em municípios remotos | IND4, IND5 |
| **Maturidade Operacional** | C2 — Nordeste | Rede existe, atendimento falha | IND5, IND2 |
| **Manutenção e Benchmark** | C0, C4 | Replicar boas práticas | INF4-UP, IND8 |

---

## Pipeline de execução

```
Dados Brutos (RQUAL + IBGE)
        ↓
    [Fase 0] Leitura e Unificação (01, 02, 03)
        ↓
    [Fase 1] Integração RQUAL + IBGE (04)
        ↓
    [Fase 2] Feature Selection (05)
        ↓
    [Fase 3] Clustering K-Means + HDBSCAN (06)
        ↓
    [Fase 4] Interpretação e Visualização (07)
        ↓
    Base Clusterizada (rqual_2022_clusterizado.parquet)
```

Execute os notebooks na ordem numérica:

| # | Notebook | Fase |
|---|----------|------|
| 01 | `0-Fonte de Dados/RQUAL/XLSX/01-Leitura e união de todos os estados.ipynb` | Unificação RQUAL |
| 02 | `0-Fonte de Dados/RQUAL/XLSX/02-Análise, Seleção e Preparação de ano base.ipynb` | Filtro RQUAL 2022 |
| 03 | `0-Fonte de Dados/IBGE/RAW/1-Agregacao_Dados_Socio-Economicos1_PATCHED.ipynb` | Agregação IBGE |
| 04 | `1-Base Integrada - RQUAL+SocioEconomicos/03-Integracao e Analise de Variaveis RQUAL+SocioEc.ipynb` | Integração |
| 05 | `2-FeatureSelection/04-Seleção de feicoes.ipynb` | Feature Selection |
| 06 | `3-KMeans+HDBSCAN/05-Kmeans.ipynb` | Clustering |
| 07 | `3-KMeans+HDBSCAN/06-Interpretacao_Clusters.ipynb` | Interpretação |

---

## Instalação

```bash
git clone <repo-url>
cd Framework-Explicabilidade-Indicadores
pip install -r requirements.txt
```

> Os dados brutos (`.xlsx` grandes) são gerenciados via **Git LFS**. Execute `git lfs pull` após o clone.

---

## Dados

### Fontes

| Fonte | Provedor | Cobertura | Variáveis principais |
|-------|----------|-----------|---------------------|
| RQUAL | Anatel (dados abertos) | Todos os estados, 2022 | IND2, IND4, IND5, IND8, IND9, INF1, INF4-DL, INF4-UP |
| PIB Municipal | IBGE | 5.570 municípios, 2021 | PIB total, per capita, setorial |
| Censo | IBGE | 5.570 municípios, 2022 | População, área, densidade |
| Urbanização | IBGE | 5.570 municípios, 2022 | Taxa de urbanização |
| IDHM | PNUD/Atlas Brasil | 5.570 municípios, 2010 | IDH Municipal |

### Indicadores RQUAL

| Indicador | Descrição | Interpretação |
|-----------|-----------|---------------|
| IND2 | Taxa de Reclamações | Menor = melhor |
| IND4 | Taxa de Atendimento | Maior = melhor |
| IND5 | Taxa de Solução no Prazo | Maior = melhor |
| IND8 | Disponibilidade do Serviço | Maior = melhor |
| IND9 | Velocidade de Download | Maior = melhor |
| INF1 | Cobertura/Infraestrutura | Maior = melhor |
| INF4-UP | Throughput Upload | Maior = melhor |

### Artefatos principais

| Arquivo | Descrição |
|---------|-----------|
| `base_RQUAL_unificada.parquet` | RQUAL nacional (5,96M linhas × 19 colunas) |
| `rqual_2022_consolidado_clean.parquet` | Base integrada RQUAL+IBGE, ano 2022 |
| `rqual_2022_feats_reduzidas.parquet` | Features selecionadas (20 variáveis) |
| `rqual_2022_clusterizado.parquet` | Resultado final com labels de cluster |
| `kmeans_model.pkl` | Modelo K-Means treinado (K=5) |
| `scaler_final.pkl` | RobustScaler ajustado |
| `tabela_resumo_clusters.csv` | Perfil médio por cluster |

---

## Módulos Python

Funções reutilizáveis extraídas dos notebooks estão em `src/`:

```
src/
├── data_loader.py          # Leitura paralela de dados brutos
├── feature_engineering.py  # Pipeline de seleção de features
└── clustering.py           # Avaliação e execução de clustering
```

---

## Documentação técnica

- `Documentacao/RQUALCDUST10112022.pdf` — Manual técnico RQUAL (Anatel)
- `Documentacao/Glossario_de_Termos_Indicadores de Qualidade dos Serviços RQUAL_V2.odt` — Glossário de termos

## Tecnologias

- Python 3.10+ · pandas · numpy · scipy
- scikit-learn (K-Means, métricas de clustering)
- hdbscan · umap-learn
- pyarrow (Parquet) · openpyxl
- matplotlib · seaborn
- Jupyter Notebooks
