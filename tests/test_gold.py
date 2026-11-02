FKS = [
    ("sk_ano_registro", "dim_tempo", "sk_tempo"),
    ("sk_ano_entrada", "dim_tempo", "sk_tempo"),
    ("sk_pais_nascimento", "dim_pais", "sk_pais"),
    ("sk_pais_nacionalidade", "dim_pais", "sk_pais"),
    ("sk_localidade", "dim_localidade", "sk_localidade"),
    ("sk_perfil", "dim_perfil", "sk_perfil"),
    ("sk_amparo", "dim_amparo", "sk_amparo"),
    ("sk_ocupacao", "dim_ocupacao", "sk_ocupacao"),
]


def um(con, sql, params=None):
    return con.execute(sql, params or []).fetchone()[0]


def test_fato_tem_todos_os_registros_aceitos(execucao):
    con = execucao["con"]
    assert um(con, "SELECT count(*) FROM fato_registro") == um(con, "SELECT count(*) FROM int_registros_enriquecidos")


def test_integridade_referencial(execucao):
    con = execucao["con"]
    for fk, dim, pk in FKS:
        orfaos = um(con, f"SELECT count(*) FROM fato_registro f ANTI JOIN {dim} d ON f.{fk} = d.{pk}")
        assert orfaos == 0, f"{fk} tem {orfaos} chaves sem {dim}"


def test_chaves_das_dimensoes_unicas(execucao):
    con = execucao["con"]
    for _, dim, pk in FKS:
        assert um(con, f"SELECT count(*) - count(DISTINCT {pk}) FROM {dim}") == 0


def test_base_dos_agregados_soma_igual_ao_fato(execucao):
    con = execucao["con"]
    assert um(con, "SELECT sum(qtd_registros) FROM agregado_base") == um(con, "SELECT count(*) FROM fato_registro")


def test_grafias_diferentes_viram_um_pais(execucao):
    con = execucao["con"]
    sks = con.execute(
        "SELECT DISTINCT f.sk_pais_nacionalidade FROM fato_registro f JOIN int_registros_enriquecidos p USING (id_registro) "
        "WHERE p.profissao IN ('KUAITE', 'KUWEIT')").fetchall()
    assert len(sks) == 1
    assert um(con, "SELECT iso3 FROM dim_pais WHERE sk_pais = ?", [sks[0][0]]) == "KWT"


def test_pais_ausente_vai_para_membro_nao_informado(execucao):
    con = execucao["con"]
    assert um(con, "SELECT f.sk_pais_nacionalidade FROM fato_registro f JOIN int_registros_enriquecidos p USING (id_registro) "
                   "WHERE p.profissao = 'PAIS_TRACO'") == -1


def test_hierarquia_de_amparo(execucao):
    con = execucao["con"]
    r = con.execute("SELECT categoria_ampla, subgrupo_protecao FROM dim_amparo WHERE amparo_codigo = 290").fetchone()
    assert r == ("Proteção internacional e humanitária", "Solicitantes de refúgio")
    r = con.execute("SELECT categoria_ampla FROM dim_amparo WHERE amparo_codigo = 273").fetchone()
    assert r == ("Proteção internacional e humanitária",)
    r = con.execute("SELECT categoria_ampla FROM dim_amparo WHERE amparo_codigo = 326").fetchone()
    assert r == ("Mobilidade regional e acordos",)


def test_dim_tempo_marca_ano_parcial(execucao):
    con = execucao["con"]
    assert con.execute("SELECT cobertura_registro, ano_completo FROM dim_tempo WHERE ano = 2026").fetchone() == (
        "jan-set", False)
    assert con.execute("SELECT ano_completo FROM dim_tempo WHERE ano = 2025").fetchone() == (True,)


def test_arquivos_exportados(execucao):
    cfg = execucao["cfg"]
    for t in execucao["contagens"]:
        if t.startswith("agregado_looker"):
            assert (cfg.publicacao / f"{t}.csv").exists()
            assert not (cfg.ouro / f"{t}.csv").exists()
            continue
        assert (cfg.ouro / "parquet" / f"{t}.parquet").exists()
        csv = cfg.ouro / "csv" / f"{t}.csv"
        assert csv.read_bytes()[:3] == b"\xef\xbb\xbf"
