import pytest
from research_os.capital.engine import CapitalEfficiencyEngine


def test_roic_incremental_roic_and_iwcr():
    r=CapitalEfficiencyEngine().calculate({"nopat":12,"invested_capital_begin":90,"invested_capital_end":110,
        "nopat_prev":9,"invested_capital_prev":90,"delta_nwc":60,"delta_revenue":100,
        "delta_nwc_comparison_basis":"2026_vs_2025","delta_revenue_comparison_basis":"2026_vs_2025"})
    assert r.roic==pytest.approx(.12)
    assert r.incremental_roic==pytest.approx(.15)
    assert r.iwcr==pytest.approx(.60)


def test_growth_with_large_nwc_and_debt_increase_is_debt_funded():
    r=CapitalEfficiencyEngine().funding_loop({"delta_revenue":100,"delta_nwc":60,"delta_debt":55,"delta_equity":0,
        "external_equity_financing":0,"operating_cash_flow":-20,
        "delta_revenue_comparison_basis":"2026_vs_2025","delta_nwc_comparison_basis":"2026_vs_2025",
        "delta_debt_comparison_basis":"2026_vs_2025","external_equity_financing_comparison_basis":"2026_vs_2025"})
    assert r.funding_state=="debt_funded"
    assert "DEBT_FUNDS_NWC" in r.reason_codes


def test_negative_ocf_without_funding_inputs_does_not_invent_funding_state():
    r=CapitalEfficiencyEngine().funding_loop({"operating_cash_flow":-10})
    assert r.funding_state=="unknown"
    assert "NEGATIVE_OCF" in r.reason_codes
    assert "DEBT_FUNDS_NWC" not in r.reason_codes


def test_known_zero_debt_is_not_treated_as_missing():
    r=CapitalEfficiencyEngine().funding_loop({
        "delta_revenue":100,"delta_nwc":10,"delta_debt":0,"delta_equity":0,
        "external_equity_financing":0,"operating_cash_flow":15,
        "delta_revenue_comparison_basis":"2026_vs_2025","delta_nwc_comparison_basis":"2026_vs_2025",
        "delta_debt_comparison_basis":"2026_vs_2025","external_equity_financing_comparison_basis":"2026_vs_2025"
    })
    assert r.funding_state=="self_funded"


def test_missing_debt_does_not_allow_debt_funded_classification():
    r=CapitalEfficiencyEngine().funding_loop({
        "delta_revenue":100,"delta_nwc":60,"delta_debt":None,"delta_equity":0,
        "external_equity_financing":0,"operating_cash_flow":-20,
        "delta_revenue_comparison_basis":"2026_vs_2025","delta_nwc_comparison_basis":"2026_vs_2025",
        "external_equity_financing_comparison_basis":"2026_vs_2025"
    })
    assert r.funding_state=="unknown"
    assert "NEGATIVE_OCF" in r.reason_codes


def test_explicit_external_equity_financing_and_dilution_drive_equity_funded_state():
    basis = "2026_vs_2025"
    r = CapitalEfficiencyEngine().funding_loop({
        "delta_revenue": 100,
        "delta_nwc": 60,
        "delta_debt": 5,
        "delta_equity": 25,
        "external_equity_financing": 55,
        "equity_dilution": True,
        "operating_cash_flow": -20,
        "delta_revenue_comparison_basis": basis,
        "delta_nwc_comparison_basis": basis,
        "delta_debt_comparison_basis": basis,
        "external_equity_financing_comparison_basis": basis,
    })
    assert r.funding_state == "equity_funded"
    assert r.incremental_equity == 55
    assert r.reported_equity_change == 25
    assert "EQUITY_DILUTION" in r.reason_codes


def test_missing_comparison_basis_preserves_missing_iwcr_with_reason():
    r = CapitalEfficiencyEngine().calculate({"delta_nwc": 60, "delta_revenue": 100})
    assert r.iwcr is None
    assert r.iwcr_reason_code == "COMPARISON_BASIS_REQUIRED"


def test_growth_quality_exposes_components_without_unversioned_composite_score():
    c=CapitalEfficiencyEngine().growth_quality_components({
        "revenue_growth":.30,"margin_change":.01,"roic":.10,"cash_conversion":.8,
        "incremental_nwc_efficiency":.7,"leverage_deterioration":.1,"dilution":0.0})
    assert set(c)=={"growth","margin","roic","cash_conversion","incremental_nwc_efficiency","leverage_deterioration","dilution"}
    assert "score" not in c
