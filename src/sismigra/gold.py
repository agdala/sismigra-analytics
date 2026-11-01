"""Camada ouro: monta o esquema estrela (sql/gold.sql) e exporta Parquet e CSV."""

from __future__ import annotations

import shutil
from pathlib import Path

import duckdb

from .config import Config
from .silver import lit

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
    """Requer a tabela `prata` e as referências já carregadas na conexão (ver silver.executar)."""
    con.execute((cfg.sql / "gold.sql").read_text(encoding="utf-8"))
    (cfg.ouro / "parquet").mkdir(parents=True, exist_ok=True)
    (cfg.ouro / "csv").mkdir(parents=True, exist_ok=True)
    contagens = {}
    for t in TABELAS:
        con.execute(f"COPY {t} TO {lit((cfg.ouro / 'parquet' / f'{t}.parquet').as_posix())} (FORMAT parquet)")
        # CSV com separador ';' e BOM UTF-8 para abrir direto no Excel em português
        destino = cfg.ouro / "csv" / f"{t}.csv"
        con.execute(f"COPY {t} TO {lit(destino.as_posix())} (HEADER, DELIMITER ';')")
        _prefixar_bom(destino)
        contagens[t] = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    # Agregado do Looker Studio: vírgula como separador (padrão de importação do Looker)
    con.execute(
        f"COPY agregado_looker TO {lit((cfg.ouro / 'agregado_looker.csv').as_posix())} (HEADER, DELIMITER ',')"
    )
    contagens["agregado_looker"] = con.execute("SELECT count(*) FROM agregado_looker").fetchone()[0]
    return contagens
