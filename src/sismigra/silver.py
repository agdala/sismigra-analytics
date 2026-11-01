"""Camada prata: lê os CSVs da bronze, valida o contrato de layout e padroniza.

O SQL de transformação fica em sql/silver.sql. Este módulo:
1. confere o contrato de colunas de cada arquivo (falha cedo se o layout mudar);
2. carrega os CSVs como texto, com número da linha e ano esperado do arquivo;
3. separa linhas malformadas (número de colunas errado) como rejeição R00;
4. carrega as tabelas de referência e executa sql/silver.sql;
5. grava data/silver/registros.parquet e data/silver/rejeitados.parquet.
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


def carregar_referencias(con: duckdb.DuckDBPyConnection, cfg: Config) -> None:
    def ler(nome: str) -> str:
        return f"read_csv({lit((cfg.ref / nome).as_posix())}, delim=';', header=true, all_varchar=true)"

    con.execute(f"CREATE OR REPLACE TABLE ref_uf AS SELECT * FROM {ler('uf.csv')}")
    con.execute(
        "CREATE OR REPLACE TABLE ref_municipios AS SELECT *, "
        "regexp_replace(upper(strip_accents(municipio)), '[^A-Z]', '', 'g') AS nome_norm "
        f"FROM {ler('municipios_ibge.csv')}"
    )
    con.execute(f"CREATE OR REPLACE TABLE ref_excecoes AS SELECT * FROM {ler('excecoes_municipios.csv')}")
    con.execute(f"CREATE OR REPLACE TABLE ref_paises AS SELECT * FROM {ler('paises.csv')}")
    con.execute(
        f"CREATE OR REPLACE TABLE ref_amparos AS SELECT * REPLACE (CAST(codigo AS INTEGER) AS codigo) "
        f"FROM {ler('amparos.csv')}"
    )
    con.execute(
        "CREATE OR REPLACE TABLE ref_fontes AS SELECT * REPLACE (CAST(ano AS INTEGER) AS ano, "
        f"CAST(ano_completo AS BOOLEAN) AS ano_completo) FROM {ler('fontes.csv')}"
    )


def carregar_bruto(con: duckdb.DuckDBPyConnection, cfg: Config, manifesto: dict) -> list[dict]:
    """Carrega cada CSV da bronze na tabela `bruto`. Devolve estatísticas de leitura por arquivo."""
    con.execute("DROP TABLE IF EXISTS bruto")
    con.execute(
        "CREATE TABLE malformadas (arquivo_csv VARCHAR, linha_origem BIGINT, ano_arquivo INTEGER, erro VARCHAR)"
    )
    colunas_bruto = COLUNAS_COMUNS + COLUNAS_IDADE
    con.execute(
        "CREATE TABLE bruto (" + ", ".join(f'"{c}" VARCHAR' for c in colunas_bruto)
        + ", arquivo_csv VARCHAR, linha_origem BIGINT, ano_arquivo INTEGER, sha12 VARCHAR)"
    )
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
        selecao = ", ".join(f'"{c}"' if c in colunas else f"NULL AS \"{c}\"" for c in colunas_bruto)
        con.execute(
            f"INSERT INTO bruto SELECT {selecao}, {lit(item['csv'])}, linha_origem, {int(item['ano'])}, "
            f"{lit(item['sha256'][:12])} FROM _arq"
        )
        n_malf = con.execute("SELECT count(DISTINCT line) FROM _rej").fetchone()[0]
        if n_malf:
            con.execute(
                f"INSERT INTO malformadas SELECT {lit(item['csv'])}, line - 1, {int(item['ano'])}, "
                "string_agg(error_message, ' | ') FROM _rej GROUP BY line"
            )
        lidas = con.execute("SELECT count(*) FROM _arq").fetchone()[0]
        leitura.append({"arquivo_csv": item["csv"], "ano": item["ano"], "lidas_validas": lidas, "malformadas": n_malf})
    return leitura


def executar(cfg: Config, manifesto: dict, con: duckdb.DuckDBPyConnection | None = None) -> dict:
    cfg.criar_pastas()
    con = con or duckdb.connect()
    carregar_referencias(con, cfg)
    leitura = carregar_bruto(con, cfg, manifesto)
    con.execute((cfg.sql / "silver.sql").read_text(encoding="utf-8"))
    # linhas malformadas também são rejeições (R00)
    con.execute(
        "INSERT INTO rejeitados (arquivo_csv, linha_origem, ano_arquivo, regra) "
        "SELECT arquivo_csv, linha_origem, ano_arquivo, 'R00' FROM malformadas"
    )
    con.execute(f"COPY prata TO {lit((cfg.prata / 'registros.parquet').as_posix())} (FORMAT parquet)")
    con.execute(f"COPY rejeitados TO {lit((cfg.prata / 'rejeitados.parquet').as_posix())} (FORMAT parquet)")
    return {"leitura": leitura}
