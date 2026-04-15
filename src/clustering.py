"""
clustering.py — Utilitários de clustering (K-Means + HDBSCAN)

Funções reutilizáveis extraídas do notebook 05:
- Avaliação de K-Means para range de K com múltiplas métricas
- Seleção de K ótimo via rank ponderado
- Aplicação de HDBSCAN dentro de cada macro-cluster
- Serialização de artefatos (modelo, scaler, config)
"""

from __future__ import annotations

import json
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.preprocessing import RobustScaler, StandardScaler


# ---------------------------------------------------------------------------
# Avaliação de K
# ---------------------------------------------------------------------------

@dataclass
class KMetrics:
    k: int
    inertia: float
    silhouette: float
    calinski: float
    davies: float


def evaluate_kmeans_range(
    X: np.ndarray,
    k_min: int = 2,
    k_max: int = 12,
    n_init: int = 25,
    max_iter: int = 500,
    random_state: int = 42,
    verbose: bool = True,
) -> pd.DataFrame:
    """
    Avalia K-Means para cada K em [k_min, k_max] e retorna tabela de métricas.

    Métricas calculadas:
    - Inércia (SSE within-cluster)
    - Silhouette score (quanto maior, melhor)
    - Calinski-Harabasz index (quanto maior, melhor)
    - Davies-Bouldin index (quanto menor, melhor)

    Parâmetros
    ----------
    X            : array numpy (n_samples × n_features), já escalonado
    k_min/k_max  : range de K a testar
    n_init       : inicializações por K
    max_iter     : iterações máximas por rodada
    random_state : semente para reprodutibilidade
    verbose      : imprime progresso

    Retorna
    -------
    DataFrame com uma linha por K e colunas: k, inertia, silhouette, calinski, davies
    """
    resultados: list[KMetrics] = []

    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, n_init=n_init, max_iter=max_iter,
                    random_state=random_state)
        labels = km.fit_predict(X)

        m = KMetrics(
            k=k,
            inertia=float(km.inertia_),
            silhouette=float(silhouette_score(X, labels, sample_size=min(5000, len(X)),
                                              random_state=random_state)),
            calinski=float(calinski_harabasz_score(X, labels)),
            davies=float(davies_bouldin_score(X, labels)),
        )
        resultados.append(m)

        if verbose:
            print(f"  K={k:2d} | Inércia={m.inertia:,.0f} | "
                  f"Silhouette={m.silhouette:.3f} | "
                  f"Calinski={m.calinski:,.1f} | Davies={m.davies:.3f}")

    return pd.DataFrame([asdict(r) for r in resultados])


# ---------------------------------------------------------------------------
# Seleção de K ótimo
# ---------------------------------------------------------------------------

def choose_best_k(
    metricas: pd.DataFrame,
    pesos: Optional[dict[str, float]] = None,
) -> int:
    """
    Seleciona K ótimo via rank ponderado das métricas.

    Estratégia de ranking:
    - silhouette e calinski: rank crescente do maior para o menor (maior = melhor)
    - davies e inertia: rank crescente do menor para o maior (menor = melhor)
    - score final = soma ponderada dos ranks; K com menor score é o melhor

    Parâmetros
    ----------
    metricas : DataFrame retornado por evaluate_kmeans_range()
    pesos    : pesos por métrica (default: silhouette 0.4, calinski 0.3,
               davies 0.2, inertia 0.1)

    Retorna
    -------
    K ótimo (int)
    """
    pesos = pesos or {
        "silhouette": 0.4,
        "calinski": 0.3,
        "davies": 0.2,
        "inertia": 0.1,
    }

    df = metricas.copy()

    # Rank: silhouette e calinski — maior é melhor (rank_desc)
    df["rank_silhouette"] = df["silhouette"].rank(ascending=False)
    df["rank_calinski"] = df["calinski"].rank(ascending=False)
    # Rank: davies e inertia — menor é melhor (rank_asc)
    df["rank_davies"] = df["davies"].rank(ascending=True)
    df["rank_inertia"] = df["inertia"].rank(ascending=True)

    df["score_ponderado"] = (
        pesos["silhouette"] * df["rank_silhouette"]
        + pesos["calinski"] * df["rank_calinski"]
        + pesos["davies"] * df["rank_davies"]
        + pesos["inertia"] * df["rank_inertia"]
    )

    melhor = df.loc[df["score_ponderado"].idxmin()]
    k_otimo = int(melhor["k"])
    print(f"[KMeans] K ótimo selecionado: K={k_otimo} "
          f"(score ponderado={melhor['score_ponderado']:.3f}, "
          f"silhouette={melhor['silhouette']:.3f})")
    return k_otimo


# ---------------------------------------------------------------------------
# Escalonamento
# ---------------------------------------------------------------------------

