import re

from sismigra.config import RAIZ
from sismigra.quality import REGRAS


def test_lidas_igual_aceitas_mais_rejeitadas(execucao):
    rel = execucao["qualidade"]
    for a in rel["por_arquivo"]:
        assert a["lidas"] == a["aceitas"] + a["rejeitadas"]
    t = rel["totais"]
    assert t["lidas"] == t["aceitas"] + t["rejeitadas"]


def test_contagens_do_relatorio(execucao):
    rel = execucao["qualidade"]
    a25 = next(a for a in rel["por_arquivo"] if a["ano"] == 2025)
    assert a25["rejeicoes_por_regra"] == {"R00": 1, "R01": 1, "R02": 1, "R03": 1}
    assert rel["alertas"]["A02"] == [{"uf": "MT", "municipio": "JUREMA", "registros": 1}]
    assert rel["alertas"]["A03"] == []
    assert rel["alertas"]["A04"] == []


def test_relatorio_gravado(execucao):
    cfg = execucao["cfg"]
    md = (cfg.relatorios / "relatorio_qualidade.md").read_text(encoding="utf-8")
    assert "Linhas lidas" in md and "R02" in md
    assert (cfg.relatorios / "relatorio_qualidade.json").exists()


def test_todo_codigo_de_regra_do_sql_esta_documentado():
    sql = (RAIZ / "sql" / "silver.sql").read_text(encoding="utf-8")
    usados = set(re.findall(r"'([RC]\d\d)'", sql))
    assert usados, "nenhum código de regra encontrado no SQL"
    assert usados <= set(REGRAS), f"regras sem documentação: {usados - set(REGRAS)}"
