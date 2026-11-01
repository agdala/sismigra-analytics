"""Validações das tabelas de referência versionadas em ref/ (regras de governança)."""

import csv

from sismigra.config import RAIZ

CATEGORIAS = {
    "Proteção internacional e humanitária", "Mobilidade regional e acordos", "Família",
    "Trabalho e investimento", "Estudo", "Outros", "Não informado",
}


def ler(nome):
    with (RAIZ / "ref" / nome).open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def test_amparos_completos_e_unicos():
    amp = ler("amparos.csv")
    codigos = [a["codigo"] for a in amp]
    assert len(codigos) == len(set(codigos))
    for a in amp:
        assert a["categoria_ampla"] in CATEGORIAS, a
        if a["categoria_ampla"] == "Proteção internacional e humanitária":
            assert a["subgrupo_protecao"], f"amparo {a['codigo']} sem subgrupo"


def test_municipios_ibge_coerentes_com_uf():
    ufs = {u["cod_uf"]: u["uf_sigla"] for u in ler("uf.csv")}
    assert len(ufs) == 27
    mun = ler("municipios_ibge.csv")
    assert len({m["cod_municipio_ibge"] for m in mun}) == len(mun)
    for m in mun:
        assert len(m["cod_municipio_ibge"]) == 7
        assert m["cod_municipio_ibge"][:2] == m["cod_uf"]
        assert ufs[m["cod_uf"]] == m["uf_sigla"]


def test_excecoes_apontam_para_municipio_existente_na_uf():
    mun = {m["cod_municipio_ibge"]: m["uf_sigla"] for m in ler("municipios_ibge.csv")}
    for e in ler("excecoes_municipios.csv"):
        assert e["justificativa"], e
        if e["cod_municipio_ibge"]:
            assert mun.get(e["cod_municipio_ibge"]) == e["uf"], e


def test_paises_um_nome_por_iso_e_sem_duplicatas():
    paises = ler("paises.csv")
    fontes = [p["nome_fonte"] for p in paises]
    assert len(fontes) == len(set(fontes))
    por_iso = {}
    for p in paises:
        if p["iso3"]:
            por_iso.setdefault(p["iso3"], set()).add(p["nome_padronizado"])
    assert all(len(v) == 1 for v in por_iso.values()), {k: v for k, v in por_iso.items() if len(v) > 1}
    for p in paises:
        if not p["iso3"]:
            assert p["observacao"], f"{p['nome_fonte']} sem ISO precisa de justificativa"


def test_fontes_um_arquivo_por_ano():
    fontes = ler("fontes.csv")
    anos = [f["ano"] for f in fontes]
    assert len(anos) == len(set(anos))
    for f in fontes:
        assert f["url_origem"].startswith("https://") and f["ano_completo"] in ("true", "false")
