from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.metrics import builtin_metric_registry
from research_os.period.models import ReportingPeriod
from research_os.plugins.builtins import (
    DistributorIndustryPlugin,
    ManufacturingIndustryPlugin,
)
from research_os.policies import builtin_policy_registry
from research_os.runtime.context import FactView


_DECISION_TS = datetime(2026, 8, 29, tzinfo=timezone.utc)
_COMPANY_ID = "synthetic:kpi-v2"
_DECIMAL_IDENTITY_TOLERANCE = Decimal("1e-24")


def _fact_view(
    values: dict[str, object],
    *,
    period_type: str = "FY",
    period_days: int | None = None,
) -> FactView:
    references = {
        fact_id: (
            EvidenceRef(
                evidence_id=f"ev:{fact_id}",
                revision=1,
                content_fingerprint="a" * 64,
            ),
        )
        for fact_id, value in values.items()
        if value is not None
    }
    return FactView(
        company_id=_COMPANY_ID,
        decision_ts=_DECISION_TS,
        values=values,
        evidence_refs_by_fact=references,
        reporting_period=ReportingPeriod(
            period_type=period_type,
            period_days=period_days,
        ),
        accounting_scope=AccountingScope(),
    )


def _metrics(
    plugin: DistributorIndustryPlugin | ManufacturingIndustryPlugin,
    values: dict[str, object],
    *,
    period_type: str = "FY",
    period_days: int | None = None,
):
    provider = plugin.services().kpi_provider
    assert provider is not None
    result = provider.calculate(
        _fact_view(values, period_type=period_type, period_days=period_days),
        builtin_metric_registry(),
        builtin_policy_registry().snapshot(),
    )
    return {item.metric_id: item for item in result}


def _assert_ccc_identity(result: dict[str, object]) -> None:
    ccc = result["ccc_days"].value  # type: ignore[attr-defined]
    dso = result["dso_days"].value  # type: ignore[attr-defined]
    dio = result["dio_days"].value  # type: ignore[attr-defined]
    dpo = result["dpo_days"].value  # type: ignore[attr-defined]
    assert ccc is not None and dso is not None and dio is not None and dpo is not None
    assert abs(ccc - (dso + dio - dpo)) <= _DECIMAL_IDENTITY_TOLERANCE


def test_manufacturing_provider_preserves_core_formula_semantics() -> None:
    result = _metrics(
        ManufacturingIndustryPlugin(),
        {
            "revenue": 100.0,
            "net_profit_parent": 10.0,
            "assets_begin": 80.0,
            "assets_end": 120.0,
            "equity_begin": 40.0,
            "equity_end": 60.0,
            "ocf": 9.0,
            "ar_begin": 15.0,
            "ar_end": 25.0,
            "inventory_begin": 20.0,
            "inventory_end": 30.0,
            "cogs": 75.0,
            "capex_cash": 5.0,
            "ppe_begin": 20.0,
            "ppe_end": 30.0,
        },
    )
    assert result["roe"].value == Decimal("0.2")
    assert result["cash_conversion_parent"].value == Decimal("0.9")
    assert result["ar_days"].value == Decimal("73")
    assert result["inventory_days"].value == (
        Decimal("25") / Decimal("75") * Decimal("365")
    )
    assert result["simple_fcf"].value == Decimal("4")
    assert result["fixed_asset_turnover"].value == Decimal("4")


def test_distributor_provider_preserves_ccc_and_missingness() -> None:
    base = {
        "avg_ar": 100.0,
        "revenue": 1000.0,
        "avg_inventory": 200.0,
        "cogs": 900.0,
        "avg_ap": 150.0,
    }
    result = _metrics(DistributorIndustryPlugin(), base)
    _assert_ccc_identity(result)

    missing = _metrics(DistributorIndustryPlugin(), {**base, "avg_ap": None})
    assert missing["dpo_days"].value is None
    assert missing["ccc_days"].value is None


