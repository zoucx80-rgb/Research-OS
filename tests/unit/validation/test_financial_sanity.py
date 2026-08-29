import importlib
import importlib.util


def _load(name: str):
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, f"missing required module {name}"
    return importlib.import_module(name)


def test_gross_profit_scale_corruption_fails():
    m = _load("research_os.validation.financial")
    result = m.FinancialSanityValidator().check_gross_profit(
        revenue=655.25, revenue_unit="亿元",
        cogs=634.01, cogs_unit="亿元",
        declared_gross_profit=2.123, declared_unit="亿元",
    )
    assert result.status == "FAIL"
    assert abs(result.expected_value / 100_000_000 - 21.24) < 0.01


def test_gross_margin_inconsistent_with_profit_fails():
    m = _load("research_os.validation.financial")
    result = m.FinancialSanityValidator().check_gross_margin(
        revenue=655.25, revenue_unit="亿元",
        gross_profit=2.123, gross_profit_unit="亿元",
        declared_margin=0.0324,
    )
    assert result.status == "FAIL"


def test_market_cap_scale_corruption_fails():
    m = _load("research_os.validation.financial")
    result = m.FinancialSanityValidator().check_market_cap(
        shares_outstanding=759_900_097,
        price=23.0,
        declared_market_cap=16.0,
        declared_unit="亿元",
    )
    assert result.status == "FAIL"


def test_yoy_mismatch_fails():
    m = _load("research_os.validation.financial")
    result = m.FinancialSanityValidator().check_yoy(current=120.0, previous=100.0, declared_growth=0.12)
    assert result.status == "FAIL"
    assert abs(result.expected_value - 0.20) < 1e-9


def test_same_metric_same_period_scope_version_conflict_fails():
    m = _load("research_os.validation.financial")
    Observation = m.FinancialMetricObservation
    observations = [
        Observation(metric="inventory", period="2026H1", scope="consolidated", version="reported", value=115.2, unit="亿元", evidence_ids=["ev1"]),
        Observation(metric="inventory", period="2026H1", scope="consolidated", version="reported", value=11.52, unit="亿元", evidence_ids=["ev2"]),
    ]
    result = m.FinancialSanityValidator().check_consistency(observations)
    assert result.status == "FAIL"
    assert any("scale" in error.lower() or "conflict" in error.lower() for error in result.errors)


def test_supported_chinese_units_normalize_to_yuan():
    m = _load("research_os.validation.financial")
    assert m.normalize_to_yuan(1, "元") == 1
    assert m.normalize_to_yuan(1, "千元") == 1_000
    assert m.normalize_to_yuan(1, "万元") == 10_000
    assert m.normalize_to_yuan(1, "百万元") == 1_000_000
    assert m.normalize_to_yuan(1, "亿元") == 100_000_000