def fit_scaler(
    X: np.ndarray | pd.DataFrame,
    frac_outliers: float = 0.02,
    threshold_robust: float = 0.02,
) -> tuple[np.ndarray, RobustScaler | StandardScaler]:
    """
    Seleciona e ajusta scaler automaticamente.

    Usa RobustScaler se frac_outliers >= threshold_robust (default 2%),
    caso contrário StandardScaler.

    Retorna
    -------
    (X_scaled, scaler_ajustado)
    """
    if frac_outliers >= threshold_robust:
        scaler = RobustScaler()
        tipo = "RobustScaler"
    else:
        scaler = StandardScaler()
        tipo = "StandardScaler"

    X_arr = X.values if isinstance(X, pd.DataFrame) else X
    X_scaled = scaler.fit_transform(X_arr)
    print(f"[Scaler] {tipo} ajustado | shape: {X_scaled.shape}")
    return X_scaled, scaler


# ---------------------------------------------------------------------------
# HDBSCAN por cluster
# ---------------------------------------------------------------------------

def run_hdbscan_per_cluster(
    df: pd.DataFrame,
    X_scaled: np.ndarray,
    label_col: str = "cluster_kmeans",
    min_cluster_size: int = 30,
    min_samples: int = 5,
) -> pd.DataFrame:
    """
    Aplica HDBSCAN dentro de cada macro-cluster K-Means.

    Gera coluna 'cluster_hdbscan' com label composto:
    '{cluster_kmeans}_{sub_cluster}' (ex: '0_1', '0_2', '1_0').
    Municípios classificados como ruído recebem sufixo '_noise'.

    Parâmetros
    ----------
    df               : DataFrame com coluna label_col (labels K-Means)
    X_scaled         : array escalonado correspondente às linhas de df
    label_col        : nome da coluna com labels K-Means
    min_cluster_size : parâmetro HDBSCAN
    min_samples      : parâmetro HDBSCAN

    Retorna
    -------
    df com coluna 'cluster_hdbscan' adicionada (cópia)
    """
    try:
        import hdbscan as hdbscan_lib
    except ImportError:
        raise ImportError("Instale hdbscan: pip install hdbscan")

    df = df.copy()
    df["cluster_hdbscan"] = ""

    for macro in sorted(df[label_col].unique()):
        mask = (df[label_col] == macro).values
        X_sub = X_scaled[mask]

        if len(X_sub) < min_cluster_size:
            df.loc[mask, "cluster_hdbscan"] = f"{macro}_0"
            continue

        clf = hdbscan_lib.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
        )
        sub_labels = clf.fit_predict(X_sub)

        labels_str = np.where(
            sub_labels == -1,
            f"{macro}_noise",
            [f"{macro}_{s}" for s in sub_labels],
        )
        df.loc[mask, "cluster_hdbscan"] = labels_str

        n_sub = len(set(sub_labels) - {-1})
        n_noise = int((sub_labels == -1).sum())
        print(f"  Cluster K={macro}: {len(X_sub)} municípios → "
              f"{n_sub} sub-clusters HDBSCAN | {n_noise} ruído")

    return df


# ---------------------------------------------------------------------------
# Serialização de artefatos
# ---------------------------------------------------------------------------

def save_clustering_artifacts(
    model: KMeans,
    scaler: RobustScaler | StandardScaler,
    metricas: pd.DataFrame,
    k_escolhido: int,
    pasta: str | Path = ".",
    prefixo: str = "",
) -> None:
    """
    Salva modelo, scaler, métricas e config de clustering na pasta indicada.

    Arquivos gerados:
    - {prefixo}kmeans_model.pkl
    - {prefixo}scaler_final.pkl
    - {prefixo}kmeans_metricas_por_K.csv
    - {prefixo}kmeans_escolha_config.json

    Parâmetros
    ----------
    model       : KMeans treinado
    scaler      : scaler ajustado
    metricas    : DataFrame de métricas por K
    k_escolhido : K selecionado
    pasta       : diretório de saída
    prefixo     : prefixo opcional para os nomes de arquivo
    """
    import joblib

    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)

    p = prefixo
    joblib.dump(model, pasta / f"{p}kmeans_model.pkl")
    joblib.dump(scaler, pasta / f"{p}scaler_final.pkl")
    metricas.to_csv(pasta / f"{p}kmeans_metricas_por_K.csv", index=False)

    config = {
        "k_escolhido": k_escolhido,
        "k_range": [int(metricas["k"].min()), int(metricas["k"].max())],
        "n_init": int(getattr(model, "n_init", 25)),
        "max_iter": int(getattr(model, "max_iter", 500)),
        "random_state": int(getattr(model, "random_state", 42)),
        "scaler": type(scaler).__name__,
        "silhouette_final": round(
            float(metricas.loc[metricas["k"] == k_escolhido, "silhouette"].values[0]), 4
        ),
    }
    with open(pasta / f"{p}kmeans_escolha_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"[Artefatos] Salvos em '{pasta}':")
    for nome in [f"{p}kmeans_model.pkl", f"{p}scaler_final.pkl",
                 f"{p}kmeans_metricas_por_K.csv", f"{p}kmeans_escolha_config.json"]:
        print(f"  - {nome}")
