"""Exporta o esquema estrela (modelos dbt do schema marts) para Parquet e CSV, só para uso interno.

Os CSVs saem com separador ';' e BOM UTF-8 para abrir direto no Excel em português.
Nada daqui pode ser publicado: a publicação usa só os agregados protegidos (divulgacao.py).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import duckdb

from .carga import lit
from .config import Config

TABELAS = [
    "fato_registro",
    "dim_tempo",
    "dim_pais",
    "dim_localidade",
    "dim_perfil",
    "dim_amparo",
    "dim_ocupacao",
    "amparo_descricao_ano",
]


def _prefixar_bom(caminho: Path) -> None:
    temp = caminho.with_suffix(".tmp")
    with caminho.open("rb") as src, temp.open("wb") as dst:
        dst.write(b"\xef\xbb\xbf")
        shutil.copyfileobj(src, dst, 8 * 1024 * 1024)
    temp.replace(caminho)


def executar(cfg: Config, con: duckdb.DuckDBPyConnection) -> dict:
    (cfg.ouro / "parquet").mkdir(parents=True, exist_ok=True)
    (cfg.ouro / "csv").mkdir(parents=True, exist_ok=True)
    contagens = {}
    for t in TABELAS:
        origem = f"marts.{t}"
        con.execute(f"COPY {origem} TO {lit((cfg.ouro / 'parquet' / f'{t}.parquet').as_posix())} (FORMAT parquet)")
        destino = cfg.ouro / "csv" / f"{t}.csv"
        con.execute(f"COPY {origem} TO {lit(destino.as_posix())} (HEADER, DELIMITER ';')")
        _prefixar_bom(destino)
        contagens[t] = con.execute(f"SELECT count(*) FROM {origem}").fetchone()[0]
    return contagens
