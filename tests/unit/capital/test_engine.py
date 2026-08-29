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
