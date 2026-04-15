"""
feature_engineering.py — Pipeline de seleção e engenharia de features

Funções reutilizáveis extraídas do notebook 04 (Seleção de feições):
- Imputação por UF (mediana) com fallback global
- Remoção de features por correlação
- Remoção iterativa por VIF
- Validação e log de outliers por z-score
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Imputação
# ---------------------------------------------------------------------------

def impute_by_uf(
    df: pd.DataFrame,
    colunas: list[str],
    uf_col: str = "uf_rqual",
    log_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Imputa valores ausentes usando mediana por UF; fallback: mediana global.

    Parâmetros
    ----------
    df       : DataFrame com as colunas a imputar
    colunas  : lista de colunas numéricas para imputar
    uf_col   : coluna com código da UF (para agrupamento)
    log_path : se fornecido, salva log CSV de auditoria da imputação

    Retorna
    -------
    DataFrame com NaNs imputados (cópia).
    """
    df = df.copy()

    # Substitui ±inf por NaN antes de imputar
    df[colunas] = df[colunas].replace([np.inf, -np.inf], np.nan)

    log_rows = []
    uf_disponivel = uf_col in df.columns

    for col in colunas:
        n_antes = int(df[col].isna().sum())
        pct_antes = round(100 * n_antes / len(df), 3)

        if n_antes == 0:
            log_rows.append({"variavel": col, "n_antes": 0, "n_depois": 0,
                             "pct_antes": 0.0, "pct_depois": 0.0, "metodo": "nenhum"})
            continue

        if uf_disponivel:
            df[col] = df.groupby(uf_col)[col].transform(
                lambda s: s.fillna(s.median())
            )

        # Fallback global para NaNs restantes
        restantes = int(df[col].isna().sum())
        if restantes:
            df[col] = df[col].fillna(df[col].median())

        n_depois = int(df[col].isna().sum())
        log_rows.append({
            "variavel": col,
            "n_antes": n_antes,
            "n_depois": n_depois,
            "pct_antes": pct_antes,
            "pct_depois": round(100 * n_depois / len(df), 3),
            "metodo": "mediana_uf+global" if uf_disponivel else "mediana_global",
        })

    log_df = pd.DataFrame(log_rows)

    if log_path is not None:
        log_df.to_csv(log_path, index=False)
        print(f"[Imputação] Log salvo em '{log_path}'")

    imputadas = log_df[log_df["n_antes"] > 0]
    if not imputadas.empty:
        print(f"[Imputação] {len(imputadas)} colunas imputadas | "
              f"Máx. % antes: {imputadas['pct_antes'].max():.1f}%")

    return df


# ---------------------------------------------------------------------------
# Correlação
# ---------------------------------------------------------------------------

