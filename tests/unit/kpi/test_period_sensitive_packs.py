import pytest

from research_os.kpi.distributor import DistributorPack
from research_os.kpi.manufacturing import ManufacturingPack


def metrics(result):
    return {m.metric_id: m for m in result}


def test_distributor_h1_days_use_period_length_not_365():
    result = metrics(DistributorPack().calculate({
        "avg_ar": 100.0,
        "revenue": 1000.0,
        "avg_inventory": 200.0,
        "cogs": 900.0,
        "avg_ap": 150.0,
        "period_type": "H1",
        "period_days": 181,
    }))
    assert result["dso_days"].value == pytest.approx(100.0 / 1000.0 * 181)
    assert result["dio_days"].value == pytest.approx(200.0 / 900.0 * 181)
    assert result["dpo_days"].value == pytest.approx(150.0 / 900.0 * 181)
    assert result["ccc_days"].value == pytest.approx(
        result["dso_days"].value + result["dio_days"].value - result["dpo_days"].value
    )


def test_distributor_interim_period_without_length_stays_missing():
    result = metrics(DistributorPack().calculate({
        "avg_ar": 100.0,
        "revenue": 1000.0,
        "avg_inventory": 200.0,
        "cogs": 900.0,
        "avg_ap": 150.0,
        "period_type": "H1",
    }))
    assert result["dso_days"].value is None
    assert result["dso_days"].status == "missing"
    assert result["dso_days"].reason_code == "PERIOD_LENGTH_REQUIRED"


def test_distributor_exposes_period_and_annualized_inventory_turns():
    result = metrics(DistributorPack().calculate({
        "avg_ar": 100.0,
        "revenue": 1000.0,
        "avg_inventory": 200.0,
        "cogs": 900.0,
        "avg_ap": 150.0,
        "period_type": "H1",
        "period_days": 181,
    }))
    assert result["inventory_turns_period"].value == pytest.approx(4.5)
    assert result["inventory_turns_annualized"].value == pytest.approx(4.5 * 365 / 181)


def test_distributor_fy_without_period_days_keeps_annual_compatibility():
    result = metrics(DistributorPack().calculate({
        "avg_ar": 100.0,
        "revenue": 1000.0,
        "avg_inventory": 200.0,
        "cogs": 900.0,
        "avg_ap": 150.0,
        "period_type": "FY",
    }))
    assert result["dso_days"].value == pytest.approx(36.5)


def test_manufacturing_h1_turnover_days_use_same_period_contract():
    result = metrics(ManufacturingPack().calculate({
        "revenue": 1000.0,
        "net_profit_parent": 50.0,
        "assets_begin": 800.0,
        "assets_end": 900.0,
        "equity_begin": 400.0,
        "equity_end": 450.0,
        "ar_begin": 90.0,
        "ar_end": 110.0,
        "inventory_begin": 180.0,
        "inventory_end": 220.0,
        "cogs": 900.0,
        "period_type": "H1",
        "period_days": 181,
    }))
    assert result["ar_days"].value == pytest.approx(100.0 / 1000.0 * 181)
    assert result["inventory_days"].value == pytest.approx(200.0 / 900.0 * 181)
