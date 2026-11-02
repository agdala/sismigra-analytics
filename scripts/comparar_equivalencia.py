"""Compara as saídas do pipeline com dbt com as do pipeline anterior (SQL puro).

Entrada: uma pasta de referência com o Parquet de cada tabela do pipeline anterior
(tabelas/*.parquet) e os CSVs de publicacao/ gerados por ele (publicacao/*.csv).

Verificações, tabela por tabela:
  1. contagem de linhas;
  2. conteúdo linha a linha (diferença simétrica com EXCEPT ALL nos dois sentidos);
  3. totais de registros por ano, por país de nacionalidade e por UF (a partir do fato);
  4. CSVs de publicacao/ idênticos byte a byte (SHA-256).

Uso:
  python scripts/comparar_equivalencia.py PASTA_REFERENCIA [--saida docs/revisao/equivalencia_dbt.md]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from sismigra import divulgacao  # noqa: E402
from sismigra.config import Config  # noqa: E402

# tabela antiga -> objeto equivalente no banco do dbt
MAPA = {
    "prata": "intermediate.int_registros_enriquecidos",
    "rejeitados": "staging.stg_rejeitados",
    "fato_registro": "marts.fato_registro",
    "dim_tempo": "marts.dim_tempo",
    "dim_pais": "marts.dim_pais",
    "dim_localidade": "marts.dim_localidade",
    "dim_perfil": "marts.dim_perfil",
    "dim_amparo": "marts.dim_amparo",
    "dim_ocupacao": "marts.dim_ocupacao",
    "amparo_descricao_ano": "marts.amparo_descricao_ano",
    "agregado_base": "marts.agregado_base",
    "agregado_looker_nacionalidade": "agregado_looker_nacionalidade",
    "agregado_looker_territorio": "agregado_looker_territorio",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def comparar(ref: Path, cfg: Config, pasta_publicacao: Path) -> tuple[bool, list[str]]:
    con = duckdb.connect(str(cfg.banco), read_only=True)
    con.execute("SET enable_progress_bar = false")
    # agregados protegidos gerados a partir do modelo dbt, numa pasta temporária
    pasta_publicacao.mkdir(parents=True, exist_ok=True)
    divulgacao.executar(con, pasta_publicacao)

    ok = True
    L = ["| Tabela antiga | Modelo dbt | Linhas (antes) | Linhas (dbt) | Só antes | Só dbt | Resultado |",
         "|---|---|---|---|---|---|---|"]
    for antiga, nova in MAPA.items():
        arq = (ref / "tabelas" / f"{antiga}.parquet").as_posix()
        cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM '{arq}'").fetchall()]
        lista = ", ".join(f'"{c}"' for c in cols)
        n_ant = con.execute(f"SELECT count(*) FROM '{arq}'").fetchone()[0]
        n_nov = con.execute(f"SELECT count(*) FROM {nova}").fetchone()[0]
        so_ant = con.execute(
            f"SELECT count(*) FROM (SELECT {lista} FROM '{arq}' EXCEPT ALL SELECT {lista} FROM {nova})").fetchone()[0]
        so_nov = con.execute(
            f"SELECT count(*) FROM (SELECT {lista} FROM {nova} EXCEPT ALL SELECT {lista} FROM '{arq}')").fetchone()[0]
        igual = n_ant == n_nov and so_ant == 0 and so_nov == 0
        ok &= igual
        L.append(f"| `{antiga}` | `{nova}` | {n_ant:,} | {n_nov:,} | {so_ant} | {so_nov} | "
                 f"{'idêntica' if igual else '**DIFERENTE**'} |".replace(",", "."))

    # totais por ano, país e UF, recalculados a partir do fato e das dimensões de cada versão
    f_ant = lambda t: f"'{(ref / 'tabelas' / f'{t}.parquet').as_posix()}'"  # noqa: E731
    consultas = {
        "ano": ("SELECT f.sk_ano_registro k, count(*) n FROM {fato} f GROUP BY 1", {}),
        "país de nacionalidade": (
            "SELECT p.pais k, count(*) n FROM {fato} f JOIN {pais} p ON p.sk_pais = f.sk_pais_nacionalidade GROUP BY 1", {}),
        "UF": (
            "SELECT coalesce(l.uf_sigla, 'Não informado') k, count(*) n FROM {fato} f "
            "JOIN {loc} l ON l.sk_localidade = f.sk_localidade GROUP BY 1", {}),
    }
    L += ["", "| Total por | Grupos | Grupos com diferença | Resultado |", "|---|---|---|---|"]
    for nome, (sql, _) in consultas.items():
        a = dict(con.execute(sql.format(fato=f_ant("fato_registro"), pais=f_ant("dim_pais"),
                                        loc=f_ant("dim_localidade"))).fetchall())
        b = dict(con.execute(sql.format(fato="marts.fato_registro", pais="marts.dim_pais",
                                        loc="marts.dim_localidade")).fetchall())
        dif = [k for k in set(a) | set(b) if a.get(k) != b.get(k)]
        ok &= not dif
        L.append(f"| {nome} | {len(a)} | {len(dif)} | {'idênticos' if not dif else '**DIFERENTES**'} |")

    L += ["", "| Arquivo de publicacao/ | SHA-256 (antes) | SHA-256 (dbt) | Resultado |", "|---|---|---|---|"]
    for csv in sorted((ref / "publicacao").glob("*.csv")):
        h1, h2 = sha(csv), sha(pasta_publicacao / csv.name)
        ok &= h1 == h2
        L.append(f"| `{csv.name}` | `{h1[:16]}` | `{h2[:16]}` | {'idêntico' if h1 == h2 else '**DIFERENTE**'} |")
    con.close()
    return ok, L


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("referencia", type=Path)
    ap.add_argument("--saida", type=Path)
    ap.add_argument("--publicacao-temp", type=Path, default=Path("data/equivalencia_publicacao"))
    a = ap.parse_args(argv)
    ok, linhas = comparar(a.referencia, Config(), a.publicacao_temp)
    texto = "\n".join(linhas)
    print(texto)
    print("\nRESULTADO:", "IDÊNTICO" if ok else "HÁ DIFERENÇAS")
    if a.saida:
        cab = [
            "# Equivalência: pipeline com dbt versus pipeline anterior (SQL puro)",
            "",
            f"Comparação executada em {datetime.now(timezone.utc).isoformat(timespec='seconds')} (UTC) "
            "com os dados reais do SISMIGRA 2021 a 2026 (1.361.391 registros), por "
            "`scripts/comparar_equivalencia.py`.",
            "",
            "- **Linhas:** contagem de cada tabela.",
            "- **Só antes / Só dbt:** linhas presentes em uma versão e ausentes na outra "
            "(`EXCEPT ALL` nos dois sentidos, todas as colunas). Zero nos dois lados = conteúdo idêntico.",
            "- **Totais:** registros por ano, por país de nacionalidade e por UF.",
            "- **publicacao/:** os CSVs protegidos precisam ser idênticos byte a byte.",
            "",
            f"**Resultado: {'idêntico em todas as verificações' if ok else 'há diferenças'}.**",
            "",
        ]
        a.saida.write_text("\n".join(cab) + "\n" + texto + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
