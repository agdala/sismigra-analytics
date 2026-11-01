"""Controle de divulgação dos agregados publicados no Looker Studio.

Regra: nenhuma célula publicada pode ter de 1 a 4 registros (limiar k = 5).

Supressão simples (apagar as células pequenas) esconderia cerca de 7% dos registros e
distorceria os totais. Por isso o método tem duas fases:

1. Agrupamento progressivo: as células abaixo do limiar têm atributos de menor prioridade
   trocados por "Agrupado", em etapas, e são somadas de novo. Atributos de maior valor
   analítico (ano, UF, país) são os últimos a serem agrupados.
2. Supressão residual: o que continuar abaixo do limiar recebe qtd_registros nulo e
   suprimido = true. A linha é mantida para indicar que existe uma célula pequena.
3. Supressão secundária: se um total conhecido publicamente (o total de cada ano, publicado
   no README) ficar com uma única célula suprimida, a menor célula publicada desse total
   também é suprimida. Sem isso, o valor escondido sairia por subtração.

Cada linha publicada traz nivel_agrupamento: 0 = sem alteração; N = agrupada na etapa N.

Para separar os cruzamentos mais sensíveis, são publicadas duas tabelas:
  agregado_looker_nacionalidade.csv  ano x país x perfil x amparo (sem território)
  agregado_looker_territorio.csv     ano x UF x perfil x amparo (sem país)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from .silver import lit

LIMIAR = 5

COMUNS = [
    "ano_registro", "cobertura", "ano_completo", "sexo", "faixa_etaria", "ordem_faixa_etaria",
    "categoria_ampla", "subgrupo_protecao", "tipologia_ajustada", "status_ativo",
]
PERFIL = [("sexo", "'Agrupado'"), ("faixa_etaria", "'Agrupada'"), ("ordem_faixa_etaria", "9"),
          ("status_ativo", "NULL")]

# Totais conhecidos publicamente (o README publica o total exato de cada ano). A supressão
# secundária garante que nenhum desses totais tenha exatamente uma célula suprimida, o que
# permitiria recuperar o valor por subtração.
MARGINAIS = ["ano_registro"]

TABELAS = {
    "agregado_looker_nacionalidade": {
        "dimensoes": COMUNS + ["pais_nacionalidade", "iso3_nacionalidade", "continente_nacionalidade"],
        "etapas": [
            [("tipologia_ajustada", "'Agrupada'")],
            [("subgrupo_protecao", "'Agrupado'")],
            PERFIL,
            [("categoria_ampla", "'Agrupada'")],
            [("pais_nacionalidade", "'Outros países (' || continente_nacionalidade || ')'"),
             ("iso3_nacionalidade", "NULL")],
            [("pais_nacionalidade", "'Outros países'"), ("continente_nacionalidade", "'Agrupado'")],
        ],
    },
    "agregado_looker_territorio": {
        "dimensoes": COMUNS + ["regiao", "uf_sigla"],
        "etapas": [
            [("tipologia_ajustada", "'Agrupada'")],
            [("subgrupo_protecao", "'Agrupado'")],
            PERFIL,
            [("categoria_ampla", "'Agrupada'")],
        ],
    },
}


def proteger(con: duckdb.DuckDBPyConnection, origem: str, destino: str, dimensoes: list[str],
             etapas: list[list[tuple[str, str]]], limiar: int = LIMIAR) -> dict:
    """Cria a tabela `destino` protegida a partir de `origem` (que tem a coluna qtd_registros)."""
    dims = ", ".join(dimensoes)
    con.execute(
        f"CREATE OR REPLACE TEMP TABLE _p AS SELECT {dims}, 0 AS nivel, sum(qtd_registros) AS n "
        f"FROM {origem} GROUP BY ALL"
    )
    stats = {"celulas_iniciais": con.execute("SELECT count(*) FROM _p").fetchone()[0], "etapas": []}
    for i, etapa in enumerate(etapas, start=1):
        afetadas = con.execute(f"SELECT count(*), coalesce(sum(n), 0) FROM _p WHERE n < {limiar}").fetchone()
        troca = ", ".join(f"CASE WHEN n < {limiar} THEN {expr} ELSE {col} END AS {col}" for col, expr in etapa)
        con.execute(
            f"CREATE OR REPLACE TEMP TABLE _p AS SELECT * EXCLUDE (nivel, n) REPLACE ({troca}), "
            f"CASE WHEN n < {limiar} THEN {i} ELSE nivel END AS nivel, n FROM _p"
        )
        con.execute(f"CREATE OR REPLACE TEMP TABLE _p AS SELECT {dims}, max(nivel) AS nivel, sum(n) AS n "
                    f"FROM _p GROUP BY ALL")
        stats["etapas"].append({"etapa": i, "colunas": [c for c, _ in etapa],
                                "celulas_agrupadas": afetadas[0], "registros_agrupados": afetadas[1]})
    # supressão primária: o que continuou abaixo do limiar
    con.execute(f"CREATE OR REPLACE TEMP TABLE _p AS SELECT *, n < {limiar} AS sup FROM _p")
    primarias = con.execute("SELECT count(*) FROM _p WHERE sup").fetchone()[0]
    # supressão secundária: em cada total conhecido com exatamente 1 célula suprimida,
    # suprime também a menor célula publicada desse total (desempate determinístico)
    secundarias = 0
    for marg in MARGINAIS:
        if marg not in dimensoes:
            continue
        while True:
            alvo = con.execute(
                f"SELECT rowid FROM (SELECT rowid, row_number() OVER (PARTITION BY {marg} "
                f"ORDER BY n, {dims}) AS rk FROM _p WHERE NOT sup AND {marg} IN "
                f"(SELECT {marg} FROM _p GROUP BY 1 HAVING count(*) FILTER (WHERE sup) = 1)) WHERE rk = 1"
            ).fetchall()
            if not alvo:
                break
            con.execute(f"UPDATE _p SET sup = true WHERE rowid IN ({', '.join(str(r[0]) for r in alvo)})")
            secundarias += len(alvo)
    con.execute(
        f"CREATE OR REPLACE TABLE {destino} AS SELECT {dims}, "
        f"CASE WHEN NOT sup THEN n END AS qtd_registros, nivel AS nivel_agrupamento, "
        f"sup AS suprimido FROM _p ORDER BY ALL"
    )
    # total real fica só na memória para conferência; nunca é exportado por célula
    total = con.execute("SELECT sum(n) FROM _p").fetchone()[0]
    sup = con.execute("SELECT count(*), coalesce(sum(n), 0) FROM _p WHERE sup").fetchone()
    publicado = con.execute(f"SELECT coalesce(sum(qtd_registros), 0) FROM {destino}").fetchone()[0]
    con.execute("DROP TABLE _p")
    stats.update({
        "limiar": limiar,
        "celulas_publicadas": con.execute(f"SELECT count(*) FROM {destino}").fetchone()[0],
        "celulas_suprimidas": sup[0],
        "celulas_supressao_primaria": primarias,
        "celulas_supressao_secundaria": secundarias,
        "registros_suprimidos": sup[1],
        "registros_total": total,
        "registros_publicados": publicado,
        "pct_publicado": round(100 * publicado / total, 3) if total else None,
    })
    return stats


def executar(con: duckdb.DuckDBPyConnection, pasta_saida, limiar: int = LIMIAR) -> dict:
    """Gera e exporta os agregados protegidos a partir da tabela agregado_base."""
    resultado = {}
    for nome, spec in TABELAS.items():
        resultado[nome] = proteger(con, "agregado_base", nome, spec["dimensoes"], spec["etapas"], limiar)
        # CSV para Looker Studio e Power BI: vírgula, UTF-8 sem BOM, ponto decimal, aspas só quando
        # necessário (ex.: "Outros países (Europa)" não precisa; nomes com vírgula, sim)
        con.execute(
            f"COPY {nome} TO {lit((Path(pasta_saida) / f'{nome}.csv').as_posix())} "
            "(HEADER, DELIMITER ',', QUOTE '\"')"
        )
    return resultado


def escrever_metadados(pasta_saida, manifesto: dict, stats: dict) -> Path:
    """Grava publicacao/metadados.json: procedência e resultado do controle de divulgação."""
    meta = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "limiar_k": LIMIAR,
        "regra": "Nenhuma célula publicada tem de 1 a 4 registros. Ver src/sismigra/divulgacao.py.",
        "formato": {"separador": ",", "codificacao": "UTF-8 sem BOM", "decimal": ".", "nulo": "vazio",
                    "booleano": "true/false"},
        "fontes": [
            {"arquivo": a["arquivo_original"], "sha256": a["sha256"], "ano": a["ano"],
             "cobertura": a["cobertura"], "distribuidor": a["distribuidor"]}
            for a in manifesto["arquivos"]
        ],
        "tabelas": {
            nome: {k: v for k, v in st.items() if k != "registros_total"} for nome, st in stats.items()
        },
    }
    destino = Path(pasta_saida) / "metadados.json"
    destino.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return destino
