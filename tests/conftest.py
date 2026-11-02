"""Fixtures com dados sintéticos no layout real do SISMIGRA (não usam microdados).

O fixture `execucao` roda o pipeline completo uma vez: bronze, carga, dbt build (com todos os
testes do dbt), exportação, controle de divulgação e relatório de qualidade.
"""

from __future__ import annotations

import hashlib

import pytest

from sismigra import pipeline
from sismigra.config import RAIZ
from sismigra.sinteticos import CAB_2025, CAB_2026, LINHAS_2025, LINHAS_2026, N_MALFORMADAS, preparar  # noqa: F401


def hash_ref() -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((RAIZ / "ref").glob("*.csv"))}


@pytest.fixture(scope="session")
def ref_antes():
    """Hashes de ref/ antes de qualquer execução do dbt (para provar que o dbt não altera a fonte)."""
    return hash_ref()


@pytest.fixture(scope="session")
def ambiente(tmp_path_factory):
    return preparar(tmp_path_factory.mktemp("sismigra"))


@pytest.fixture(scope="session")
def execucao(ambiente, ref_antes):
    """Roda o pipeline inteiro uma vez sobre os dados sintéticos e mantém a conexão aberta."""
    res = pipeline.executar(ambiente, silencioso_dbt=True)
    con = res["con"]
    yield {"cfg": ambiente, "con": con, "manifesto": res["manifesto"], "contagens": res["contagens"],
           "divulgacao": res["divulgacao"], "qualidade": res["qualidade"]}
    con.close()


@pytest.fixture
def linha(execucao):
    """Devolve a linha da prata (int_registros_enriquecidos) pelo marcador (coluna profissao)."""
    con = execucao["con"]

    def _buscar(marcador: str) -> dict:
        cur = con.execute("SELECT * FROM int_registros_enriquecidos WHERE profissao = ?", [marcador])
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        assert len(rows) == 1, f"esperada 1 linha para {marcador}, encontradas {len(rows)}"
        return dict(zip(cols, rows[0]))

    return _buscar
