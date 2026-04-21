# CLAUDE.md — Framework Explicabilidade Indicadores

## O que é este projeto

Framework analítico para segmentar e explicar os **5.570 municípios brasileiros** por qualidade de serviços de telecomunicações, cruzando os indicadores RQUAL (Anatel) com dados socioeconômicos e geográficos do IBGE.

**Domínio:** Telecomunicações / Políticas públicas / Ciência de dados  
**Idioma do projeto:** Português brasileiro  
**Linguagem:** Python 3.10+ em Jupyter Notebooks  
**Caminho local:** `/Users/marcofidos/GitHub/Framework-Explicabilidade-Indicadores/`

---

## Estrutura do repositório

```
Framework-Explicabilidade-Indicadores/
├── CLAUDE.md                        ← este arquivo
├── README.md                        ← visão geral / artigo de pesquisa
├── requirements.txt                 ← dependências do ambiente
│
├── data/
│   ├── raw/
│   │   ├── rqual/                   ← 12 XLSX RQUAL por estado
│   │   └── ibge/                    ← XLSXs/JSONs IBGE (PIB, pop, IDHM, etc.)
│   ├── interim/                     ← parquets intermediários do pipeline
│   ├── output/                      ← CSVs de artefatos finais citados nos artigos
│   └── logs/                        ← CSVs de auditoria por fase
│
├── notebooks/                       ← 11 notebooks (01–11), planos
├── figures/                         ← 30+ figuras PNG geradas pelo pipeline
├── models/                          ← kmeans_model.pkl, scaler_final.pkl, config JSON
├── docs/                            ← manual RQUAL (Anatel) e glossário
│
└── src/                             ← módulos Python reutilizáveis
    ├── data_loader.py
    ├── feature_engineering.py
    └── clustering.py
```

---

## Pipeline de execução (ordem)

