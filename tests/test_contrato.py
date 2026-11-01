import pytest

from sismigra.silver import ErroContrato, validar_contrato
from conftest import CAB_2025, CAB_2026


def test_layouts_2021_2025_e_2026_aceitos():
    validar_contrato("a.csv", CAB_2025.split(";"))
    validar_contrato("b.csv", CAB_2026.split(";"))


def test_coluna_ausente_falha():
    cols = [c for c in CAB_2025.split(";") if c != "AMPARO"]
    with pytest.raises(ErroContrato, match="colunas ausentes"):
        validar_contrato("x.csv", cols)


def test_duas_colunas_de_idade_falha():
    with pytest.raises(ErroContrato, match="exatamente uma"):
        validar_contrato("x.csv", CAB_2025.split(";") + ["IDADE"])


def test_coluna_nova_falha():
    with pytest.raises(ErroContrato, match="colunas novas"):
        validar_contrato("x.csv", CAB_2025.split(";") + ["NOVA_COLUNA"])
