"""Executa o projeto dbt (dbt/) sobre o mesmo arquivo DuckDB do pipeline.

Usa a API Python do dbt (dbtRunner), sem acessar a rede: o projeto não depende de pacotes do
dbt Hub. O caminho do banco é passado por variável de ambiente lida em dbt/profiles.yml.

As seeds vêm de ref/ (ou da pasta cfg.ref nos testes): antes de cada execução, os CSVs são
copiados para dbt/seeds/, uma pasta gerada e fora do Git.
"""

from __future__ import annotations

import os
import shutil
from contextlib import contextmanager

from .config import Config


class ErroDbt(Exception):
    """O dbt falhou (modelo com erro ou teste com severidade de erro)."""


@contextmanager
def _ambiente(cfg: Config):
    anterior = {k: os.environ.get(k) for k in ("SISMIGRA_DUCKDB", "DBT_SEND_ANONYMOUS_USAGE_STATS")}
    os.environ["SISMIGRA_DUCKDB"] = cfg.banco.resolve().as_posix()
    os.environ["DBT_SEND_ANONYMOUS_USAGE_STATS"] = "false"   # nada de rede
    try:
        yield
    finally:
        for k, v in anterior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def sincronizar_seeds(cfg: Config) -> None:
    """Copia ref/*.csv para dbt/seeds/ (recriada do zero, para não sobrar referência antiga)."""
    destino = cfg.dbt / "seeds"
    shutil.rmtree(destino, ignore_errors=True)
    destino.mkdir(parents=True)
    for csv in sorted(cfg.ref.glob("*.csv")):
        shutil.copyfile(csv, destino / csv.name)


def executar(cfg: Config, comando: str = "build", *args: str, silencioso: bool = False) -> None:
    """Roda `dbt <comando>` (padrão: build) e falha se algum nó der erro."""
    from dbt.cli.main import dbtRunner

    base = [*comando.split(), "--project-dir", str(cfg.dbt), "--profiles-dir", str(cfg.dbt)]
    if silencioso:
        base = ["--quiet", *base]
    sincronizar_seeds(cfg)
    with _ambiente(cfg):
        res = dbtRunner().invoke([*base, *args])
    if not res.success:
        falhas = []
        for r in getattr(res.result, "results", None) or []:
            if str(getattr(r, "status", "")) in ("error", "fail"):
                falhas.append(f"{r.node.name}: {r.message}")
        detalhe = ("\n  " + "\n  ".join(falhas)) if falhas else f" ({res.exception})"
        raise ErroDbt(f"dbt {comando} falhou:{detalhe}")
