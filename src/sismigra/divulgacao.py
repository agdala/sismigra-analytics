"""Controle de divulgação dos agregados publicados no Looker Studio.

Regra: nenhuma célula publicada pode ter de 1 a 4 registros (limiar k = 5).

Supressão simples (apagar as células pequenas) esconderia cerca de 7% dos registros e
distorceria os totais. Por isso o método tem duas fases:

1. Agrupamento progressivo: as células abaixo do limiar têm atributos de menor prioridade
   trocados por "Agrupado", em etapas, e são somadas de novo. Atributos de maior valor
   analítico (ano, UF, país) são os últimos a serem agrupados.
2. Supressão residual: o que continuar abaixo do limiar recebe qtd_registros nulo e
   suprimido = true. A linha é mantida para indicar que existe uma célula pequena.

Cada linha publicada traz nivel_agrupamento: 0 = sem alteração; N = agrupada na etapa N.

Para separar os cruzamentos mais sensíveis, são publicadas duas tabelas:
  agregado_looker_nacionalidade.csv  ano x país x perfil x amparo (sem território)
  agregado_looker_territorio.csv     ano x UF x perfil x amparo (sem país)
"""

from __future__ import annotations

import duckdb

from .silver import lit

LIMIAR = 5

COMUNS = [
    "ano_registro", "cobertura", "ano_completo", "sexo", "faixa_etaria", "ordem_faixa_etaria",
    "categoria_ampla", "subgrupo_protecao", "tipologia_ajustada", "status_ativo",
]
PERFIL = [("sexo", "'Agrupado'"), ("faixa_etaria", "'Agrupada'"), ("ordem_faixa_etaria", "9"),
          ("status_ativo", "NULL")]

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
    con.execute(
        f"CREATE OR REPLACE TABLE {destino} AS SELECT {dims}, "
        f"CASE WHEN n >= {limiar} THEN n END AS qtd_registros, nivel AS nivel_agrupamento, "
        f"n < {limiar} AS suprimido FROM _p ORDER BY ALL"
    )
    # total real fica só na memória para conferência; nunca é exportado por célula
    total = con.execute("SELECT sum(n) FROM _p").fetchone()[0]
    sup = con.execute(f"SELECT count(*), coalesce(sum(n), 0) FROM _p WHERE n < {limiar}").fetchone()
    publicado = con.execute(f"SELECT coalesce(sum(qtd_registros), 0) FROM {destino}").fetchone()[0]
    con.execute("DROP TABLE _p")
    stats.update({
        "limiar": limiar,
        "celulas_publicadas": con.execute(f"SELECT count(*) FROM {destino}").fetchone()[0],
        "celulas_suprimidas": sup[0],
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
        con.execute(f"COPY {nome} TO {lit((pasta_saida / f'{nome}.csv').as_posix())} (HEADER, DELIMITER ',')")
    return resultado
