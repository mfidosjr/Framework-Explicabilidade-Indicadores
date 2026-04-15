"""
data_loader.py — Utilitários de leitura e unificação de dados

Funções para leitura paralela dos arquivos RQUAL (por estado) e
carregamento das fontes IBGE. Extrai a lógica dos notebooks 01 e 03.
"""

from __future__ import annotations

import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# RQUAL
# ---------------------------------------------------------------------------

def _read_single_rqual(path: Path, engine: str = "calamine") -> pd.DataFrame:
    """Lê um único arquivo XLSX de RQUAL, adicionando coluna de rastreabilidade."""
    try:
        df = pd.read_excel(path, engine=engine, dtype_backend="pyarrow")
    except Exception:
        df = pd.read_excel(path, engine="openpyxl", dtype_backend="pyarrow")
    df["__arquivo_origem"] = path.name
    return df


def load_rqual_parallel(
    pasta: str | Path,
    padrao: str = "RQUAL_8ind-*.xlsx",
    max_workers: int = 8,
    engine: str = "calamine",
) -> pd.DataFrame:
    """
    Lê todos os arquivos XLSX de RQUAL em paralelo e retorna base unificada.

    Parâmetros
    ----------
    pasta : caminho para a pasta com os arquivos por estado
    padrao : glob para filtrar arquivos (padrão: "RQUAL_8ind-*.xlsx")
    max_workers : número de threads paralelas
    engine : engine de leitura Excel ("calamine" preferido, fallback "openpyxl")

    Retorna
    -------
    DataFrame unificado com coluna '__arquivo_origem' para rastreabilidade.
    """
    pasta = Path(pasta)
    arquivos = sorted(pasta.glob(padrao))
    if not arquivos:
        raise FileNotFoundError(f"Nenhum arquivo encontrado em '{pasta}' com padrão '{padrao}'")

    print(f"[RQUAL] {len(arquivos)} arquivos encontrados. Lendo em paralelo ({max_workers} workers)...")
    resultados: dict[str, pd.DataFrame] = {}
    erros: list[str] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = {executor.submit(_read_single_rqual, arq, engine): arq for arq in arquivos}
        for futuro in as_completed(futuros):
            arq = futuros[futuro]
            try:
                resultados[arq.name] = futuro.result()
            except Exception as exc:
                erros.append(f"{arq.name}: {exc}")

    if erros:
        warnings.warn(f"Erros ao ler {len(erros)} arquivo(s):\n" + "\n".join(erros))

    dfs = [resultados[a.name] for a in arquivos if a.name in resultados]
    base = pd.concat(dfs, ignore_index=True)

    n_dup = base.duplicated().sum()
    if n_dup:
        warnings.warn(f"[RQUAL] {n_dup} linhas duplicadas encontradas. Removendo.")
        base = base.drop_duplicates().reset_index(drop=True)

    print(f"[RQUAL] Base unificada: {base.shape[0]:,} linhas × {base.shape[1]} colunas")
    return base


# ---------------------------------------------------------------------------
# IBGE
# ---------------------------------------------------------------------------

def _normalizar_nome(serie: pd.Series) -> pd.Series:
    """Remove acentos e padroniza nomes de municípios para join."""
    import unicodedata
    return (
        serie.astype(str)
        .str.strip()
        .str.upper()
        .apply(lambda s: unicodedata.normalize("NFKD", s)
               .encode("ASCII", "ignore")
               .decode("ASCII"))
    )


