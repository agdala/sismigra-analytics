"""Comando único do pipeline: bronze (Python), transformação (dbt), publicação protegida (Python).

Etapas:
  1. bronze      ingestão dos arquivos originais com hash e manifesto (Python)
  2. carga       contrato de layout e carga das fontes bronze no DuckDB (Python)
  3. dbt build   seeds, staging, intermediate, marts e testes (dbt)
  4. exportação  esquema estrela em Parquet e CSV, só para uso interno (Python)
  5. divulgação  agregados protegidos (k = 5) em publicacao/ (Python)
  6. qualidade   relatório de qualidade (Python)

Uso:
  python -m sismigra.pipeline                 # usa data/landing/
  python -m sismigra.pipeline --entrada PASTA # outra pasta de entrada
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace
from pathlib import Path

import duckdb

from . import bronze, carga, dbt_runner, divulgacao, exportacao, quality
from .config import Config


def _conectar(cfg: Config, modelos_dbt: bool = False) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(cfg.banco))
    con.execute("SET enable_progress_bar = false")
    if modelos_dbt:
        # nomes sem schema (ex.: fato_registro) resolvem para os modelos criados pelo dbt
        con.execute("SET search_path = 'marts,intermediate,staging,ref,bronze,main'")
    return con


def executar(cfg: Config, silencioso_dbt: bool = False) -> dict:
    inicio = time.time()
    cfg.criar_pastas()
    print("[1/6] Bronze: ingestão dos arquivos originais")
    manifesto = bronze.executar(cfg)
    print(f"      {len(manifesto['arquivos'])} arquivo(s) no manifesto")

    print("[2/6] Carga: contrato de layout e fontes bronze no DuckDB")
    con = _conectar(cfg)
    leitura = carga.executar(cfg, manifesto, con)
    con.close()   # o dbt abre o mesmo arquivo

    print("[3/6] dbt build: seeds, modelos e testes")
    dbt_runner.executar(cfg, "build", silencioso=silencioso_dbt)

    con = _conectar(cfg, modelos_dbt=True)
    print("[4/6] Exportação do esquema estrela (uso interno)")
    contagens = exportacao.executar(cfg, con)
    for t, n in contagens.items():
        print(f"      {t}: {n:,} linhas".replace(",", "."))

    print("[5/6] Controle de divulgação: agregados protegidos em publicacao/")
    estat = divulgacao.executar(con, cfg.publicacao)
    divulgacao.escrever_metadados(cfg.publicacao, manifesto, estat)
    for t, st in estat.items():
        contagens[t] = st["celulas_publicadas"]
        print(f"      {t}: {st['pct_publicado']}% dos registros publicados, "
              f"{st['celulas_suprimidas']} célula(s) suprimida(s)")

    print("[6/6] Relatório de qualidade")
    rel = quality.calcular(con, leitura, estat)
    quality.escrever(cfg, rel)
    t = rel["totais"]
    print(f"      lidas {t['lidas']:,} | aceitas {t['aceitas']:,} | rejeitadas {t['rejeitadas']:,}".replace(",", "."))
    print(f"      relatório: {cfg.relatorios / 'relatorio_qualidade.md'}")
    print(f"Concluído em {time.time() - inicio:.1f}s")
    return {"manifesto": manifesto, "contagens": contagens, "divulgacao": estat, "qualidade": rel,
            "leitura": leitura, "con": con}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", type=Path, help="pasta com os ZIPs/CSVs do SISMIGRA (padrão: data/landing)")
    a = ap.parse_args(argv)
    cfg = Config() if a.entrada is None else replace(Config(), entrada=a.entrada)
    try:
        res = executar(cfg)
        res["con"].close()
    except (FileNotFoundError, carga.ErroContrato, dbt_runner.ErroDbt) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
