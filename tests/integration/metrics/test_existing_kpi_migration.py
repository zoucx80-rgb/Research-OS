from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.policies import PolicySnapshot
from research_os.contracts.values import AccountingScope
from research_os.kpi.distributor import DistributorPack
from research_os.kpi.manufacturing import ManufacturingPack
from research_os.metrics import builtin_metric_registry
from research_os.period.models import ReportingPeriod
from research_os.plugins.builtins import (
    DistributorIndustryPlugin,
    ManufacturingIndustryPlugin,
)
from research_os.runtime.context import FactView


def _facts(values: dict[str, Decimal], period: ReportingPeriod) -> FactView:
    references = {
        fact_id: (
            EvidenceRef(
                evidence_id=f"ev:{fact_id}",
                revision=1,
                content_fingerprint=f"{index:064x}",
            ),
        )
        for index, fact_id in enumerate(sorted(values), start=1)
    }
    return FactView(
        company_id="synthetic:kpi-migration",
        decision_ts=datetime(2026, 8, 20, tzinfo=timezone.utc),
        values=values,
        evidence_refs_by_fact=references,
        reporting_period=period,
        accounting_scope=AccountingScope(consolidation="consolidated"),
    )


def _metrics(plugin: object, facts: FactView):
    provider = plugin.services().kpi_provider
    assert provider is not None
    return {
        item.metric_id: item
        for item in provider.calculate(facts, builtin_metric_registry(), PolicySnapshot())
    }


def test_manufacturing_provider_preserves_golden_values_through_registry() -> None:
    values = {
        "revenue": Decimal("1000"),
        "net_profit_parent": Decimal("50"),
        "assets_begin": Decimal("800"),
        "assets_end": Decimal("900"),
        "equity_begin": Decimal("400"),
        "equity_end": Decimal("450"),
        "ar_begin": Decimal("90"),
        "ar_end": Decimal("110"),
        "inventory_begin": Decimal("180"),
        "inventory_end": Decimal("220"),
        "cogs": Decimal("900"),
        "ocf": Decimal("80"),
        "capex_cash": Decimal("30"),
        "ppe_begin": Decimal("500"),
        "ppe_end": Decimal("600"),
    }
    metrics = _metrics(
        ManufacturingIndustryPlugin(),
        _facts(values, ReportingPeriod(period_type="H1", period_days=181)),
    )

    assert metrics["net_margin"].value == Decimal("0.05")
    assert metrics["asset_turnover"].value == Decimal("1000") / Decimal("850")
    assert metrics["roe"].value == Decimal("50") / Decimal("425")
    assert metrics["ar_days"].value == Decimal("18.1")
    assert metrics["inventory_days"].value == Decimal("36200") / Decimal("900")
    assert metrics["simple_fcf"].value == Decimal("50")
    assert all(item.evidence_refs for item in metrics.values() if item.status == "valid")


def test_distributor_provider_preserves_golden_values_through_registry() -> None:
    values = {
        "revenue": Decimal("1000"),
        "cogs": Decimal("900"),
        "avg_ar": Decimal("100"),
        "avg_inventory": Decimal("200"),
        "avg_ap": Decimal("150"),
        "ar": Decimal("110"),
        "inventory": Decimal("210"),
        "ap": Decimal("160"),
        "gross_profit": Decimal("100"),
        "nopat": Decimal("20"),
        "avg_invested_capital": Decimal("250"),
    }
    metrics = _metrics(
        DistributorIndustryPlugin(),
        _facts(values, ReportingPeriod(period_type="FY")),
    )

    assert metrics["dso_days"].value == Decimal("36.5")
    assert metrics["inventory_turns_period"].value == Decimal("4.5")
    assert metrics["nwc_intensity"].value == Decimal("0.16")
    assert metrics["gross_profit_to_working_capital"].value == Decimal("0.625")
    assert metrics["roic"].value == Decimal("0.08")


def test_industry_packs_select_definitions_without_executing_formulas() -> None:
    manufacturing = ManufacturingPack()
    distributor = DistributorPack()

    assert manufacturing.metric_ids
    assert distributor.metric_ids
    assert not hasattr(manufacturing, "calculate")
    assert not hasattr(distributor, "calculate")