def load_ibge_socioeconomico(
    arq_pib: str | Path,
    arq_pop: str | Path,
    arq_urb: str | Path,
    arq_idhm: str | Path,
    arq_latlon: Optional[str | Path] = None,
) -> pd.DataFrame:
    """
    Carrega e mescla as 4-5 fontes IBGE em um único DataFrame municipal.

    Fontes esperadas
    ----------------
    arq_pib   : PIB dos Municípios (IBGE)
    arq_pop   : Código município + nome + população + área + densidade
    arq_urb   : Taxa de urbanização por município
    arq_idhm  : IDHM Atlas Brasil 2010
    arq_latlon: (opcional) coordenadas geográficas; se None, usa geobr

    Chave de junção: 'cod_mun' (int 7 dígitos, código IBGE)

    Retorna
    -------
    DataFrame com 5.570 linhas (um por município) e colunas padronizadas.
    """
    # PIB
    pib = pd.read_excel(arq_pib, dtype={"Código do Município": str})
    pib = pib.rename(columns={
        "Código do Município": "cod_mun",
        "Produto Interno Bruto per capita,\na preços correntes\n(R$ 1,00)": "pib_per_capita",
        "Valor adicionado bruto da Agropecuária,\na preços correntes\n(R$ 1,00)": "pib_agropecuaria",
        "Valor adicionado bruto da Indústria,\na preços correntes\n(R$ 1,00)": "pib_industria",
        "Valor adicionado bruto dos Serviços,\na preços correntes\n(R$ 1,00)": "pib_servicos",
        "Produto Interno Bruto, \na preços correntes\n(R$ 1,00)": "pib_total",
    })
    pib["cod_mun"] = pib["cod_mun"].astype(str).str[:7].astype(int)
    pib_cols = ["cod_mun", "pib_total", "pib_per_capita", "pib_agropecuaria", "pib_industria", "pib_servicos"]
    pib = pib[[c for c in pib_cols if c in pib.columns]].dropna(subset=["cod_mun"])

    # População / Área / Densidade
    pop = pd.read_excel(arq_pop)
    pop.columns = pop.columns.str.strip()
    pop = pop.rename(columns=lambda c: c.lower().replace(" ", "_"))
    # normalizar nome da coluna cod_mun
    for alias in ["código_do_município", "codmun", "cod_municipio", "código_município"]:
        if alias in pop.columns:
            pop = pop.rename(columns={alias: "cod_mun"})
            break
    pop["cod_mun"] = pop["cod_mun"].astype(str).str[:7].astype(int)

    # Urbanização
    urb = pd.read_excel(arq_urb)
    urb.columns = urb.columns.str.strip()
    urb = urb.rename(columns=lambda c: c.lower().replace(" ", "_"))
    for alias in ["código_do_município", "codmun", "cod_municipio"]:
        if alias in urb.columns:
            urb = urb.rename(columns={alias: "cod_mun"})
            break
    urb["cod_mun"] = urb["cod_mun"].astype(str).str[:7].astype(int)

    # IDHM
    idhm = pd.read_excel(arq_idhm)
    idhm.columns = idhm.columns.str.strip()
    idhm = idhm.rename(columns=lambda c: c.lower().replace(" ", "_"))
    for alias in ["codmun7", "cod_mun", "código_do_município", "codmun"]:
        if alias in idhm.columns:
            idhm = idhm.rename(columns={alias: "cod_mun"})
            break
    idhm["cod_mun"] = idhm["cod_mun"].astype(str).str[:7].astype(int)
    if "idhm" not in idhm.columns:
        # tenta encontrar coluna com nome similar
        col_idhm = next((c for c in idhm.columns if "idhm" in c.lower()), None)
        if col_idhm:
            idhm = idhm.rename(columns={col_idhm: "idhm"})

    # Merge progressivo
    base = pib.merge(pop, on="cod_mun", how="outer")
    base = base.merge(urb, on="cod_mun", how="left", suffixes=("", "_urb"))
    base = base.merge(idhm[["cod_mun", "idhm"]], on="cod_mun", how="left")

    # Lat/Lon
    if arq_latlon is not None:
        latlon = pd.read_csv(arq_latlon)
        latlon.columns = latlon.columns.str.strip().str.lower()
        for alias in ["cod_mun", "codmun", "código_do_município"]:
            if alias in latlon.columns:
                latlon = latlon.rename(columns={alias: "cod_mun"})
                break
        latlon["cod_mun"] = latlon["cod_mun"].astype(str).str[:7].astype(int)
        base = base.merge(latlon[["cod_mun", "lat", "lon"]], on="cod_mun", how="left")
    else:
        warnings.warn("[IBGE] arq_latlon não fornecido. Use geobr para obter lat/lon.")

    print(f"[IBGE] Base socioeconômica: {base.shape[0]:,} municípios × {base.shape[1]} colunas")
    return base


# ---------------------------------------------------------------------------
# Parquet
# ---------------------------------------------------------------------------

def load_parquet(caminho: str | Path, **kwargs) -> pd.DataFrame:
    """Wrapper padronizado para leitura de Parquet com PyArrow."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho.resolve()}")
    df = pd.read_parquet(caminho, engine="pyarrow", **kwargs)
    print(f"[Parquet] {caminho.name}: {df.shape[0]:,} linhas × {df.shape[1]} colunas")
    return df
