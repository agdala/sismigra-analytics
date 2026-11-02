"""Verificações da camada dbt sobre os dados sintéticos."""

import json

from conftest import hash_ref


def um(con, sql):
    return con.execute(sql).fetchone()[0]


def test_dbt_criou_as_camadas(execucao):
    con = execucao["con"]
    esperado = {
        "staging": {"stg_registros", "stg_rejeitados"},
        "intermediate": {"int_registros_municipio", "int_registros_enriquecidos", "int_paises", "int_mapa_pais"},
        "marts": {"fato_registro", "dim_tempo", "dim_pais", "dim_localidade", "dim_perfil", "dim_amparo",
                  "dim_ocupacao", "amparo_descricao_ano", "agregado_base"},
        "ref": {"amparos", "paises", "municipios_ibge", "excecoes_municipios", "uf", "fontes"},
        "bronze": {"registros_brutos", "linhas_malformadas", "manifesto"},
    }
    for schema, objetos in esperado.items():
        existentes = {r[0] for r in con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = ?", [schema]).fetchall()}
        assert objetos <= existentes, f"{schema}: faltam {objetos - existentes}"


def test_seed_de_referencia_nao_carrega_insumo_manual(execucao):
    con = execucao["con"]
    assert um(con, "SELECT count(*) FROM information_schema.tables WHERE table_name = 'paises_manual'") == 0


def test_testes_do_dbt_rodaram_sem_erro(execucao):
    """O dbt build falharia o pipeline em erro; aqui confere o resultado salvo pelo dbt."""
    resultados = json.loads((execucao["cfg"].dbt / "target" / "run_results.json").read_text(encoding="utf-8"))
    status = {r["status"] for r in resultados["results"]}
    assert status <= {"success", "pass", "warn", "no-op"}, status   # no-op = exposures
    testes = [r for r in resultados["results"] if r["unique_id"].startswith("test.")]
    assert len(testes) >= 100


def test_alertas_sao_avisos_e_nao_erros(execucao):
    resultados = json.loads((execucao["cfg"].dbt / "target" / "run_results.json").read_text(encoding="utf-8"))
    por_nome = {r["unique_id"].split(".")[2]: r["status"] for r in resultados["results"]}
    # JUREMA/MT existe nos dados sintéticos: o alerta A02 dispara como aviso
    assert por_nome["alerta_municipio_sem_correspondencia_ibge"] == "warn"


def test_dbt_nao_altera_ref(execucao, ref_antes):
    """Regressão: com seeds fora do projeto, o dbt chegou a sobrescrever ref/*.csv com SQL compilado."""
    assert hash_ref() == ref_antes


def test_fonte_manifesto_com_data_de_ingestao(execucao):
    con = execucao["con"]
    assert um(con, "SELECT count(*) FROM bronze.manifesto WHERE ingerido_em IS NULL") == 0
    assert um(con, "SELECT count(*) FROM bronze.manifesto") == len(execucao["manifesto"]["arquivos"])
