"""Caminhos e parâmetros do pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Config:
    """Locais de entrada, saída e referência. Todos podem ser trocados (ex.: nos testes)."""

    entrada: Path = RAIZ / "data" / "landing"
    dados: Path = RAIZ / "data"
    ref: Path = RAIZ / "ref"
    sql: Path = RAIZ / "sql"
    relatorios: Path = RAIZ / "reports" / "qualidade"

    @property
    def bronze(self) -> Path:
        return self.dados / "bronze"

    @property
    def prata(self) -> Path:
        return self.dados / "silver"

    @property
    def ouro(self) -> Path:
        return self.dados / "gold"

    @property
    def manifesto(self) -> Path:
        return self.bronze / "manifest.json"

    def criar_pastas(self) -> None:
        for p in (self.entrada, self.bronze, self.prata, self.ouro, self.relatorios):
            p.mkdir(parents=True, exist_ok=True)


# Colunas que todo arquivo precisa ter (contrato de layout).
COLUNAS_COMUNS = [
    "DATAREGISTRO", "AMPARO", "AMPARO_DESCRICAO", "CLASSIFICACAO_REGISTRO", "DATAENTRADA",
    "UNIDADE_FED_RESIDENCIA", "MUNICIPIO_RESIDENCIA", "PAIS_NASCIMENTO", "PAIS_NACIONALIDADE",
    "CONTINENTE", "SEXO", "ESTADO_CIVIL", "PROFISSAO", "STATUS", "CLASSIFICACAO_REVISADA",
    "TIPOLOGIA_AMPAROS",
]
# A idade vem como faixa (2021 a 2025) ou como idade exata (2026). Uma das duas é obrigatória.
COLUNAS_IDADE = ["FAIXA_ETARIA", "IDADE"]
