"""Fixtures com dados sintéticos no layout real do SISMIGRA (não usam microdados)."""

from __future__ import annotations

import csv
import shutil
import zipfile
from pathlib import Path

import duckdb
import pytest

from sismigra import bronze, gold, quality, silver
from sismigra.config import RAIZ, Config

CAB_2025 = ("DATAREGISTRO;AMPARO;AMPARO_DESCRICAO;CLASSIFICACAO_REGISTRO;DATAENTRADA;UNIDADE_FED_RESIDENCIA;"
            "MUNICIPIO_RESIDENCIA;PAIS_NASCIMENTO;PAIS_NACIONALIDADE;CONTINENTE;FAIXA_ETARIA;SEXO;ESTADO_CIVIL;"
            "PROFISSAO;STATUS;CLASSIFICACAO_REVISADA;TIPOLOGIA_AMPAROS")
CAB_2026 = CAB_2025.replace("FAIXA_ETARIA", "IDADE")

PADRAO = {
    "DATAREGISTRO": "2025", "AMPARO": "290", "AMPARO_DESCRICAO": "290 - ART. 2. DECRETO 9.277/2018",
    "CLASSIFICACAO_REGISTRO": "Provisório", "DATAENTRADA": "2025", "UNIDADE_FED_RESIDENCIA": "RR",
    "MUNICIPIO_RESIDENCIA": "BOA VISTA", "PAIS_NASCIMENTO": "VENEZUELA", "PAIS_NACIONALIDADE": "VENEZUELA",
    "CONTINENTE": "AMÉRICA DO SUL", "FAIXA_ETARIA": "25 |-- 40 anos", "IDADE": "30", "SEXO": "Masculino",
    "ESTADO_CIVIL": "SOLTEIRO", "PROFISSAO": "ESTUDANTE", "STATUS": "Ativo",
    "CLASSIFICACAO_REVISADA": "NÃO APLICÁVEL", "TIPOLOGIA_AMPAROS": "NÃO APLICÁVEL",
}

# Cada linha: (marcador, alterações). O marcador vai em PROFISSAO para localizar a linha no teste.
LINHAS_2025 = [
    ("DUP", {}), ("DUP", {}),
    ("R01", {"DATAREGISTRO": "abc"}),
    ("R02", {"DATAREGISTRO": "2024"}),
    ("R03", {"AMPARO": ""}),
    ("ENTRADA_TRACO", {"DATAENTRADA": "--"}),
    ("ENTRADA_FUTURA", {"DATAENTRADA": "2030"}),
    ("ENTRADA_OK", {"DATAENTRADA": "2019"}),
    ("SEXO_ND", {"SEXO": "Nao Declarado"}),
    ("SEXO_TRACO", {"SEXO": "-"}),
    ("SP", {"UNIDADE_FED_RESIDENCIA": "SP", "MUNICIPIO_RESIDENCIA": "SÃO PAULO"}),
    ("APOSTROFO", {"UNIDADE_FED_RESIDENCIA": "SC", "MUNICIPIO_RESIDENCIA": "HERVAL DOESTE"}),
    ("EXCECAO", {"UNIDADE_FED_RESIDENCIA": "RJ", "MUNICIPIO_RESIDENCIA": "PARATI"}),
    ("SEM_MATCH", {"UNIDADE_FED_RESIDENCIA": "MT", "MUNICIPIO_RESIDENCIA": "JUREMA"}),
    ("NAO_ESPEC", {"MUNICIPIO_RESIDENCIA": "NÃO ESPECIFICADO"}),
    ("UF_TRACO", {"UNIDADE_FED_RESIDENCIA": "-", "MUNICIPIO_RESIDENCIA": "NÃO ESPECIFICADO"}),
    ("EC_UNDERSCORE", {"ESTADO_CIVIL": "SEPARADO_JUDICIALMENTE"}),
    ("EC_DESCONHECIDO", {"ESTADO_CIVIL": "DESCONHECIDO"}),
    ("KUAITE", {"PAIS_NACIONALIDADE": "KUAITE", "PAIS_NASCIMENTO": "KUAITE", "CONTINENTE": "ÁSIA"}),
    ("KUWEIT", {"PAIS_NACIONALIDADE": "KUWEIT", "PAIS_NASCIMENTO": "KUWEIT", "CONTINENTE": "ÁSIA"}),
    ("PAIS_TRACO", {"PAIS_NACIONALIDADE": "-"}),
    ("FAIXA_NE", {"FAIXA_ETARIA": "NÃO ESPECIFICADO"}),
    ("VENEZ_273", {"AMPARO": "273", "AMPARO_DESCRICAO": "273 - PORTARIA INTERMINISTERIAL N 19/2021",
                   "CLASSIFICACAO_REGISTRO": "Temporário", "TIPOLOGIA_AMPAROS": "ACOLHIDA VENEZUELANOS"}),
    ("CPLP_326", {"AMPARO": "326", "PAIS_NACIONALIDADE": "ANGOLA", "PAIS_NASCIMENTO": "ANGOLA"}),
]
LINHAS_2026 = [
    ("IDADE_30", {"IDADE": "30"}),
    ("IDADE_14", {"IDADE": "14"}),
    ("IDADE_15", {"IDADE": "15"}),
    ("IDADE_65", {"IDADE": "65"}),
    ("IDADE_NEG", {"IDADE": "-1974"}),
    ("IDADE_NULA", {"IDADE": ""}),
]
N_MALFORMADAS = 1


