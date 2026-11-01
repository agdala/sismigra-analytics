"""Camada bronze: guarda os arquivos originais sem alteração e registra a procedência.

Os arquivos do SISMIGRA são distribuídos pelo OBMigra/UnB em pastas do SharePoint que
exigem autenticação institucional. Por isso a entrada é manual: o usuário coloca os ZIPs
(ou CSVs) em data/landing/ e a bronze:

1. calcula o SHA-256 de cada arquivo;
2. copia o arquivo, byte a byte, para data/bronze/originais/;
3. extrai os CSVs para data/bronze/extraidos/ (o ZIP original é preservado);
4. registra no manifesto: arquivo, hash, tamanho, data de ingestão (UTC), URL de origem
   e cobertura (de ref/fontes.csv).

É idempotente: um arquivo com hash já registrado não é reprocessado.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .config import Config

BLOCO = 8 * 1024 * 1024


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(BLOCO), b""):
            h.update(bloco)
    return h.hexdigest()


def carregar_fontes(cfg: Config) -> dict[str, dict]:
    with (cfg.ref / "fontes.csv").open(encoding="utf-8") as f:
        return {r["arquivo_csv"]: r for r in csv.DictReader(f, delimiter=";")}


def carregar_manifesto(cfg: Config) -> dict:
    if cfg.manifesto.exists():
        return json.loads(cfg.manifesto.read_text(encoding="utf-8"))
    return {"arquivos": []}


def _extrair_csvs(origem: Path, destino_dir: Path, nome_original: str) -> list[Path]:
    destino_dir.mkdir(parents=True, exist_ok=True)
    if origem.suffix.lower() == ".csv":
        destino = destino_dir / nome_original
        shutil.copyfile(origem, destino)
        return [destino]
    extraidos = []
    with zipfile.ZipFile(origem) as z:
        for membro in z.namelist():
            if not membro.lower().endswith(".csv"):
                continue
            destino = destino_dir / Path(membro).name  # descarta subpastas do ZIP
            with z.open(membro) as src, destino.open("wb") as dst:
                shutil.copyfileobj(src, dst, BLOCO)
            extraidos.append(destino)
    return extraidos


def executar(cfg: Config) -> dict:
    """Ingere os arquivos novos de cfg.entrada e devolve o manifesto atualizado."""
    cfg.criar_pastas()
    fontes = carregar_fontes(cfg)
    manifesto = carregar_manifesto(cfg)
    conhecidos = {a["sha256"] for a in manifesto["arquivos"]}
    originais = cfg.bronze / "originais"
    originais.mkdir(parents=True, exist_ok=True)

    candidatos = sorted(p for p in cfg.entrada.iterdir() if p.suffix.lower() in (".zip", ".csv"))
    if not candidatos and not manifesto["arquivos"]:
        raise FileNotFoundError(
            f"Nenhum ZIP ou CSV em {cfg.entrada}. Baixe os arquivos do SISMIGRA e coloque-os nessa pasta."
        )

    for arq in candidatos:
        h = sha256(arq)
        if h in conhecidos:
            continue
        destino = originais / f"{h[:12]}_{arq.name}"
        shutil.copyfile(arq, destino)
        if sha256(destino) != h:
            raise IOError(f"Cópia corrompida: {arq.name}")
        csvs = _extrair_csvs(destino, cfg.bronze / "extraidos" / h[:12], arq.name)
        for c in csvs:
            fonte = fontes.get(c.name, {})
            manifesto["arquivos"].append({
                "arquivo_original": arq.name,
                "sha256": h,
                "tamanho_bytes": arq.stat().st_size,
                "csv": c.name,
                "csv_sha256": sha256(c),
                "caminho_bronze": c.relative_to(cfg.dados).as_posix(),
                "ingerido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "url_origem": fonte.get("url_origem"),
                "distribuidor": fonte.get("distribuidor"),
                "ano": int(fonte["ano"]) if fonte.get("ano") else None,
                "cobertura": fonte.get("cobertura"),
                "ano_completo": fonte.get("ano_completo") == "true" if fonte else None,
            })
        conhecidos.add(h)

    cfg.manifesto.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifesto
