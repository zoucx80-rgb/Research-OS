import pytest
from research_os.capital.engine import CapitalEfficiencyEngine

def test_roic_incremental_roic_and_iwcr():
    r=CapitalEfficiencyEngine().calculate({"nopat":12,"invested_capital_begin":90,"invested_capital_end":110,
        "nopat_prev":9,"invested_capital_prev":90,"delta_nwc":60,"delta_revenue":100})
    assert r.roic==pytest.approx(.12)
    assert r.incremental_roic==pytest.approx(.15)
    assert r.iwcr==pytest.approx(.60)

def test_growth_with_large_nwc_and_debt_increase_is_debt_funded():
    r=CapitalEfficiencyEngine().funding_loop({"delta_revenue":100,"delta_nwc":60,"delta_debt":55,"delta_equity":0,"operating_cash_flow":-20})
    assert r.funding_state=="debt_funded"
    assert "DEBT_FUNDS_NWC" in r.reason_codes

def test_growth_quality_exposes_components_without_unversioned_composite_score():
    c=CapitalEfficiencyEngine().growth_quality_components({
        "revenue_growth":.30,"margin_change":.01,"roic":.10,"cash_conversion":.8,
        "incremental_nwc_efficiency":.7,"leverage_deterioration":.1,"dilution":0.0})
    assert set(c)=={"growth","margin","roic","cash_conversion","incremental_nwc_efficiency","leverage_deterioration","dilution"}
    assert "score" not in c
