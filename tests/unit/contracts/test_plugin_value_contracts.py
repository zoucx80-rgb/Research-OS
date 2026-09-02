from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from research_os.contracts.metrics import MetricDefinition, MetricResult
from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.policies import PolicySelection, PolicySnapshot
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod


def test_reporting_period_and_accounting_scope_are_frozen_typed_values():
    period = ReportingPeriod(
        period_type="H1",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 6, 30),
        period_days=181,
    )
    scope = AccountingScope(
        accounting_standard="IFRS",
        consolidation="consolidated",
        segment="industrial",
        geography="global",
    )

    with pytest.raises(ValidationError):
        period.period_days = 365
    with pytest.raises(ValidationError):
        scope.segment = "changed"


def test_metric_result_carries_period_scope_and_revision_bound_lineage():
    reference = EvidenceRef(
        evidence_id="ev:revenue",
        revision=1,
        content_fingerprint="a" * 64,
    )
    result = MetricResult(
        metric_id="revenue",
        value=100,
        unit="CNY",
        status="valid",
        formula_version="reported@1",
        reporting_period=ReportingPeriod(period_type="H1", period_days=181),
        accounting_scope=AccountingScope(consolidation="consolidated"),
        evidence_refs=(reference,),
    )

    assert result.reporting_period.period_days == 181
    assert result.accounting_scope.consolidation == "consolidated"
    with pytest.raises(ValidationError):
        result.value = 999


def test_metric_result_rejects_inconsistent_missingness_and_untraceable_valid_values():
    common = {
        "metric_id": "revenue",
        "unit": "CNY",
        "formula_version": "reported@1",
        "reporting_period": ReportingPeriod(period_type="H1", period_days=181),
        "accounting_scope": AccountingScope(consolidation="consolidated"),
    }

    with pytest.raises(ValidationError, match="valid metric requires a value"):
        MetricResult(**common, value=None, status="valid")
    with pytest.raises(ValidationError, match="non-valid metric cannot carry a value"):
        MetricResult(**common, value=100, status="missing")
    with pytest.raises(ValidationError, match="valid metric requires EvidenceRef lineage"):
        MetricResult(**common, value=100, status="valid")


def test_policy_snapshot_is_order_independent_and_rejects_conflicting_ids():
    first = PolicySelection(
        policy_id="policy:a",
        policy_version="1.0.0",
        parameters_fingerprint="a" * 64,
    )
    second = PolicySelection(
        policy_id="policy:b",
        policy_version="2.0.0",
        parameters_fingerprint="b" * 64,
    )

    assert PolicySnapshot(policies=(second, first)).policies == (first, second)
    with pytest.raises(ValueError, match="duplicate policy_id"):
        PolicySnapshot(policies=(first, first))


def test_metric_definition_has_stable_semantic_identity():
    definition = MetricDefinition(
        metric_id="revenue",
        definition_version="1.0.0",
        output_kind="flow",
        output_unit="CNY",
    )

    assert definition.metric_id == "revenue"
    with pytest.raises(ValidationError):
        definition.output_unit = "USD"