def test_distributor_provider_preserves_funding_metrics_and_comparison_basis() -> None:
    result = _metrics(
        DistributorIndustryPlugin(),
        {
            "revenue": 1000.0,
            "cogs": 900.0,
            "avg_ar": 100.0,
            "avg_inventory": 200.0,
            "avg_ap": 150.0,
            "ar": 110.0,
            "inventory": 210.0,
            "ap": 160.0,
            "delta_nwc": 30.0,
            "delta_revenue": 100.0,
            "delta_nwc_comparison_basis": "2026_vs_2025",
            "delta_revenue_comparison_basis": "2026_vs_2025",
            "short_debt": 120.0,
            "equity": 200.0,
            "gross_profit": 100.0,
            "interest_expense": 10.0,
            "ocf": 20.0,
            "net_profit": 25.0,
            "nopat": 20.0,
            "avg_invested_capital": 250.0,
        },
    )
    assert result["nwc_intensity"].value == Decimal("0.16")
    assert result["incremental_nwc_intensity"].value == Decimal("0.3")
    assert result["interest_to_gross_profit"].value == Decimal("0.1")
    assert result["roic"].value == Decimal("0.08")


def test_distributor_provider_preserves_growth_quality_metrics() -> None:
    result = _metrics(
        DistributorIndustryPlugin(),
        {
            "revenue": 100.0,
            "cogs": 95.0,
            "avg_ar": 20.0,
            "avg_inventory": 10.0,
            "avg_ap": 8.0,
            "ar": 21.0,
            "inventory": 11.0,
            "ap": 9.0,
            "gross_profit": 5.0,
            "interest_expense": 1.0,
            "credit_impairment": 0.2,
            "inventory_impairment": 0.1,
            "revenue_growth": 0.20,
            "working_capital_growth": 0.35,
            "nopat": 3.0,
            "avg_invested_capital": 30.0,
            "delta_nopat": 0.6,
            "delta_invested_capital": 10.0,
        },
    )
    required = {
        "inventory_turns",
        "gross_profit_to_working_capital",
        "credit_impairment_to_gross_profit",
        "inventory_impairment_to_gross_profit",
        "revenue_growth_vs_working_capital_growth",
        "incremental_roic",
    }
    assert required.issubset(result)
    assert result["inventory_turns"].value == Decimal("9.5")
    assert result["incremental_roic"].value == Decimal("0.06")


def test_distributor_h1_days_use_explicit_period_length() -> None:
    result = _metrics(
        DistributorIndustryPlugin(),
        {
            "avg_ar": 100.0,
            "revenue": 1000.0,
            "avg_inventory": 200.0,
            "cogs": 900.0,
            "avg_ap": 150.0,
        },
        period_type="H1",
        period_days=181,
    )
    assert result["dso_days"].value == Decimal("100") / Decimal("1000") * Decimal("181")
    assert result["dio_days"].value == Decimal("200") / Decimal("900") * Decimal("181")
    assert result["dpo_days"].value == Decimal("150") / Decimal("900") * Decimal("181")
    _assert_ccc_identity(result)


def test_distributor_interim_without_period_length_stays_missing() -> None:
    result = _metrics(
        DistributorIndustryPlugin(),
        {
            "avg_ar": 100.0,
            "revenue": 1000.0,
            "avg_inventory": 200.0,
            "cogs": 900.0,
            "avg_ap": 150.0,
        },
        period_type="H1",
    )
    assert result["dso_days"].value is None
    assert result["dso_days"].status == "missing"
    assert result["dso_days"].reason_code == "PERIOD_LENGTH_REQUIRED"


def test_distributor_exposes_period_and_annualized_inventory_turns() -> None:
    result = _metrics(
        DistributorIndustryPlugin(),
        {
            "avg_ar": 100.0,
            "revenue": 1000.0,
            "avg_inventory": 200.0,
            "cogs": 900.0,
            "avg_ap": 150.0,
        },
        period_type="H1",
        period_days=181,
    )
    assert result["inventory_turns_period"].value == Decimal("4.5")
    assert result["inventory_turns_annualized"].value == (
        Decimal("4.5") * Decimal("365") / Decimal("181")
    )


def test_distributor_fy_without_period_days_uses_annual_contract() -> None:
    result = _metrics(
        DistributorIndustryPlugin(),
        {
            "avg_ar": 100.0,
            "revenue": 1000.0,
            "avg_inventory": 200.0,
            "cogs": 900.0,
            "avg_ap": 150.0,
        },
    )
    assert result["dso_days"].value == Decimal("36.5")


def test_manufacturing_h1_turnover_days_use_same_period_contract() -> None:
    result = _metrics(
        ManufacturingIndustryPlugin(),
        {
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
        },
        period_type="H1",
        period_days=181,
    )
    assert result["ar_days"].value == Decimal("100") / Decimal("1000") * Decimal("181")
    assert result["inventory_days"].value == Decimal("200") / Decimal("900") * Decimal("181")
