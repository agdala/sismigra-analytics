"""Etapa 0: inventário estrutural dos arquivos do SISMIGRA.

Lê um arquivo CSV, um ZIP ou uma pasta com esses arquivos e gera um
inventário das colunas reais (tipos inferidos, ausentes, cardinalidade e
valores mais frequentes das colunas categóricas). O objetivo é definir o
modelo de dados a partir do que existe de fato, sem inventar colunas.

Saída (pasta reports/inventario/ por padrão):
  - inventario.json : estrutura completa, legível por máquina
  - inventario.md   : resumo legível para revisão

O inventário não copia linhas dos microdados: apenas estatísticas por coluna
e, para colunas de baixa cardinalidade, as categorias com suas frequências.

Uso:
  python scripts/etapa0_inventario.py CAMINHO [--saida PASTA] [--max-categorias N]

Exemplo (Windows):
  python scripts\\etapa0_inventario.py "C:\\Users\\voce\\Documentos\\sismigra"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

AMOSTRA_BYTES = 1024 * 1024  # 1 MB para detectar delimitador
BLOCO = 8 * 1024 * 1024


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(BLOCO), b""):
            h.update(bloco)
    return h.hexdigest()


def detectar_codificacao(caminho: Path) -> str:
    """Retorna 'utf-8' se o arquivo inteiro decodifica como UTF-8; senão 'cp1252'."""
    import codecs

    dec = codecs.getincrementaldecoder("utf-8")(errors="strict")
    try:
        with caminho.open("rb") as f:
            for bloco in iter(lambda: f.read(BLOCO), b""):
                dec.decode(bloco)
            dec.decode(b"", final=True)
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


def para_utf8(caminho: Path, codificacao: str, destino_dir: Path) -> Path:
    """Converte para UTF-8 em arquivo temporário (DuckDB lê UTF-8 nativamente)."""
    if codificacao == "utf-8":
        return caminho
    destino = destino_dir / (caminho.stem + ".utf8.csv")
    with caminho.open("r", encoding=codificacao, newline="") as src, destino.open(
        "w", encoding="utf-8", newline=""
    ) as dst:
        for bloco in iter(lambda: src.read(BLOCO), ""):
            dst.write(bloco)
    return destino


def detectar_delimitador(caminho_utf8: Path) -> str:
    with caminho_utf8.open("r", encoding="utf-8-sig", newline="") as f:
        amostra = f.read(AMOSTRA_BYTES)
    try:
        return csv.Sniffer().sniff(amostra, delimiters=";,|\t").delimiter
    except csv.Error:
        return ";"


def q(nome: str) -> str:
    return '"' + nome.replace('"', '""') + '"'


def perfilar_csv(caminho: Path, origem: str, tmp: Path, max_cat: int) -> dict:
    codificacao = detectar_codificacao(caminho)
    caminho_utf8 = para_utf8(caminho, codificacao, tmp)
    delim = detectar_delimitador(caminho_utf8)

    with caminho_utf8.open("r", encoding="utf-8-sig", newline="") as f:
        cabecalho_bruto = f.readline().rstrip("\r\n")

    con = duckdb.connect()
    def lit(s: str) -> str:
        return "'" + s.replace("'", "''") + "'"

    # Tabela em memória: o arquivo é lido uma única vez para todas as métricas.
    con.execute(
        f"CREATE TABLE t AS SELECT * FROM read_csv({lit(caminho_utf8.as_posix())}, "
        f"delim={lit(delim)}, header=true, all_varchar=true, quote='\"', "
        "strict_mode=false, null_padding=true)"
    )
    colunas = [r[0] for r in con.execute("DESCRIBE t").fetchall()]
    n_linhas = con.execute("SELECT count(*) FROM t").fetchone()[0]
    n_distintas = con.execute("SELECT count(*) FROM (SELECT DISTINCT * FROM t)").fetchone()[0]

    perfis = []
    for c in colunas:
        col = q(c)
        nulos, vazios, distintos, min_len, max_len, n_int, n_dec, n_data = con.execute(
            f"""
            SELECT
              count(*) FILTER (WHERE {col} IS NULL),
              count(*) FILTER (WHERE {col} IS NOT NULL AND trim({col}) = ''),
              count(DISTINCT {col}),
              min(length({col})),
              max(length({col})),
              count(*) FILTER (WHERE TRY_CAST(trim({col}) AS BIGINT) IS NOT NULL),
              count(*) FILTER (WHERE TRY_CAST(replace(trim({col}), ',', '.') AS DOUBLE) IS NOT NULL),
              count(*) FILTER (WHERE
                  TRY_STRPTIME(trim({col}), '%d/%m/%Y') IS NOT NULL
                  OR TRY_STRPTIME(trim({col}), '%Y-%m-%d') IS NOT NULL
                  OR TRY_STRPTIME(trim({col}), '%d/%m/%Y %H:%M:%S') IS NOT NULL)
            FROM t
            """
        ).fetchone()
        preenchidos = n_linhas - nulos - vazios
        tipo = "texto"
        if preenchidos:
            if n_data == preenchidos:
                tipo = "data"
            elif n_int == preenchidos:
                tipo = "inteiro"
            elif n_dec == preenchidos:
                tipo = "decimal"

        perfil = {
            "coluna": c,
            "tipo_inferido": tipo,
            "nulos": nulos,
            "vazios": vazios,
            "pct_ausente": round(100 * (nulos + vazios) / n_linhas, 2) if n_linhas else None,
            "distintos": distintos,
            "tamanho_min": min_len,
            "tamanho_max": max_len,
        }
        limite = max_cat if distintos <= max_cat else 5
        top = con.execute(
            f"SELECT {col} AS v, count(*) AS n FROM t GROUP BY 1 ORDER BY n DESC, v LIMIT {limite}"
        ).fetchall()
        perfil["categorias" if distintos <= max_cat else "mais_frequentes"] = [
            {"valor": v, "n": n} for v, n in top
        ]
        if tipo in ("inteiro", "decimal"):
            mn, mx, soma = con.execute(
                f"SELECT min(x), max(x), sum(x) FROM (SELECT TRY_CAST(replace(trim({col}), ',', '.') AS DOUBLE) x FROM t)"
            ).fetchone()
            perfil.update({"min": mn, "max": mx, "soma": soma})
        if tipo == "data":
            mn, mx = con.execute(
                f"""SELECT min(d), max(d) FROM (SELECT COALESCE(
                      TRY_STRPTIME(trim({col}), '%d/%m/%Y'),
                      TRY_STRPTIME(trim({col}), '%Y-%m-%d'),
                      TRY_STRPTIME(trim({col}), '%d/%m/%Y %H:%M:%S')) d FROM t)"""
            ).fetchone()
            perfil.update({"min": str(mn), "max": str(mx)})
        perfis.append(perfil)
    con.close()

    return {
        "arquivo": caminho.name,
        "origem": origem,
        "tamanho_bytes": caminho.stat().st_size,
        "sha256": sha256(caminho),
        "codificacao": codificacao,
        "delimitador": delim,
        "cabecalho_bruto": cabecalho_bruto,
        "linhas": n_linhas,
        "linhas_distintas": n_distintas,
        "linhas_duplicadas_exatas": n_linhas - n_distintas,
        "n_colunas": len(colunas),
        "colunas": perfis,
    }


def coletar(caminho: Path, tmp: Path) -> list[tuple[Path, str]]:
    """Retorna (csv_local, origem) para cada CSV encontrado, extraindo ZIPs."""
    alvos: list[Path] = []
    if caminho.is_dir():
        alvos = sorted(p for p in caminho.rglob("*") if p.suffix.lower() in (".csv", ".zip"))
    else:
        alvos = [caminho]
    saida = []
    for p in alvos:
        if p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p) as z:
                for m in z.namelist():
                    if m.lower().endswith(".csv"):
                        destino = tmp / Path(m).name
                        with z.open(m) as src, destino.open("wb") as dst:
                            for bloco in iter(lambda: src.read(BLOCO), b""):
                                dst.write(bloco)
                        saida.append((destino, f"{p.name}::{m}"))
        else:
            saida.append((p, p.name))
    return saida


def escrever_md(inv: dict, destino: Path) -> None:
    linhas = [
        "# Inventário de colunas: SISMIGRA (Etapa 0)",
        "",
        f"Gerado em {inv['gerado_em']}.",
        "",
    ]
    for a in inv["arquivos"]:
        linhas += [
            f"## {a['origem']}",
            "",
            f"- Linhas: {a['linhas']:,} | colunas: {a['n_colunas']} | duplicadas exatas: {a['linhas_duplicadas_exatas']:,}",
            f"- Codificação: {a['codificacao']} | delimitador: `{a['delimitador']}` | tamanho: {a['tamanho_bytes']:,} bytes",
            f"- SHA-256: `{a['sha256']}`",
            f"- Cabeçalho bruto: `{a['cabecalho_bruto']}`",
            "",
            "| Coluna | Tipo inferido | % ausente | Distintos | Exemplos (valor: n) |",
            "|---|---|---|---|---|",
        ]
        for c in a["colunas"]:
            ex = c.get("categorias") or c.get("mais_frequentes") or []
            ex_txt = "; ".join(
                f"{'(nulo)' if e['valor'] is None else str(e['valor']).replace('|', '/')}: {e['n']}"
                for e in ex[:8]
            )
            linhas.append(
                f"| {c['coluna']} | {c['tipo_inferido']} | {c['pct_ausente']} | {c['distintos']:,} | {ex_txt} |"
            )
        linhas.append("")
    destino.write_text("\n".join(linhas), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("caminho", type=Path, help="CSV, ZIP ou pasta")
    ap.add_argument("--saida", type=Path, default=Path("reports/inventario"))
    ap.add_argument("--max-categorias", type=int, default=300,
                    help="lista todas as categorias de colunas com até N valores distintos")
    args = ap.parse_args(argv)

    if not args.caminho.exists():
        print(f"Caminho não encontrado: {args.caminho}", file=sys.stderr)
        return 1

    args.saida.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpd:
        tmp = Path(tmpd)
        arquivos = coletar(args.caminho, tmp)
        if not arquivos:
            print("Nenhum CSV ou ZIP encontrado.", file=sys.stderr)
            return 1
        inv = {
            "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "duckdb": duckdb.__version__,
            "arquivos": [],
        }
        for csv_path, origem in arquivos:
            print(f"Perfilando {origem} ...")
            inv["arquivos"].append(perfilar_csv(csv_path, origem, tmp, args.max_categorias))

    (args.saida / "inventario.json").write_text(
        json.dumps(inv, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    escrever_md(inv, args.saida / "inventario.md")
    print(f"Inventário salvo em {args.saida.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
