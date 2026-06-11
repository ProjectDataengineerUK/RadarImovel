"""Unit tests for each risk dimension with mocked sources."""
from datetime import date
from unittest.mock import MagicMock

import pytest

from app.risk.schemas import DimensionScore


class FakeCnj:
    def __init__(self, processos=None):
        self._processos = processos or []

    def search(self, **kwargs):
        return self._processos


class FakeIbama:
    def __init__(self, layers=None):
        self._layers = layers or []

    def contains_point(self, lat, lng, layer_types=None):
        return self._layers


class FakeCemaden:
    def __init__(self, zones=None):
        self._zones = zones or []

    def risk_zones(self, lat, lng):
        return self._zones


class FakeTransp:
    def __init__(self, result=None):
        self._result = result

    def get_iptu_debt(self, **kwargs):
        return self._result


class FakeIbge:
    def __init__(self, stats=None):
        self._stats = stats

    def get_stats(self, ibge_code):
        return self._stats


class FakeIpea:
    def __init__(self, rate=None):
        self._rate = rate

    def get_homicide_rate(self, ibge_code):
        return self._rate


class FakeFipe:
    def __init__(self, price=None):
        self._price = price

    def get_price_per_sqm(self, city, state):
        return self._price


class FakeReceita:
    def __init__(self, data=None):
        self._data = data

    def get_cnpj(self, cnpj):
        return self._data


def test_juridico_no_processos():
    from app.risk.dimensions.juridico import score_juridico
    dim = score_juridico("", "Rua A", "SP", "SP", FakeCnj([]))
    assert dim.raw_points == 0.0
    assert not dim.partial


def test_juridico_com_processos_ativos():
    from app.risk.dimensions.juridico import score_juridico
    processos = [
        {"numero": "1", "classe": "Execução Fiscal", "status": "ativo", "tribunal": "TJSP"},
        {"numero": "2", "classe": "Inventário", "status": "ativo", "tribunal": "TJSP"},
    ]
    dim = score_juridico("12345678000100", "Rua A", "SP", "SP", FakeCnj(processos))
    assert dim.raw_points > 0
    assert len(dim.indicators) >= 2
    assert any(ind.code == "A2" for ind in dim.indicators)


def test_fundiario_inside_app():
    from app.risk.dimensions.fundiario import score_fundiario
    dim = score_fundiario(-23.55, -46.60, None, FakeIbama(["APP"]), FakeCemaden([]))
    assert dim.raw_points >= 50
    assert any("APP" in ind.code for ind in dim.indicators)


def test_fundiario_inside_cemaden_zone():
    from app.risk.dimensions.fundiario import score_fundiario
    dim = score_fundiario(-23.55, -46.60, None, FakeIbama([]), FakeCemaden(["deslizamento"]))
    assert dim.raw_points == 25.0


def test_fundiario_no_lat_lng():
    from app.risk.dimensions.fundiario import score_fundiario
    dim = score_fundiario(None, None, None, FakeIbama([]), FakeCemaden([]))
    assert dim.partial is True
    assert dim.raw_points == 0.0


def test_fiscal_sem_divida():
    from app.risk.dimensions.fiscal import score_fiscal
    dim = score_fiscal("Rua A", "SP", "SP", 400_000, None, FakeTransp({"has_debt": False}))
    assert dim.raw_points == 0.0


def test_fiscal_com_divida_alta():
    from app.risk.dimensions.fiscal import score_fiscal
    dim = score_fiscal(
        "Rua A", "SP", "SP", 400_000, None,
        FakeTransp({"has_debt": True, "debt_ratio": 0.35}),
    )
    assert dim.raw_points == 60.0


def test_fiscal_partial_when_source_fails():
    from app.risk.dimensions.fiscal import score_fiscal
    dim = score_fiscal("Rua A", "SP", "SP", 400_000, None, FakeTransp(None))
    assert dim.partial is True


def test_socioeconomico_low_idh():
    from app.risk.dimensions.socioeconomico import score_socioeconomico
    stats = {"idh": 0.600, "homicide_rate": None, "population_2022": 100_000, "population_2010": 100_000, "vacancy_rate": None}
    dim = score_socioeconomico("3550308", FakeIbge(stats), FakeIpea(None))
    assert any(ind.code == "E1" for ind in dim.indicators)
    assert dim.raw_points >= 30.0


def test_socioeconomico_high_homicide():
    from app.risk.dimensions.socioeconomico import score_socioeconomico
    stats = {"idh": 0.800, "homicide_rate": None, "population_2022": 100_000, "population_2010": 100_000, "vacancy_rate": None}
    dim = score_socioeconomico("3550308", FakeIbge(stats), FakeIpea(35.0))
    assert any(ind.code == "E4" for ind in dim.indicators)


def test_mercado_above_market():
    from app.risk.dimensions.mercado import score_mercado
    dim = score_mercado("São Paulo", "SP", 660_000, 100, FakeFipe(5000.0))
    assert dim.raw_points == 40.0
    assert not dim.partial


def test_mercado_partial_when_fipe_fails():
    from app.risk.dimensions.mercado import score_mercado
    dim = score_mercado("SP", "SP", 300_000, 60, FakeFipe(None))
    assert dim.partial is True
