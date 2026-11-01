"""Regras de qualidade e relatório gerado a cada execução.

As regras são declaradas uma única vez em REGRAS. O SQL da prata aplica as regras de
rejeição (R) e correção (C); os alertas (A) são calculados aqui. Os testes em tests/
verificam cada regra com dados sintéticos.

Severidades:
  rejeicao  o registro sai da prata e vai para rejeitados.parquet
  correcao  o registro fica; o valor é padronizado ou marcado como "Não informado"
  alerta    nada muda nos dados; o achado aparece no relatório para análise
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import duckdb

from .config import Config

REGRAS = {
    "R00": ("rejeicao", "Linha malformada (número de colunas diferente do cabeçalho)"),
    "R01": ("rejeicao", "DATAREGISTRO ausente ou não numérico"),
    "R02": ("rejeicao", "DATAREGISTRO diferente do ano declarado para o arquivo em ref/fontes.csv"),
    "R03": ("rejeicao", "AMPARO ausente ou não numérico"),
    "C01": ("correcao", "Ano de entrada ausente, inválido (ex.: '--', '####', '0007') ou posterior ao registro: vira nulo"),
    "C02": ("correcao", "UF ausente ou inválida: localidade 'Não informado'"),
    "C03": ("correcao", "Município casado por exceção manual (ref/excecoes_municipios.csv)"),
    "C04": ("correcao", "Sexo ausente ou não declarado (5 grafias na fonte): 'Não informado'"),
    "C05": ("correcao", "Faixa etária não especificada na fonte ou idade ausente/inválida"),
    "C06": ("correcao", "Idade fora de 0 a 120 anos (ex.: negativa): descartada"),
    "C07": ("correcao", "Estado civil ausente, '-' ou DESCONHECIDO: 'Não informado'"),
    "C08": ("correcao", "Estado civil com '_' no lugar de espaço (ex.: SEPARADO_JUDICIALMENTE)"),
    "C09": ("correcao", "Classificação do registro ausente: 'Não informado'"),
    "A01": ("alerta", "Registros que pertencem a um grupo de linhas idênticas no mesmo arquivo (mantidos: sem identificador, são pessoas distintas)"),
    "A02": ("alerta", "Município informado sem correspondência no IBGE nem exceção"),
    "A03": ("alerta", "País da fonte sem mapeamento em ref/paises.csv"),
    "A04": ("alerta", "Código de amparo sem categoria em ref/amparos.csv"),
    "A05": ("alerta", "Profissão 'MENOR' com faixa etária de 25 anos ou mais"),
    "A06": ("alerta", "Mesmo código de amparo com mais de uma descrição no mesmo ano"),
}


def calcular(con: duckdb.DuckDBPyConnection, leitura: list[dict]) -> dict:
    """Calcula as métricas de qualidade a partir das tabelas prata e rejeitados."""
    q = lambda sql: con.execute(sql).fetchall()  # noqa: E731

    por_arquivo = []
    for item in leitura:
        nome = item["arquivo_csv"]
        aceitas = q(f"SELECT count(*) FROM prata WHERE arquivo_csv = '{nome}'")[0][0]
        rej = dict(q(f"SELECT regra, count(*) FROM rejeitados WHERE arquivo_csv = '{nome}' GROUP BY 1"))
        lidas = item["lidas_validas"] + item["malformadas"]
        por_arquivo.append({
            "arquivo_csv": nome, "ano": item["ano"], "lidas": lidas, "aceitas": aceitas,
            "rejeitadas": sum(rej.values()), "rejeicoes_por_regra": rej,
        })

    correcoes = {}
    for ano, regra, n in q(
        "SELECT ano_registro, c, count(*) FROM (SELECT ano_registro, unnest(correcoes) c FROM prata) GROUP BY ALL"
    ):
        correcoes.setdefault(regra, {})[str(ano)] = n

    alertas = {
        "A01": dict((str(a), n) for a, n in q(
            "SELECT ano_registro, count(*) FROM prata WHERE flag_duplicata_exata GROUP BY 1 ORDER BY 1")),
        "A02": [{"uf": u, "municipio": m, "registros": n} for u, m, n in q(
            "SELECT uf_sigla, municipio_fonte, count(*) FROM prata WHERE municipio_status = 'sem correspondência' "
            "GROUP BY ALL ORDER BY 3 DESC")],
        "A03": [{"pais": p, "registros": n} for p, n in q(
            "SELECT p, count(*) FROM (SELECT unnest([pais_nascimento_fonte, pais_nacionalidade_fonte]) p FROM prata) "
            "WHERE p NOT IN (SELECT nome_fonte FROM ref_paises) GROUP BY 1 ORDER BY 2 DESC")],
        "A04": [{"amparo": c, "registros": n} for c, n in q(
            "SELECT amparo_codigo, count(*) FROM prata WHERE amparo_codigo NOT IN (SELECT codigo FROM ref_amparos) "
            "GROUP BY 1 ORDER BY 2 DESC")],
        "A05": q("SELECT count(*) FROM prata WHERE profissao LIKE 'MENOR%' "
                 "AND faixa_etaria IN ('25 a 39 anos', '40 a 64 anos', '65 anos ou mais')")[0][0],
        "A06": [{"amparo": c, "ano": a, "descricoes": n} for c, a, n in q(
            "SELECT amparo_codigo, ano_registro, count(DISTINCT amparo_descricao) n FROM prata "
            "GROUP BY 1, 2 HAVING n > 1 ORDER BY 1, 2")],
    }

    municipios = dict(q("SELECT municipio_status, count(*) FROM prata GROUP BY 1"))
    especificados = municipios.get("ibge", 0) + municipios.get("exceção manual", 0) + municipios.get(
        "sem correspondência", 0)
    casados = municipios.get("ibge", 0) + municipios.get("exceção manual", 0)

    total_lidas = sum(a["lidas"] for a in por_arquivo)
    total_aceitas = sum(a["aceitas"] for a in por_arquivo)
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "totais": {
            "lidas": total_lidas,
            "aceitas": total_aceitas,
            "rejeitadas": total_lidas - total_aceitas,
            "pct_aceitas": round(100 * total_aceitas / total_lidas, 3) if total_lidas else None,
        },
        "por_arquivo": por_arquivo,
        "correcoes": correcoes,
        "alertas": alertas,
        "municipios": {
            "por_status": municipios,
            "pct_casados_entre_especificados": round(100 * casados / especificados, 3) if especificados else None,
        },
    }


def _fmt(n) -> str:
    return f"{n:,}".replace(",", ".") if isinstance(n, int) else str(n)


def escrever(cfg: Config, rel: dict) -> None:
    cfg.relatorios.mkdir(parents=True, exist_ok=True)
    carimbo = rel["gerado_em"].replace(":", "").replace("-", "")[:15]
    js = json.dumps(rel, ensure_ascii=False, indent=2)
    (cfg.relatorios / f"qualidade_{carimbo}.json").write_text(js, encoding="utf-8")
    (cfg.relatorios / "relatorio_qualidade.json").write_text(js, encoding="utf-8")

    t = rel["totais"]
    anos = sorted({a for v in rel["correcoes"].values() for a in v})
    L = [
        "# Relatório de qualidade: SISMIGRA",
        "",
        f"Gerado em {rel['gerado_em']} (UTC) pelo pipeline `python -m sismigra.pipeline`.",
        "",
        "## Resumo",
        "",
        f"- Linhas lidas: **{_fmt(t['lidas'])}**",
        f"- Aceitas na prata: **{_fmt(t['aceitas'])}** ({t['pct_aceitas']}%)",
        f"- Rejeitadas: **{_fmt(t['rejeitadas'])}**",
        f"- Municípios especificados com código IBGE: **{rel['municipios']['pct_casados_entre_especificados']}%**",
        "",
        "## Leitura por arquivo",
        "",
        "| Arquivo | Ano | Lidas | Aceitas | Rejeitadas | Motivos |",
        "|---|---|---|---|---|---|",
    ]
    for a in rel["por_arquivo"]:
        motivos = ", ".join(f"{r}: {_fmt(n)}" for r, n in sorted(a["rejeicoes_por_regra"].items())) or "nenhum"
        L.append(f"| {a['arquivo_csv']} | {a['ano']} | {_fmt(a['lidas'])} | {_fmt(a['aceitas'])} | "
                 f"{_fmt(a['rejeitadas'])} | {motivos} |")
    L += ["", "## Regras de rejeição", "", "| Regra | Descrição |", "|---|---|"]
    L += [f"| {k} | {d} |" for k, (s, d) in REGRAS.items() if s == "rejeicao"]
    L += ["", "## Correções aplicadas (registros por ano)", "",
          "| Regra | Descrição | " + " | ".join(anos) + " |", "|---|---|" + "---|" * len(anos)]
    for k, (s, d) in REGRAS.items():
        if s == "correcao":
            v = rel["correcoes"].get(k, {})
            L.append(f"| {k} | {d} | " + " | ".join(_fmt(v.get(a, 0)) for a in anos) + " |")
    al = rel["alertas"]
    L += ["", "## Alertas", "", "| Regra | Descrição | Resultado |", "|---|---|---|"]
    L.append(f"| A01 | {REGRAS['A01'][1]} | " + ", ".join(f"{a}: {_fmt(n)}" for a, n in al["A01"].items()) + " |")
    L.append(f"| A02 | {REGRAS['A02'][1]} | " + (", ".join(
        f"{x['uf']}/{x['municipio']} ({_fmt(x['registros'])})" for x in al["A02"]) or "nenhum") + " |")
    L.append(f"| A03 | {REGRAS['A03'][1]} | " + (", ".join(
        f"{x['pais']} ({_fmt(x['registros'])})" for x in al["A03"]) or "nenhum") + " |")
    L.append(f"| A04 | {REGRAS['A04'][1]} | " + (", ".join(
        f"{x['amparo']} ({_fmt(x['registros'])})" for x in al["A04"]) or "nenhum") + " |")
    L.append(f"| A05 | {REGRAS['A05'][1]} | {_fmt(al['A05'])} registros |")
    L.append(f"| A06 | {REGRAS['A06'][1]} | " + (", ".join(
        f"{x['amparo']} em {x['ano']} ({x['descricoes']})" for x in al["A06"]) or "nenhum") + " |")
    L += ["", "## Municípios por situação", "", "| Situação | Registros |", "|---|---|"]
    L += [f"| {k} | {_fmt(v)} |" for k, v in sorted(rel["municipios"]["por_status"].items(), key=lambda x: -x[1])]
    L.append("")
    texto = "\n".join(L)
    (cfg.relatorios / f"qualidade_{carimbo}.md").write_text(texto, encoding="utf-8")
    (cfg.relatorios / "relatorio_qualidade.md").write_text(texto, encoding="utf-8")
