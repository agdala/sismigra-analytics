"""Constrói as tabelas de referência versionadas em ref/.

Gera:
  ref/uf.csv              27 UFs com código IBGE, sigla, nome e região
  ref/municipios_ibge.csv municípios da DTB do IBGE (código de 7 dígitos)
  ref/paises.csv          nomes de país do SISMIGRA ligados ao código ISO 3166-1 alfa-3

As tabelas já estão versionadas no repositório. Este script só precisa ser
rodado para atualizá-las (nova DTB ou novos anos do SISMIGRA).

Uso:
  python scripts/construir_refs.py --dtb CAMINHO/DTB_2023.zip --sismigra data/landing

Dependências extras: pip install -r requirements-dev.txt
"""

from __future__ import annotations

import argparse
import csv
import gettext
import re
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

import duckdb
import pandas as pd
import pycountry

REF = Path(__file__).resolve().parents[1] / "ref"

UFS = [
    ("11", "RO", "Rondônia", "Norte"), ("12", "AC", "Acre", "Norte"),
    ("13", "AM", "Amazonas", "Norte"), ("14", "RR", "Roraima", "Norte"),
    ("15", "PA", "Pará", "Norte"), ("16", "AP", "Amapá", "Norte"),
    ("17", "TO", "Tocantins", "Norte"), ("21", "MA", "Maranhão", "Nordeste"),
    ("22", "PI", "Piauí", "Nordeste"), ("23", "CE", "Ceará", "Nordeste"),
    ("24", "RN", "Rio Grande do Norte", "Nordeste"), ("25", "PB", "Paraíba", "Nordeste"),
    ("26", "PE", "Pernambuco", "Nordeste"), ("27", "AL", "Alagoas", "Nordeste"),
    ("28", "SE", "Sergipe", "Nordeste"), ("29", "BA", "Bahia", "Nordeste"),
    ("31", "MG", "Minas Gerais", "Sudeste"), ("32", "ES", "Espírito Santo", "Sudeste"),
    ("33", "RJ", "Rio de Janeiro", "Sudeste"), ("35", "SP", "São Paulo", "Sudeste"),
    ("41", "PR", "Paraná", "Sul"), ("42", "SC", "Santa Catarina", "Sul"),
    ("43", "RS", "Rio Grande do Sul", "Sul"), ("50", "MS", "Mato Grosso do Sul", "Centro-Oeste"),
    ("51", "MT", "Mato Grosso", "Centro-Oeste"), ("52", "GO", "Goiás", "Centro-Oeste"),
    ("53", "DF", "Distrito Federal", "Centro-Oeste"),
]


def norm(s: str) -> str:
    """Mesma normalização usada na camada prata (maiúsculas, sem acento, só letras)."""
    s = unicodedata.normalize("NFKD", s.upper()).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z]", "", s)


def escrever(caminho: Path, cab: list[str], linhas: list) -> None:
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(cab)
        w.writerows(linhas)
    print(f"{caminho.relative_to(REF.parent)}: {len(linhas)} linhas")


def construir_ufs() -> None:
    escrever(REF / "uf.csv", ["cod_uf", "uf_sigla", "uf_nome", "regiao"], UFS)


def construir_municipios(dtb_zip: Path) -> None:
    with zipfile.ZipFile(dtb_zip) as z, tempfile.TemporaryDirectory() as tmp:
        membro = next(m for m in z.namelist() if m.endswith("RELATORIO_DTB_BRASIL_MUNICIPIO.xls"))
        z.extract(membro, tmp)
        bruto = pd.read_excel(Path(tmp) / membro, header=None, dtype=str)
    linha_cab = bruto.index[bruto.iloc[:, 0].eq("UF")][0]
    df = bruto.iloc[linha_cab + 1 :].copy()
    df.columns = bruto.iloc[linha_cab].tolist()
    df = df.dropna(subset=["Código Município Completo"])
    siglas = {c: s for c, s, *_ in UFS}
    linhas = sorted(
        (r["Código Município Completo"], r["Nome_Município"], r["UF"], siglas[r["UF"]])
        for _, r in df.iterrows()
    )
    escrever(REF / "municipios_ibge.csv", ["cod_municipio_ibge", "municipio", "cod_uf", "uf_sigla"], linhas)


def construir_paises(landing: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        csvs = []
        for z in sorted(landing.glob("*.zip")):
            with zipfile.ZipFile(z) as zf:
                for m in zf.namelist():
                    if m.lower().endswith(".csv"):
                        zf.extract(m, tmp)
                        csvs.append((Path(tmp) / m).as_posix())
        csvs += [p.as_posix() for p in landing.glob("*.csv")]
        con = duckdb.connect()
        nomes = sorted(
            r[0]
            for r in con.execute(
                "SELECT DISTINCT unnest([PAIS_NASCIMENTO, PAIS_NACIONALIDADE]) FROM read_csv(?, delim=';', "
                "header=true, all_varchar=true, union_by_name=true)",
                [csvs],
            ).fetchall()
            if r[0] is not None
        )

    tr = [gettext.translation("iso3166-1", pycountry.LOCALES_DIR, languages=[l]) for l in ("pt_BR", "pt")]
    indice: dict[str, str] = {}
    for c in pycountry.countries:
        for nome in {c.name, getattr(c, "common_name", c.name), getattr(c, "official_name", c.name)}:
            for t in tr:
                indice.setdefault(norm(t.gettext(nome)), c.alpha_3)

    manual = {}
    with (REF / "paises_manual.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            manual[r["nome_fonte"]] = r

    linhas, faltando = [], []
    for nome in nomes:
        if nome in manual:
            r = manual[nome]
            linhas.append((nome, r["iso3"], r["nome_padronizado"], "manual", r["observacao"]))
        elif norm(nome) in indice:
            iso = indice[norm(nome)]
            pc = pycountry.countries.get(alpha_3=iso)
            nome_pt = tr[0].gettext(getattr(pc, "common_name", pc.name))
            linhas.append((nome, iso, nome_pt, "automatico", ""))
        else:
            faltando.append(nome)
    # Um único nome padronizado por código ISO: o nome manual tem prioridade sobre o automático.
    nome_por_iso: dict[str, str] = {}
    for nome, iso, padrao, metodo, _ in sorted(linhas, key=lambda x: x[3] != "manual"):
        if iso:
            nome_por_iso.setdefault(iso, padrao)
    linhas = [(n, i, nome_por_iso.get(i, p), m, o) for n, i, p, m, o in linhas]
    escrever(REF / "paises.csv", ["nome_fonte", "iso3", "nome_padronizado", "metodo", "observacao"], linhas)
    if faltando:
        print("Sem mapeamento (adicione em ref/paises_manual.csv):", *faltando, sep="\n  ")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dtb", type=Path, help="ZIP da DTB do IBGE")
    ap.add_argument("--sismigra", type=Path, help="pasta com os ZIPs do SISMIGRA")
    a = ap.parse_args(argv)
    construir_ufs()
    if a.dtb:
        construir_municipios(a.dtb)
    if a.sismigra:
        construir_paises(a.sismigra)
    return 0


if __name__ == "__main__":
    sys.exit(main())
