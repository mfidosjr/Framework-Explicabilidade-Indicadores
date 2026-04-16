# CLAUDE.md — Framework Explicabilidade Indicadores

## O que é este projeto

Framework analítico para segmentar e explicar os **5.570 municípios brasileiros** por qualidade de serviços de telecomunicações, cruzando os indicadores RQUAL (Anatel) com dados socioeconômicos e geográficos do IBGE.

**Domínio:** Telecomunicações / Políticas públicas / Ciência de dados  
**Idioma do projeto:** Português brasileiro  
**Linguagem:** Python 3.10+ em Jupyter Notebooks

---

## Estrutura do repositório

```
Framework-Explicabilidade-Indicadores/
├── CLAUDE.md                        ← este arquivo
├── README.md                        ← visão geral para humanos
├── requirements.txt                 ← dependências do ambiente
│
├── 0-Fonte de Dados/
│   ├── IBGE/RAW/                    ← dados brutos IBGE + notebook de agregação
│   └── RQUAL/XLSX/                  ← dados brutos RQUAL (12 estados) + notebooks
│
├── 1-Base Integrada - RQUAL+SocioEconomicos/   ← join RQUAL + IBGE
├── 2-FeatureSelection/              ← seleção e engenharia de features
├── 3-KMeans+HDBSCAN/               ← clustering e análise
│
├── src/                             ← módulos Python reutilizáveis
│   ├── data_loader.py               ← leitura/unificação de dados
│   ├── feature_engineering.py       ← pipeline de feature selection
│   └── clustering.py                ← utilitários de clustering
│
└── Documentacao/                    ← manual RQUAL (Anatel) e glossário
```

---

## Pipeline de execução (ordem)

| Passo | Notebook | Input | Output |
|-------|----------|-------|--------|
| 1 | `0-Fonte de Dados/RQUAL/XLSX/01-Leitura e união de todos os estados.ipynb` | 12 arquivos XLSX por estado | `base_RQUAL_unificada.parquet` (5.96M linhas) |
| 2 | `0-Fonte de Dados/RQUAL/XLSX/02-Análise, Seleção e Preparação de ano base.ipynb` | `base_RQUAL_unificada.parquet` | RQUAL filtrado para 2022 |
| 3 | `0-Fonte de Dados/IBGE/RAW/1-Agregacao_Dados_Socio-Economicos1_PATCHED.ipynb` | XLSXs IBGE (PIB, pop, IDHM, etc.) | `base_socioeconomica_completa.xlsx` |
| 4 | `1-Base Integrada.../03-Integracao e Analise de Variaveis RQUAL+SocioEc.ipynb` | RQUAL 2022 + IBGE | `rqual_2022_consolidado_clean.parquet` |
| 5 | `2-FeatureSelection/04-Seleção de feicoes.ipynb` | `rqual_2022_consolidado_clean.parquet` | `rqual_2022_feats_reduzidas.parquet` |
| 6 | `3-KMeans+HDBSCAN/05-Kmeans.ipynb` | `rqual_2022_feats_reduzidas.parquet` | `rqual_2022_clusterizado.parquet` + modelos `.pkl` |
| 7 | `3-KMeans+HDBSCAN/06-Interpretacao_Clusters.ipynb` | `rqual_2022_clusterizado.parquet` | Tabelas interpretativas, figuras, `tabela_resumo_clusters.csv` |
| 8 | `3-KMeans+HDBSCAN/07-UMAP_HDBSCAN_LOF.ipynb` | `rqual_2022_clusterizado.parquet` | `rqual_2022_clusterizado_v2.parquet`, `municipios_excepcionais_lof.csv` |

---

## Dados e variáveis principais

### Indicadores RQUAL (Anatel)
- `IND2` — Taxa de Reclamações
- `IND4` — Taxa de Atendimento
- `IND5` — Taxa de Solução no Prazo
- `IND8` — Disponibilidade do Serviço
- `IND9` — Velocidade de Download
- `INF1` — Infraestrutura (cobertura)
- `INF4-DL` / `INF4-UP` — Throughput download/upload

### Variáveis socioeconômicas (IBGE)
- `pib_per_capita`, `pib_agropecuaria`, `pib_industria`, `pib_servicos`
- `pop_total`, `densidade`, `area_km2`, `tx_urbanizacao`
- `idhm` (Atlas Brasil 2010)
- `lat`, `lon` (coordenadas geográficas)
- Dummies regionais (Norte, Nordeste, Centro-Oeste, Sul/Sudeste)

