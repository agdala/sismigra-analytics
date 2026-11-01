"""Comando único do pipeline: bronze, prata, ouro e relatório de qualidade.

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

from . import bronze, gold, quality, silver
from . import divulgacao as divulgacao_mod
from .config import Config


def executar(cfg: Config) -> dict:
    inicio = time.time()
    print("[1/4] Bronze: ingestão dos arquivos originais")
    manifesto = bronze.executar(cfg)
    print(f"      {len(manifesto['arquivos'])} arquivo(s) no manifesto")

    con = duckdb.connect()
    con.execute("SET enable_progress_bar = false")
    print("[2/4] Prata: contrato de layout, padronização e regras de qualidade")
    res = silver.executar(cfg, manifesto, con)

    print("[3/4] Ouro: esquema estrela, Parquet e CSV")
    contagens = gold.executar(cfg, con)
    divulgacao = contagens.pop("_divulgacao")
    divulgacao_mod.escrever_metadados(cfg.publicacao, manifesto, divulgacao)
    for t, n in contagens.items():
        print(f"      {t}: {n:,} linhas".replace(",", "."))
    for t, st in divulgacao.items():
        print(f"      {t}: {st['pct_publicado']}% dos registros publicados, "
              f"{st['celulas_suprimidas']} célula(s) suprimida(s)")
    print(f"      agregados publicáveis em: {cfg.publicacao}")

    print("[4/4] Relatório de qualidade")
    rel = quality.calcular(con, res["leitura"], divulgacao)
    quality.escrever(cfg, rel)
    t = rel["totais"]
    print(f"      lidas {t['lidas']:,} | aceitas {t['aceitas']:,} | rejeitadas {t['rejeitadas']:,}".replace(",", "."))
    print(f"      relatório: {cfg.relatorios / 'relatorio_qualidade.md'}")
    print(f"Concluído em {time.time() - inicio:.1f}s")
    con.close()
    return {"manifesto": manifesto, "contagens": contagens, "divulgacao": divulgacao, "qualidade": rel}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", type=Path, help="pasta com os ZIPs/CSVs do SISMIGRA (padrão: data/landing)")
    a = ap.parse_args(argv)
    cfg = Config() if a.entrada is None else replace(Config(), entrada=a.entrada)
    try:
        executar(cfg)
    except (FileNotFoundError, silver.ErroContrato) as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
