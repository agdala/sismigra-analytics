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
            f"SELECT count(*) FROM read_csv('{(cfg.ouro / f'{t}.csv').as_posix()}', header=true) "
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