### Chave de junção: `cod_mun` (código IBGE do município, 7 dígitos)

---

## Artefatos gerados pelo pipeline

| Arquivo | Local | Descrição |
|---------|-------|-----------|
| `base_RQUAL_unificada.parquet` | `0-Fonte de Dados/RQUAL/XLSX/` | RQUAL nacional unificado |
| `rqual_2022_consolidado_clean.parquet` | `1-Base Integrada.../` | Base integrada RQUAL+IBGE 2022 |
| `rqual_2022_feats_reduzidas.parquet` | `2-FeatureSelection/` | Features selecionadas para clustering |
| `rqual_2022_clusterizado.parquet` | `3-KMeans+HDBSCAN/` | Resultado K-Means K=5 + HDBSCAN original (v1) |
| `rqual_2022_clusterizado_v2.parquet` | `3-KMeans+HDBSCAN/` | Base enriquecida com UMAP (umap_x/y), LOF (lof_score, lof_outlier) |
| `municipios_excepcionais_lof.csv` | `3-KMeans+HDBSCAN/` | ~557 municípios excepcionais identificados pelo LOF (10% por cluster) |
| `kmeans_model.pkl` | `3-KMeans+HDBSCAN/` | Modelo K-Means serializado |
| `scaler_final.pkl` | `3-KMeans+HDBSCAN/` | RobustScaler serializado |
| `kmeans_metricas_por_K.csv` | `3-KMeans+HDBSCAN/` | Métricas (silhouette, calinski, etc.) por K |
| `kmeans_escolha_config.json` | `3-KMeans+HDBSCAN/` | Configuração reproduzível do clustering |

---

## Módulos Python (`src/`)

### `src/data_loader.py`
- `load_rqual_parallel()` — lê arquivos XLSX de estados em paralelo
- `load_ibge_socioeconomico()` — carrega e mescla fontes IBGE
- `load_parquet()` — wrapper padronizado para leitura de Parquet

### `src/feature_engineering.py`
- `impute_knn()` — imputação KNN para indicadores com missings
- `remove_high_correlation()` — poda de features correlacionadas (threshold ρ ≥ 0.8)
- `run_vif_iterative()` — remoção iterativa por VIF (multicolinearidade)
- `validate_zscore()` — validação e log de outliers por z-score

### `src/clustering.py`
- `evaluate_kmeans_range()` — avalia K-Means para range de K, retorna métricas
- `choose_best_k()` — seleciona K ótimo via rank ponderado
- `run_hdbscan_per_cluster()` — aplica HDBSCAN dentro de cada macro-cluster
- `save_clustering_artifacts()` — serializa modelo, scaler e config

---

## Convenções

- Codificação de municípios: sempre `cod_mun` (int 7 dígitos, ex: `5300108`)
- Formato de dados primário: **Parquet** (via PyArrow)
- Logs de auditoria: CSVs em subpastas `logs/` de cada fase
- Modelos serializados: **pickle** (`.pkl`) na pasta da fase correspondente
- Nomes de colunas: snake_case em português (ex: `tx_urbanizacao`, `pib_per_capita`)

---

## Notas para o Claude

- Este projeto é **em português**; mantenha variáveis, comentários e documentação em português
- Os notebooks são a fonte da verdade para a lógica; `src/` contém versões modulares dessas funções
- Ao modificar o pipeline, preserve os logs de auditoria CSV — são rastreabilidade intencional
- O K ótimo para K-Means foi determinado empiricamente como **K=5** (silhouette=0.831); mudanças nesse valor devem ser justificadas com métricas
- **HDBSCAN direto nas features (20D) produz 96.3% de ruído** — não usar. Ver NB07 para alternativas documentadas
- Método adotado para identificação de municípios excepcionais: **LOF** (Local Outlier Factor), aplicado por cluster com `n_neighbors=20, contamination=0.10`
- UMAP 2D (`umap_x`, `umap_y`) gerado em NB07 para visualização exploratória; usar `rqual_2022_clusterizado_v2.parquet` quando precisar dessas colunas
- Dados brutos grandes (>10 MB) não são commitados via Git padrão — o repositório usa **Git LFS**
