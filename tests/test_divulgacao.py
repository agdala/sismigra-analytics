"""Controle de divulgação: nenhuma célula publicada com 1 a 4 registros, totais conciliados."""

import duckdb
import pytest

from sismigra import divulgacao

TABELAS = list(divulgacao.TABELAS)


@pytest.mark.parametrize("tabela", TABELAS)
def test_nenhuma_celula_publicada_abaixo_do_limiar(execucao, tabela):
    con = execucao["con"]
    n = con.execute(f"SELECT count(*) FROM {tabela} WHERE qtd_registros < {divulgacao.LIMIAR}").fetchone()[0]
    assert n == 0


@pytest.mark.parametrize("tabela", TABELAS)
def test_suprimidas_tem_contagem_nula(execucao, tabela):
    con = execucao["con"]
    ruins = con.execute(
        f"SELECT count(*) FROM {tabela} WHERE suprimido <> (qtd_registros IS NULL)").fetchone()[0]
    assert ruins == 0


@pytest.mark.parametrize("tabela", TABELAS)
def test_publicado_mais_suprimido_igual_ao_fato(execucao, tabela):
    st = execucao["divulgacao"][tabela]
    fato = execucao["con"].execute("SELECT count(*) FROM fato_registro").fetchone()[0]
    assert st["registros_total"] == fato
    assert st["registros_publicados"] + st["registros_suprimidos"] == fato


def test_celula_grande_nao_e_alterada(execucao):
    """Os 6 registros GRUPO (AM, mesmo perfil e amparo) somados aos demais iguais formam célula >= 5."""
    con = execucao["con"]
    r = con.execute(
        "SELECT qtd_registros, nivel_agrupamento FROM agregado_looker_territorio "
        "WHERE uf_sigla = 'AM' AND sexo = 'Masculino'").fetchall()
    assert r == [(6, 0)]


def test_csv_exportado_sem_contagens_pequenas(execucao):
    cfg = execucao["cfg"]
    con = duckdb.connect()
    for t in TABELAS:
        n = con.execute(
            f"SELECT count(*) FROM read_csv('{(cfg.publicacao / f'{t}.csv').as_posix()}', header=true) "
            f"WHERE qtd_registros BETWEEN 1 AND {divulgacao.LIMIAR - 1}").fetchone()[0]
        assert n == 0


def test_agrupamento_preserva_total_quando_possivel():
    """5 células de 1 registro no mesmo ano e UF viram 1 célula de 5 após o agrupamento: nada é suprimido."""
    con = duckdb.connect()
    con.execute("""
        CREATE TABLE base AS SELECT * FROM (VALUES
            (2025, 'SP', 'Masculino', 'A', 1), (2025, 'SP', 'Feminino', 'A', 1),
            (2025, 'SP', 'Masculino', 'B', 1), (2025, 'SP', 'Feminino', 'B', 1),
            (2025, 'SP', 'Masculino', 'C', 1), (2025, 'RJ', 'Feminino', 'A', 3)
        ) v(ano, uf, sexo, tipo, qtd_registros)""")
    st = divulgacao.proteger(con, "base", "saida", ["ano", "uf", "sexo", "tipo"],
                             [[("tipo", "'Agrupado'")], [("sexo", "'Agrupado'")]])
    linhas = con.execute("SELECT uf, sexo, tipo, qtd_registros, suprimido FROM saida ORDER BY uf").fetchall()
    assert ("SP", "Agrupado", "Agrupado", 5, False) in linhas
    assert ("RJ", "Agrupado", "Agrupado", None, True) in linhas
    assert st["registros_publicados"] == 5 and st["registros_suprimidos"] == 3


def test_formato_dos_arquivos_publicados(execucao):
    """Vírgula, UTF-8 sem BOM, cabeçalho na primeira linha e colunas esperadas."""
    cfg = execucao["cfg"]
    for t, spec in divulgacao.TABELAS.items():
        bruto = (cfg.publicacao / f"{t}.csv").read_bytes()
        assert not bruto.startswith(b"\xef\xbb\xbf")
        bruto.decode("utf-8")
        cabecalho = bruto.split(b"\n", 1)[0].decode("utf-8").split(",")
        assert cabecalho == spec["dimensoes"] + ["qtd_registros", "nivel_agrupamento", "suprimido"]


def test_metadados_de_publicacao(execucao):
    import json
    cfg = execucao["cfg"]
    meta = json.loads((cfg.publicacao / "metadados.json").read_text(encoding="utf-8"))
    assert meta["limiar_k"] == divulgacao.LIMIAR
    assert {f["sha256"] for f in meta["fontes"]} == {a["sha256"] for a in execucao["manifesto"]["arquivos"]}
    assert set(meta["tabelas"]) == set(divulgacao.TABELAS)
    assert all("registros_total" not in v for v in meta["tabelas"].values())


@pytest.mark.parametrize("tabela", TABELAS)
def test_nenhum_ano_com_uma_unica_celula_suprimida(execucao, tabela):
    """Com o total do ano publicado, uma única célula suprimida seria recuperável por subtração."""
    con = execucao["con"]
    anos = con.execute(
        f"SELECT ano_registro, count(*) FILTER (WHERE suprimido) s FROM {tabela} GROUP BY 1 HAVING s = 1"
    ).fetchall()
    assert anos == []


def test_supressao_secundaria():
    """Um ano com uma só célula pequena tem a menor célula publicada suprimida junto."""
    con = duckdb.connect()
    con.execute("""
        CREATE TABLE base AS SELECT * FROM (VALUES
            (2025, 'SP', 50), (2025, 'RJ', 7), (2025, 'AC', 2),
            (2024, 'SP', 40), (2024, 'RJ', 9)
        ) v(ano_registro, uf, qtd_registros)""")
    st = divulgacao.proteger(con, "base", "saida", ["ano_registro", "uf"], [])
    linhas = dict(((a, u), (q, s)) for a, u, q, s in con.execute(
        "SELECT ano_registro, uf, qtd_registros, suprimido FROM saida").fetchall())
    assert linhas[(2025, "AC")] == (None, True)
    assert linhas[(2025, "RJ")] == (None, True)     # secundária: menor célula publicada do ano
    assert linhas[(2025, "SP")] == (50, False)
    assert linhas[(2024, "RJ")] == (9, False)       # ano sem supressão não é afetado
    assert st["celulas_supressao_primaria"] == 1 and st["celulas_supressao_secundaria"] == 1
