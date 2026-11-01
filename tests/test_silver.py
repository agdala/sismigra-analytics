"""Uma verificação por regra de rejeição e de correção da camada prata."""


def regras_rejeitadas(con):
    return dict(con.execute("SELECT regra, count(*) FROM rejeitados GROUP BY 1").fetchall())


def test_rejeicoes(execucao):
    r = regras_rejeitadas(execucao["con"])
    assert r == {"R00": 1, "R01": 1, "R02": 1, "R03": 1}


def test_duplicatas_exatas_sao_mantidas_e_marcadas(execucao):
    rows = execucao["con"].execute(
        "SELECT flag_duplicata_exata FROM prata WHERE profissao = 'DUP'").fetchall()
    assert rows == [(True,), (True,)]


def test_linha_unica_nao_e_duplicata(linha):
    assert linha("SP")["flag_duplicata_exata"] is False


def test_ano_entrada(linha):
    assert linha("ENTRADA_OK")["ano_entrada"] == 2019
    for m in ("ENTRADA_TRACO", "ENTRADA_FUTURA"):
        r = linha(m)
        assert r["ano_entrada"] is None and "C01" in r["correcoes"]


def test_sexo_padronizado(linha):
    assert linha("SP")["sexo"] == "Masculino"
    for m in ("SEXO_ND", "SEXO_TRACO"):
        r = linha(m)
        assert r["sexo"] == "Não informado" and "C04" in r["correcoes"]


def test_municipios(linha):
    assert (linha("SP")["cod_municipio_ibge"], linha("SP")["municipio_status"]) == ("3550308", "ibge")
    assert linha("APOSTROFO")["municipio_status"] == "ibge"  # HERVAL DOESTE = Herval d'Oeste
    ex = linha("EXCECAO")
    assert (ex["cod_municipio_ibge"], ex["municipio_status"]) == ("3303807", "exceção manual")
    assert "C03" in ex["correcoes"]
    sm = linha("SEM_MATCH")
    assert sm["cod_municipio_ibge"] is None and sm["municipio_status"] == "sem correspondência"
    assert linha("NAO_ESPEC")["municipio_status"] == "não especificado"
    uf = linha("UF_TRACO")
    assert uf["uf_sigla"] is None and uf["municipio_status"] == "uf não informada" and "C02" in uf["correcoes"]


def test_estado_civil(linha):
    r = linha("EC_UNDERSCORE")
    assert r["estado_civil"] == "SEPARADO JUDICIALMENTE" and "C08" in r["correcoes"]
    r = linha("EC_DESCONHECIDO")
    assert r["estado_civil"] == "Não informado" and "C07" in r["correcoes"]


def test_faixa_etaria_da_fonte(linha):
    r = linha("SP")
    assert (r["faixa_etaria"], r["faixa_etaria_origem"]) == ("25 a 39 anos", "fonte")
    r = linha("FAIXA_NE")
    assert r["faixa_etaria"] == "Não especificado" and "C05" in r["correcoes"]


def test_faixa_etaria_derivada_da_idade_2026(linha):
    esperado = {"IDADE_30": "25 a 39 anos", "IDADE_14": "0 a 14 anos",
                "IDADE_15": "15 a 24 anos", "IDADE_65": "65 anos ou mais"}
    for m, faixa in esperado.items():
        r = linha(m)
        assert (r["faixa_etaria"], r["faixa_etaria_origem"]) == (faixa, "derivada da idade")


def test_idade_invalida(linha):
    r = linha("IDADE_NEG")
    assert r["idade"] is None and r["faixa_etaria"] == "Não especificado"
    assert {"C05", "C06"} <= set(r["correcoes"])
    r = linha("IDADE_NULA")
    assert r["faixa_etaria"] == "Não especificado" and "C06" not in r["correcoes"]


def test_id_registro_unico(execucao):
    n, d = execucao["con"].execute("SELECT count(*), count(DISTINCT id_registro) FROM prata").fetchone()
    assert n == d