def _escrever_csv(caminho: Path, cab: str, linhas: list, ano: str, malformada: bool = False) -> None:
    cols = cab.split(";")
    with caminho.open("w", encoding="utf-8", newline="") as f:
        f.write(cab + "\n")
        for marcador, alt in linhas:
            reg = {**PADRAO, "DATAREGISTRO": ano, "PROFISSAO": marcador, **alt}
            f.write(";".join(reg[c] for c in cols) + "\n")
        if malformada:
            f.write("2025;290;faltam colunas\n")


@pytest.fixture(scope="session")
def ambiente(tmp_path_factory) -> Config:
    base = tmp_path_factory.mktemp("sismigra")
    ref = base / "ref"
    shutil.copytree(RAIZ / "ref", ref)
    with (ref / "fontes.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["arquivo_csv", "ano", "cobertura", "ano_completo", "url_origem", "distribuidor"])
        w.writerow(["teste_2025.csv", "2025", "jan-dez", "true", "https://exemplo.org/2025.zip", "Teste"])
        w.writerow(["teste_2026.csv", "2026", "jan-set", "false", "https://exemplo.org/2026.zip", "Teste"])
    landing = base / "landing"
    landing.mkdir()
    _escrever_csv(base / "teste_2025.csv", CAB_2025, LINHAS_2025, "2025", malformada=True)
    with zipfile.ZipFile(landing / "teste_2025.zip", "w") as z:
        z.write(base / "teste_2025.csv", "pasta/teste_2025.csv")
    _escrever_csv(landing / "teste_2026.csv", CAB_2026, LINHAS_2026, "2026")
    return Config(entrada=landing, dados=base / "data", ref=ref, sql=RAIZ / "sql", relatorios=base / "reports")


@pytest.fixture(scope="session")
def execucao(ambiente):
    """Roda o pipeline inteiro uma vez sobre os dados sintéticos e mantém a conexão aberta."""
    manifesto = bronze.executar(ambiente)
    con = duckdb.connect()
    res = silver.executar(ambiente, manifesto, con)
    contagens = gold.executar(ambiente, con)
    rel = quality.calcular(con, res["leitura"])
    quality.escrever(ambiente, rel)
    yield {"cfg": ambiente, "con": con, "manifesto": manifesto, "contagens": contagens, "qualidade": rel}
    con.close()


@pytest.fixture
def linha(execucao):
    """Devolve a linha da prata pelo marcador (coluna profissao)."""
    con = execucao["con"]

    def _buscar(marcador: str) -> dict:
        cur = con.execute("SELECT * FROM prata WHERE profissao = ?", [marcador])
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        assert len(rows) == 1, f"esperada 1 linha para {marcador}, encontradas {len(rows)}"
        return dict(zip(cols, rows[0]))

    return _buscar
