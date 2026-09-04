from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from research_os.contracts.artifact_values import AssumptionRef
from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.temporal.models import (
    FinancialPeriodObservation,
    FinancialTemporalAnalysis,
    MetricTemporalAssessment,
)


def _evidence_ref(key: str = "revenue") -> EvidenceRef:
    return EvidenceRef(
        evidence_id=f"ev:{key}",
        revision=1,
        content_fingerprint="a" * 64,
    )


def _assumption_ref(key: str = "revenue-normalization") -> AssumptionRef:
    return AssumptionRef(
        assumption_key=key,
        assumption_version="1.0.0",
        content_fingerprint="b" * 64,
    )


def _period() -> ReportingPeriod:
    return ReportingPeriod(
        period_type="FY",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        period_days=366,
        is_cumulative=True,
    )


def test_period_observation_requires_timezone_aware_availability() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        FinancialPeriodObservation(
            metric_id="revenue",
            reporting_period=_period(),
            period_kind="FLOW",
            value=Decimal("100"),
            unit="CNY",
            accounting_scope=AccountingScope(consolidation="consolidated"),
            value_kind="reported",
            comparison_basis="YOY_PERIOD",
            available_ts=datetime(2025, 3, 31),
            evidence_refs=(_evidence_ref(),),
        )


def test_period_observation_normalizes_availability_to_utc() -> None:
    observation = FinancialPeriodObservation(
        metric_id="revenue",
        reporting_period=_period(),
        period_kind="FLOW",
        value=Decimal("100"),
        unit="cny",
        accounting_scope=AccountingScope(consolidation="consolidated"),
        value_kind="reported",
        comparison_basis="YOY_PERIOD",
        available_ts=datetime(2025, 3, 31, tzinfo=timezone(timedelta(hours=8))),
        evidence_refs=(_evidence_ref(),),
    )

    assert observation.available_ts == datetime(2025, 3, 30, 16, tzinfo=timezone.utc)
    assert observation.unit == "CNY"


def test_reported_period_observation_requires_evidence_lineage() -> None:
    with pytest.raises(ValidationError, match="reported observation requires evidence"):
        FinancialPeriodObservation(
            metric_id="revenue",
            reporting_period=_period(),
            period_kind="FLOW",
            value=Decimal("100"),
            unit="CNY",
            accounting_scope=AccountingScope(consolidation="consolidated"),
            value_kind="reported",
            comparison_basis="YOY_PERIOD",
            available_ts=datetime(2025, 3, 31, tzinfo=timezone.utc),
        )


def test_derived_period_observation_requires_evidence_or_assumption_lineage() -> None:
    with pytest.raises(ValidationError, match="derived observation requires lineage"):
        FinancialPeriodObservation(
            metric_id="revenue",
            reporting_period=_period(),
            period_kind="FLOW",
            value=Decimal("100"),
            unit="CNY",
            accounting_scope=AccountingScope(consolidation="consolidated"),
            value_kind="derived",
            comparison_basis="YOY_PERIOD",
            available_ts=datetime(2025, 3, 31, tzinfo=timezone.utc),
        )

    supported = FinancialPeriodObservation(
        metric_id="revenue",
        reporting_period=_period(),
        period_kind="FLOW",
        value=Decimal("100"),
        unit="CNY",
        accounting_scope=AccountingScope(consolidation="consolidated"),
        value_kind="derived",
        comparison_basis="YOY_PERIOD",
        available_ts=datetime(2025, 3, 31, tzinfo=timezone.utc),
        assumption_refs=(_assumption_ref(),),
    )
    assert supported.assumption_refs == (_assumption_ref(),)


def test_temporal_analysis_has_deterministic_assessment_order() -> None:
    revenue = MetricTemporalAssessment(
        metric_id="revenue",
        unit="CNY",
        point_count=2,
        comparable_point_count=2,
        comparison_status="PASS",
    )
    margin = MetricTemporalAssessment(
        metric_id="gross_margin",
        unit="ratio",
        point_count=2,
        comparable_point_count=2,
        comparison_status="PASS",
    )

    analysis = FinancialTemporalAnalysis(assessments=(revenue, margin))

    assert tuple(item.metric_id for item in analysis.assessments) == (
        "gross_margin",
        "revenue",
    )


def test_temporal_analysis_rejects_duplicate_assessment_identity() -> None:
    assessment = MetricTemporalAssessment(
        metric_id="revenue",
        unit="CNY",
        point_count=2,
        comparable_point_count=2,
        comparison_status="PASS",
    )

    with pytest.raises(ValidationError, match="assessment identities must be unique"):
        FinancialTemporalAnalysis(assessments=(assessment, assessment))
