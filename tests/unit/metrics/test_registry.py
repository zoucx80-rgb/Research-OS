from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.policies import PolicySnapshot
from research_os.contracts.values import AccountingScope
from research_os.metrics import (
    MetricCalculationEngine,
    MetricDefinition,
    MetricDefinitionConflictError,
    MetricDefinitionRegistry,
    MetricInputDefinition,
    builtin_metric_definitions,
)
from research_os.period.models import ReportingPeriod
from research_os.runtime.context import FactView


def _definition(**updates: object) -> MetricDefinition:
    values = {
        "metric_id": "net_margin",
        "definition_version": "2.0.0",
        "economic_meaning": "Profit attributable to revenue",
        "formula_id": "safe_ratio",
        "output_kind": "ratio",
        "output_unit": "percent",
        "required_inputs": (
            MetricInputDefinition(fact_id="net_profit_parent", role="numerator"),
            MetricInputDefinition(fact_id="revenue", role="denominator"),
        ),
        "valid_comparison_bases": frozenset({"YOY_PERIOD"}),
        "accounting_scope_policy": "exact",
    }
    values.update(updates)
    return MetricDefinition(**values)


@pytest.mark.parametrize(
    "updates",
    (
        {"formula_id": "average_ratio"},
        {"output_unit": "x"},
        {"output_kind": "flow"},
        {"accounting_scope_policy": "consolidated_only"},
    ),
)
def test_registry_rejects_same_id_with_conflicting_semantics(
    updates: dict[str, object],
) -> None:
    with pytest.raises(MetricDefinitionConflictError, match="net_margin"):
        MetricDefinitionRegistry((_definition(), _definition(**updates)))


def test_registry_is_order_independent_and_read_only() -> None:
    first = _definition()
    second = _definition(
        metric_id="roic",
        economic_meaning="Return on invested capital",
        required_inputs=(
            MetricInputDefinition(fact_id="nopat", role="numerator"),
            MetricInputDefinition(fact_id="avg_invested_capital", role="denominator"),
        ),
    )

    forward = MetricDefinitionRegistry((first, second))
    reverse = MetricDefinitionRegistry((second, first))

    assert forward.definitions == reverse.definitions == (first, second)
    assert forward.get("net_margin") == first
    assert not hasattr(forward, "register")


def test_period_sensitive_metric_fails_closed_without_period_length() -> None:
    definition = next(item for item in builtin_metric_definitions() if item.metric_id == "dso_days")
    reference = EvidenceRef(
        evidence_id="ev:inputs",
        revision=1,
        content_fingerprint="a" * 64,
    )
    facts = FactView(
        company_id="synthetic:metrics",
        decision_ts=datetime(2026, 8, 20, tzinfo=timezone.utc),
        values={"avg_ar": Decimal("100"), "revenue": Decimal("1000")},
        evidence_refs_by_fact={"avg_ar": (reference,), "revenue": (reference,)},
        reporting_period=ReportingPeriod(period_type="H1"),
        accounting_scope=AccountingScope(consolidation="consolidated"),
    )

    result = MetricCalculationEngine().calculate(facts, definition, PolicySnapshot())

    assert result.status == "missing"
    assert result.value is None
    assert result.reason_code == "PERIOD_LENGTH_REQUIRED"
    assert result.reporting_period.period_type == "H1"
    assert result.accounting_scope.consolidation == "consolidated"


def test_builtin_registry_owns_common_financial_formulas() -> None:
    definitions = {item.metric_id: item for item in builtin_metric_definitions()}

    assert definitions["net_margin"].formula_id == "safe_ratio"
    assert definitions["roic"].formula_id == "safe_ratio"
    assert definitions["asset_turnover"].formula_id == "average_ratio"
    assert definitions["dso_days"].formula_id == "turnover_days"
    assert definitions["gross_profit_to_working_capital"].formula_id == ("ratio_to_working_capital")
