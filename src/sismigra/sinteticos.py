"""Dados sintéticos no layout real do SISMIGRA, para testes e CI (não usam microdados).

Cada linha tem um marcador na coluna PROFISSAO que identifica a regra que ela exercita.
`preparar(pasta)` monta uma pasta de entrada (um ZIP de 2025 com uma linha malformada e um CSV
de 2026 com IDADE), uma cópia de ref/ com fontes.csv apontando para esses arquivos, e devolve a
Config correspondente.

Uso no CI:
  python -m sismigra.sinteticos PASTA          # prepara e roda o pipeline completo (inclui dbt build)
  python -m sismigra.sinteticos PASTA --docs   # idem e gera o site do dbt docs (dbt/target/static_index.html)
"""

from __future__ import annotations

import csv
import shutil
import sys
import zipfile
from pathlib import Path

from .config import RAIZ, Config

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
    # 6 registros com o mesmo perfil: formam uma célula >= 5 no agregado (não deve ser alterada)
    *[(f"GRUPO{i}", {"UNIDADE_FED_RESIDENCIA": "AM", "MUNICIPIO_RESIDENCIA": "MANAUS"}) for i in range(6)],
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



def preparar(base: Path) -> Config:
    """Cria os arquivos sintéticos em `base` e devolve a Config que aponta para eles."""
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
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
    return Config(entrada=landing, dados=base / "data", ref=ref, relatorios=base / "reports",
                  publicacao=base / "publicacao")


def main(argv: list[str] | None = None) -> int:
    from . import dbt_runner, pipeline

    argv = sys.argv[1:] if argv is None else argv
    docs = "--docs" in argv
    pastas = [a for a in argv if a != "--docs"]
    if len(pastas) != 1:
        print("uso: python -m sismigra.sinteticos PASTA [--docs]", file=sys.stderr)
        return 2
    cfg = preparar(Path(pastas[0]))
    res = pipeline.executar(cfg)
    res["con"].close()
    if docs:
        # site estático (um único HTML) com estrutura, descrições, testes e linhagem; sem dados reais
        dbt_runner.executar(cfg, "docs generate", "--static")
    return 0


if __name__ == "__main__":
    sys.exit(main())