def top_corr_pairs(df: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """Retorna os k pares de colunas mais correlacionados (valor absoluto)."""
    corr = df.corr().abs()
    np.fill_diagonal(corr.values, 0.0)
    pairs = (
        corr.stack()
        .reset_index()
        .rename(columns={"level_0": "var1", "level_1": "var2", 0: "rho"})
        .query("var1 < var2")
        .sort_values("rho", ascending=False)
        .head(k)
        .reset_index(drop=True)
    )
    return pairs


def remove_high_correlation(
    df: pd.DataFrame,
    keep_always: Optional[set[str]] = None,
    rho_thresh: float = 0.80,
    log_path: Optional[str | Path] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Remove features com correlação absoluta >= rho_thresh.

    Estratégia: para cada par correlacionado, remove a feature com
    maior correlação média com as demais (preserva 'keep_always').

    Parâmetros
    ----------
    df          : DataFrame apenas com features numéricas
    keep_always : conjunto de colunas que nunca serão removidas
    rho_thresh  : limiar de correlação (default 0.80)
    log_path    : salva log CSV se fornecido

    Retorna
    -------
    (df_podado, log_df)
    """
    keep_always = keep_always or set()
    cols = list(df.columns)
    removidas = []

    while True:
        corr = df[cols].corr().abs()
        np.fill_diagonal(corr.values, 0.0)
        max_corr = corr.max()
        worst_col = max_corr.idxmax()

        if max_corr[worst_col] < rho_thresh:
            break

        # par com maior correlação
        par_col = corr[worst_col].idxmax()

        # decidir qual remover (nunca remove keep_always)
        candidato = worst_col if worst_col not in keep_always else par_col
        if candidato in keep_always:
            # ambos são keep_always → não pode remover; interrompe
            break

        removidas.append({
            "variavel_removida": candidato,
            "correlacionada_com": par_col if candidato == worst_col else worst_col,
            "rho": round(float(max_corr[worst_col]), 4),
        })
        cols.remove(candidato)

    log_df = pd.DataFrame(removidas)

    if log_path is not None:
        log_df.to_csv(log_path, index=False)
        print(f"[Correlação] Log salvo em '{log_path}'")

    print(f"[Correlação] Removidas: {len(removidas)} | Restantes: {len(cols)}")
    return df[cols].copy(), log_df


# ---------------------------------------------------------------------------
# VIF
# ---------------------------------------------------------------------------

def compute_vif_table(X: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula VIF (Variance Inflation Factor) para todas as colunas de X.

    Usa statsmodels se disponível; caso contrário, fallback via sklearn (R²).
    Retorna DataFrame ordenado por VIF decrescente.
    """
    X = X.astype(float)

    if X.isna().any().any():
        raise ValueError("Há NaNs em X. Impute antes de calcular VIF.")
    if (X.std(ddof=1).abs() < 1e-12).any():
        cols_const = X.columns[(X.std(ddof=1).abs() < 1e-12)].tolist()
        raise ValueError(f"Colunas com desvio≈0 detectadas: {cols_const}")

    try:
        from statsmodels.stats.outliers_influence import variance_inflation_factor
        vif_values = [
            variance_inflation_factor(X.values, i)
            for i in range(X.shape[1])
        ]
    except ImportError:
        from sklearn.linear_model import LinearRegression
        vif_values = []
        for i, col in enumerate(X.columns):
            y = X.iloc[:, i].values
            Xr = X.drop(columns=col).values
            r2 = LinearRegression().fit(Xr, y).score(Xr, y)
            vif_values.append(1 / (1 - r2) if r2 < 1.0 else np.inf)

    return (
        pd.DataFrame({"variavel": X.columns, "VIF": vif_values})
        .sort_values("VIF", ascending=False)
        .reset_index(drop=True)
    )


def run_vif_iterative(
    df: pd.DataFrame,
    keep_always: Optional[set[str]] = None,
    vif_target: float = 5.0,
    vif_tol: float = 10.0,
    log_path: Optional[str | Path] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Remove features iterativamente até que todas tenham VIF <= vif_target.

    Preserva colunas em keep_always. Se a pior for keep_always mas VIF > vif_tol,
    tenta remover a segunda pior (se não for keep_always).

    Parâmetros
    ----------
    df         : DataFrame apenas com features numéricas (sem NaNs)
    keep_always: colunas nunca removíveis (ex.: indicadores RQUAL)
    vif_target : meta de VIF (default 5.0)
    vif_tol    : tolerância máxima para keep_always (default 10.0)
    log_path   : salva log CSV se fornecido

    Retorna
    -------
    (df_podado, log_df)
    """
    keep_always = keep_always or set()
    cols = list(df.columns)
    removidas = []
    iteracao = 0

    while True:
        iteracao += 1
        vif_tab = compute_vif_table(df[cols])
        worst = vif_tab.iloc[0]

        if worst["VIF"] <= vif_target or len(cols) <= 1:
            break

        candidato = worst["variavel"]

        if candidato not in keep_always:
            removidas.append({"iteracao": iteracao, "variavel": candidato,
                               "VIF": round(float(worst["VIF"]), 2)})
            cols.remove(candidato)
        elif worst["VIF"] > vif_tol and len(vif_tab) > 1:
            segundo = vif_tab.iloc[1]
            if segundo["variavel"] not in keep_always:
                removidas.append({"iteracao": iteracao, "variavel": segundo["variavel"],
                                   "VIF": round(float(segundo["VIF"]), 2),
                                   "nota": f"keep_always protegeu '{candidato}'"})
                cols.remove(segundo["variavel"])
            else:
                break  # ambos protegidos
        else:
            break  # keep_always abaixo do tolerável

    log_df = pd.DataFrame(removidas)

    if log_path is not None:
        log_df.to_csv(log_path, index=False)
        print(f"[VIF] Log salvo em '{log_path}'")

    vif_final = compute_vif_table(df[cols]).iloc[0]["VIF"]
    print(f"[VIF] Iterações: {iteracao} | Removidas: {len(removidas)} | "
          f"Restantes: {len(cols)} | VIF máx. final: {vif_final:.2f}")

    return df[cols].copy(), log_df


# ---------------------------------------------------------------------------
# Z-score / Outliers
# ---------------------------------------------------------------------------

def validate_zscore(
    df: pd.DataFrame,
    colunas: list[str],
    threshold: float = 4.0,
    log_path: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Valida outliers via z-score e retorna log de diagnóstico.

    Não remove outliers — apenas registra e informa. Para tratamento,
    use Winsorization ou Yeo-Johnson conforme notebook 04.

    Parâmetros
    ----------
    df        : DataFrame com as features
    colunas   : colunas numéricas a avaliar
    threshold : limiar de |z| para considerar outlier (default 4.0)
    log_path  : salva log CSV se fornecido

    Retorna
    -------
    log_df com colunas: variavel, n_outliers, pct_outliers, z_max, z_min
    """
    log_rows = []
    for col in colunas:
        s = df[col].dropna()
        std = s.std(ddof=1)
        if std == 0 or std is np.nan:
            continue
        z = (s - s.mean()) / std
        mask = z.abs() > threshold
        log_rows.append({
            "variavel": col,
            "n_outliers": int(mask.sum()),
            "pct_outliers": round(100 * mask.mean(), 3),
            "z_max": round(float(z.max()), 3),
            "z_min": round(float(z.min()), 3),
        })

    log_df = (
        pd.DataFrame(log_rows)
        .sort_values("pct_outliers", ascending=False)
        .reset_index(drop=True)
    )

    if log_path is not None:
        log_df.to_csv(log_path, index=False)
        print(f"[Z-score] Log salvo em '{log_path}'")

    n_com_outlier = (log_df["n_outliers"] > 0).sum()
    print(f"[Z-score] {n_com_outlier} variáveis com outliers |z| > {threshold} "
          f"(de {len(colunas)} avaliadas)")

    return log_df
