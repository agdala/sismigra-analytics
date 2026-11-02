"""Carga da camada bronze no DuckDB, como fontes do dbt.

Para cada CSV registrado no manifesto da bronze:
1. confere o contrato de colunas (falha cedo se o layout mudar);
2. carrega todas as colunas como texto, com número da linha, ano esperado e hash do arquivo,
   em bronze.registros_brutos;
3. separa as linhas malformadas (número de colunas errado) em bronze.linhas_malformadas;
4. espelha o manifesto em bronze.manifesto (procedência e data de ingestão, usada pelo
   teste de atualização do dbt).

Nenhuma transformação de negócio acontece aqui: ela fica nos modelos do dbt (dbt/models/).
"""

from __future__ import annotations

import duckdb

from .config import COLUNAS_COMUNS, COLUNAS_IDADE, Config


class ErroContrato(Exception):
    """O arquivo não segue o layout esperado do SISMIGRA."""


def lit(texto: str) -> str:
    return "'" + str(texto).replace("'", "''") + "'"


def validar_contrato(nome: str, colunas: list[str]) -> None:
    faltando = [c for c in COLUNAS_COMUNS if c not in colunas]
    idade = [c for c in COLUNAS_IDADE if c in colunas]
    extras = [c for c in colunas if c not in COLUNAS_COMUNS + COLUNAS_IDADE]
    problemas = []
    if faltando:
        problemas.append(f"colunas ausentes: {faltando}")
    if len(idade) != 1:
        problemas.append(f"esperada exatamente uma de {COLUNAS_IDADE}, encontrado {idade}")
    if extras:
        problemas.append(f"colunas novas não previstas: {extras}")
    if problemas:
        raise ErroContrato(
            f"{nome}: " + "; ".join(problemas)
            + ". Atualize src/sismigra/config.py e o dicionário de dados antes de processar."
        )


def _carregar_manifesto(con: duckdb.DuckDBPyConnection, manifesto: dict) -> None:
    con.execute("""
        CREATE OR REPLACE TABLE bronze.manifesto (
            arquivo_original VARCHAR, sha256 VARCHAR, tamanho_bytes BIGINT, csv VARCHAR,
            csv_sha256 VARCHAR, caminho_bronze VARCHAR, ingerido_em TIMESTAMPTZ, url_origem VARCHAR,
            distribuidor VARCHAR, ano INTEGER, cobertura VARCHAR, ano_completo BOOLEAN)""")
    for a in manifesto["arquivos"]:
        con.execute(
            "INSERT INTO bronze.manifesto VALUES (?, ?, ?, ?, ?, ?, CAST(? AS TIMESTAMPTZ), ?, ?, ?, ?, ?)",
            [a["arquivo_original"], a["sha256"], a["tamanho_bytes"], a["csv"], a["csv_sha256"],
             a["caminho_bronze"], a["ingerido_em"], a.get("url_origem"), a.get("distribuidor"),
             a.get("ano"), a.get("cobertura"), a.get("ano_completo")],
        )


def executar(cfg: Config, manifesto: dict, con: duckdb.DuckDBPyConnection) -> list[dict]:
    """Recria as tabelas do schema bronze e devolve as estatísticas de leitura por arquivo."""
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    colunas_bruto = COLUNAS_COMUNS + COLUNAS_IDADE
    con.execute(
        "CREATE OR REPLACE TABLE bronze.registros_brutos ("
        + ", ".join(f'"{c}" VARCHAR' for c in colunas_bruto)
        + ", arquivo_csv VARCHAR, linha_origem BIGINT, ano_arquivo INTEGER, sha12 VARCHAR)"
    )
    con.execute(
        "CREATE OR REPLACE TABLE bronze.linhas_malformadas "
        "(arquivo_csv VARCHAR, linha_origem BIGINT, ano_arquivo INTEGER, erro VARCHAR)"
    )
    _carregar_manifesto(con, manifesto)

    leitura = []
    for item in manifesto["arquivos"]:
        if item.get("ano") is None:
            raise ErroContrato(
                f"{item['csv']} não está em ref/fontes.csv. Registre ano, cobertura e URL de origem antes de processar."
            )
        caminho = (cfg.dados / item["caminho_bronze"]).as_posix()
        with open(caminho, encoding="utf-8-sig", newline="") as f:
            colunas = [c.strip().strip('"') for c in f.readline().rstrip("\r\n").split(";")]
        validar_contrato(item["csv"], colunas)
        # Layout explícito (sem detecção automática): todas as colunas como texto.
        tipos = "{" + ", ".join(f"{lit(c)}: 'VARCHAR'" for c in colunas) + "}"
        opcoes = f"delim=';', header=true, quote='\"', auto_detect=false, columns={tipos}"

        con.execute("DROP TABLE IF EXISTS _rej; DROP TABLE IF EXISTS _rej_scan")
        con.execute(
            f"CREATE OR REPLACE TEMP TABLE _arq AS SELECT *, row_number() OVER () AS linha_origem "
            f"FROM read_csv({lit(caminho)}, {opcoes}, ignore_errors=true, store_rejects=true, "
            f"rejects_table='_rej', rejects_scan='_rej_scan')"
        )
        selecao = ", ".join(f'"{c}"' if c in colunas else f'NULL AS "{c}"' for c in colunas_bruto)
        con.execute(
            f"INSERT INTO bronze.registros_brutos SELECT {selecao}, {lit(item['csv'])}, linha_origem, "
            f"{int(item['ano'])}, {lit(item['sha256'][:12])} FROM _arq"
        )
        n_malf = con.execute("SELECT count(DISTINCT line) FROM _rej").fetchone()[0]
        if n_malf:
            con.execute(
                f"INSERT INTO bronze.linhas_malformadas SELECT {lit(item['csv'])}, line - 1, {int(item['ano'])}, "
                "string_agg(error_message, ' | ') FROM _rej GROUP BY line"
            )
        lidas = con.execute("SELECT count(*) FROM _arq").fetchone()[0]
        con.execute("DROP TABLE _arq")
        leitura.append({"arquivo_csv": item["csv"], "ano": item["ano"], "lidas_validas": lidas, "malformadas": n_malf})
    return leitura
