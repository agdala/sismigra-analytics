import json

import pytest

from sismigra import bronze
from sismigra.config import Config


def test_manifesto_registra_procedencia(execucao):
    arquivos = execucao["manifesto"]["arquivos"]
    assert {a["csv"] for a in arquivos} == {"teste_2025.csv", "teste_2026.csv"}
    for a in arquivos:
        assert len(a["sha256"]) == 64
        assert a["url_origem"].startswith("https://")
        assert a["ingerido_em"].endswith("+00:00")
        assert a["ano"] in (2025, 2026)


def test_original_preservado_byte_a_byte(execucao):
    cfg = execucao["cfg"]
    for a in execucao["manifesto"]["arquivos"]:
        copia = next((cfg.bronze / "originais").glob(f"{a['sha256'][:12]}_*"))
        assert bronze.sha256(copia) == a["sha256"]
        assert bronze.sha256(cfg.entrada / a["arquivo_original"]) == a["sha256"]


def test_csv_extraido_de_zip_com_subpasta(execucao):
    item = next(a for a in execucao["manifesto"]["arquivos"] if a["arquivo_original"].endswith(".zip"))
    assert item["csv"] == "teste_2025.csv"


def test_ingestao_idempotente(execucao):
    cfg = execucao["cfg"]
    antes = json.loads(cfg.manifesto.read_text(encoding="utf-8"))
    bronze.executar(cfg)
    depois = json.loads(cfg.manifesto.read_text(encoding="utf-8"))
    assert antes == depois


def test_entrada_vazia_falha_com_mensagem(tmp_path, ambiente):
    cfg = Config(entrada=tmp_path / "vazia", dados=tmp_path / "data", ref=ambiente.ref,
                 relatorios=tmp_path / "r", publicacao=tmp_path / "p")
    with pytest.raises(FileNotFoundError, match="Nenhum ZIP ou CSV"):
        bronze.executar(cfg)