| Passo | Notebook | Input | Output |
|-------|----------|-------|--------|
| 1 | `notebooks/01-Leitura e união de todos os estados.ipynb` | 12 XLSX em `data/raw/rqual/` | `data/interim/base_RQUAL_unificada.parquet` (5.96M linhas) |
| 2 | `notebooks/02-Análise, Seleção e Preparação de ano base.ipynb` | `data/interim/base_RQUAL_unificada.parquet` | RQUAL filtrado para 2022 |
| 3 | `notebooks/03-Agregacao_Dados_Socio-Economicos1_PATCHED.ipynb` | XLSXs em `data/raw/ibge/` | `data/interim/base_socioeconomica_completa.xlsx` |
| 4 | `notebooks/04-Integracao e Analise de Variaveis RQUAL+SocioEc.ipynb` | RQUAL 2022 + IBGE | `data/interim/rqual_2022_consolidado_clean.parquet` |
| 5 | `notebooks/05-Seleção de feicoes.ipynb` | `data/interim/rqual_2022_consolidado_clean.parquet` | `data/interim/rqual_2022_feats_reduzidas.parquet` |
| 6 | `notebooks/06-Kmeans.ipynb` | `data/interim/rqual_2022_feats_reduzidas.parquet` | `data/interim/rqual_2022_clusterizado.parquet` + modelos em `models/` |
| 7 | `notebooks/07-Interpretacao_Clusters.ipynb` | `data/interim/rqual_2022_clusterizado.parquet` | Figuras, `data/output/tabela_resumo_clusters.csv` |
| 8 | `notebooks/08-UMAP_HDBSCAN_LOF.ipynb` | `data/interim/rqual_2022_clusterizado.parquet` | `data/interim/rqual_2022_clusterizado_v2.parquet`, `data/output/municipios_excepcionais_lof.csv` |
| 9 | `notebooks/09-Comparacao_Achados_HDBSCAN_vs_LOF.ipynb` | `data/interim/rqual_2022_clusterizado_v2.parquet` | `data/output/comparacao_achados_hdbscan_lof.csv` |
| 10 | `notebooks/10-SHAP_Explicabilidade_Clusters.ipynb` | `data/interim/rqual_2022_clusterizado.parquet` | `data/output/shap_importancia_por_cluster.csv`, `shap_explicacoes_municipios.csv`, `shap_matrix_completa.csv` |
| 11 | `notebooks/11-Invisibilidade_Media_Matched_Pairs.ipynb` | `data/interim/rqual_2022_clusterizado.csv` + SHAPs | `data/output/iv_invisibilidade_municipios.csv`, `matched_pairs_intracluster.csv` |

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
| `base_RQUAL_unificada.parquet` | `data/interim/` | RQUAL nacional unificado |
| `rqual_2022_consolidado_clean.parquet` | `data/interim/` | Base integrada RQUAL+IBGE 2022 |
| `rqual_2022_feats_reduzidas.parquet` | `data/interim/` | Features selecionadas para clustering |
| `rqual_2022_clusterizado.parquet` | `data/interim/` | Resultado K-Means K=5 + HDBSCAN original (v1) |
| `rqual_2022_clusterizado_v2.parquet` | `data/interim/` | Base enriquecida com UMAP (umap_x/y), LOF (lof_score, lof_outlier) |
| `municipios_excepcionais_lof.csv` | `data/output/` | ~559 municípios excepcionais identificados pelo LOF (10% por cluster) |
| `comparacao_achados_hdbscan_lof.csv` | `data/output/` | 763 municípios excepcionais (HDBSCAN ∪ LOF, com tipo) |
| `tabela_resumo_clusters.csv` | `data/output/` | Perfil médio por cluster |
| `shap_importancia_por_cluster.csv` | `data/output/` | Importância SHAP feature × cluster (16 × 5) |
| `shap_explicacoes_municipios.csv` | `data/output/` | Feature dominante + \|SHAP\| por município (5.570 linhas) |
| `shap_matrix_completa.csv` | `data/output/` | Matriz completa de valores SHAP (5.570 × 16) |
| `iv_invisibilidade_municipios.csv` | `data/output/` | Índice IV de invisibilidade à média (5.570 municípios) |
| `matched_pairs_intracluster.csv` | `data/output/` | 4.033 pares matched (contexto similar, desfecho divergente) |
| `kmeans_model.pkl` | `models/` | Modelo K-Means serializado |
| `scaler_final.pkl` | `models/` | RobustScaler serializado |
| `kmeans_metricas_por_K.csv` | `data/output/` | Métricas (silhouette, calinski, etc.) por K |
| `kmeans_escolha_config.json` | `models/` | Configuração reproduzível do clustering |

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
- Logs de auditoria: CSVs em `data/logs/`
- Modelos serializados: **pickle** (`.pkl`) em `models/`
- Nomes de colunas: snake_case em português (ex: `tx_urbanizacao`, `pib_per_capita`)

---

## Notas para o Claude

- Este projeto é **em português**; mantenha variáveis, comentários e documentação em português
- Os notebooks são a fonte da verdade para a lógica; `src/` contém versões modulares dessas funções
- Ao modificar o pipeline, preserve os logs de auditoria CSV em `data/logs/` — são rastreabilidade intencional
- O K ótimo para K-Means foi determinado empiricamente como **K=5** (silhouette=0.831); mudanças nesse valor devem ser justificadas com métricas
- **HDBSCAN direto nas features (20D) produz 96.3% de ruído** — não usar. Ver NB08 para alternativas documentadas
- Método adotado para identificação de municípios excepcionais: **LOF** (Local Outlier Factor), aplicado por cluster com `n_neighbors=20, contamination=0.10`
- UMAP 2D (`umap_x`, `umap_y`) gerado em NB08 para visualização exploratória; usar `data/interim/rqual_2022_clusterizado_v2.parquet` quando precisar dessas colunas
- **Índice de Invisibilidade à Média (IV)** calculado em NB11: `IV_i = Σ w_cj · |z_ij - z̄_cj|` com pesos SHAP normalizados por cluster
- Dados brutos grandes (>10 MB) não são commitados via Git padrão — o repositório usa **Git LFS**
- Caminhos internos dos notebooks usam `../data/...` e `../figures/...` relativo à pasta `notebooks/`
