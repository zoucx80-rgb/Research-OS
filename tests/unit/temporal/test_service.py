from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.temporal.models import FinancialPeriodObservation
from research_os.temporal.service import ComparisonBasisValidator, TemporalAnalysisService


DECISION_TS = datetime(2026, 4, 1, tzinfo=timezone.utc)


def _observation(
    *,
    metric_id: str = "revenue",
    value: str,
    period_type: str = "FY",
    period_start: date,
    period_end: date,
    is_cumulative: bool = True,
    period_kind: str = "FLOW",
    comparison_basis: str | None = "YOY_PERIOD",
    scope: str = "consolidated",
    available_ts: datetime | None = None,
) -> FinancialPeriodObservation:
    return FinancialPeriodObservation(
        metric_id=metric_id,
        reporting_period=ReportingPeriod(
            period_type=period_type,
            period_start=period_start,
            period_end=period_end,
            period_days=(period_end - period_start).days + 1,
            is_cumulative=is_cumulative,
        ),
        period_kind=period_kind,
        value=Decimal(value),
        unit="CNY" if metric_id != "gross_margin" else "ratio",
        accounting_scope=AccountingScope(consolidation=scope),
        value_kind="reported",
        comparison_basis=comparison_basis,
        available_ts=available_ts
        or datetime(
            period_end.year + 1,
            3,
            31,
            tzinfo=timezone.utc,
        ),
        evidence_refs=(
            EvidenceRef(
                evidence_id=f"ev:{metric_id}:{period_end.isoformat()}:{scope}",
                revision=1,
                content_fingerprint="a" * 64,
            ),
        ),
    )


def _fy(year: int, value: str, **kwargs: object) -> FinancialPeriodObservation:
    return _observation(
        value=value,
        period_start=date(year, 1, 1),
        period_end=date(year, 12, 31),
        **kwargs,
    )


def _h1(year: int, value: str) -> FinancialPeriodObservation:
    return _observation(
        value=value,
        period_type="H1",
        period_start=date(year, 1, 1),
        period_end=date(year, 6, 30),
        is_cumulative=True,
    )


def _quarter(year: int, quarter: int, value: str, *, basis: str) -> FinancialPeriodObservation:
    starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
    ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    start_month, start_day = starts[quarter]
    end_month, end_day = ends[quarter]
    return _observation(
        value=value,
        period_type="CUSTOM",
        period_start=date(year, start_month, start_day),
        period_end=date(year, end_month, end_day),
        is_cumulative=False,
        comparison_basis=basis,
    )


def test_one_point_is_not_temporally_sufficient() -> None:
    result = TemporalAnalysisService().analyze((_fy(2024, "100"),), decision_ts=DECISION_TS)

    assert result.temporal_coverage == "INSUFFICIENT_EVIDENCE"
    assert result.assessments[0].comparison_status == "INSUFFICIENT_EVIDENCE"
    assert result.assessments[0].yoy_change is None
    assert result.unresolved_gaps == ("revenue:INSUFFICIENT_COMPARABLE_POINTS",)


def test_cumulative_h1_supports_yoy_but_is_not_converted_to_quarter() -> None:
    result = TemporalAnalysisService().analyze(
        (_h1(2024, "100"), _h1(2025, "110")),
        decision_ts=DECISION_TS,
    )

    assessment = result.assessments[0]
    assert assessment.yoy_change == Decimal("0.1")
    assert assessment.qoq_change is None
    assert assessment.comparison_basis == "YOY_PERIOD"


def test_contiguous_non_cumulative_quarters_support_qoq() -> None:
    result = TemporalAnalysisService().analyze(
        (
            _quarter(2025, 1, "100", basis="QOQ_PERIOD"),
            _quarter(2025, 2, "125", basis="QOQ_PERIOD"),
        ),
        decision_ts=DECISION_TS,
    )

    assert result.assessments[0].qoq_change == Decimal("0.25")
    assert result.assessments[0].yoy_change is None


def test_four_contiguous_flow_quarters_support_ttm() -> None:
    result = TemporalAnalysisService().analyze(
        tuple(
            _quarter(2025, quarter, value, basis="TTM")
            for quarter, value in enumerate(("10", "20", "30", "40"), start=1)
        ),
        decision_ts=DECISION_TS,
    )

    assessment = result.assessments[0]
    assert assessment.ttm_value == Decimal("100")
    assert assessment.comparison_status == "PASS"


def test_mismatched_declared_basis_is_not_compared() -> None:
    current = _fy(2025, "110")
    prior = _fy(2024, "100").model_copy(update={"comparison_basis": "SAME_PERIOD"})

    result = TemporalAnalysisService().analyze((prior, current), decision_ts=DECISION_TS)

    assessment = result.assessments[0]
    assert assessment.comparison_status == "NOT_COMPARABLE"
    assert assessment.yoy_change is None
    assert assessment.reason_codes == ("COMPARISON_BASIS_MISMATCH",)


def test_comparison_validator_rejects_accounting_scope_mismatch() -> None:
    reasons = ComparisonBasisValidator().validate(
        _fy(2024, "100", scope="standalone"),
        _fy(2025, "110", scope="consolidated"),
        expected_basis="YOY_PERIOD",
    )

    assert reasons == ("ACCOUNTING_SCOPE_MISMATCH",)


def test_same_metric_with_mixed_period_kinds_is_not_split_into_separate_series() -> None:
    result = TemporalAnalysisService().analyze(
        (
            _fy(2024, "100", period_kind="STOCK"),
            _fy(2025, "110", period_kind="FLOW"),
        ),
        decision_ts=DECISION_TS,
    )

    assert len(result.assessments) == 1
    assert result.assessments[0].comparison_status == "NOT_COMPARABLE"
    assert result.assessments[0].reason_codes == ("PERIOD_KIND_MISMATCH",)


def test_future_available_observation_is_rejected() -> None:
    future = _fy(
        2025,
        "110",
        available_ts=DECISION_TS + timedelta(seconds=1),
    )

    with pytest.raises(ValueError, match="available_ts exceeds decision_ts"):
        TemporalAnalysisService().analyze((future,), decision_ts=DECISION_TS)


def test_distinct_accounting_scopes_remain_distinct_assessments() -> None:
    result = TemporalAnalysisService().analyze(
        (
            _fy(2024, "100", scope="standalone"),
            _fy(2025, "110", scope="standalone"),
            _fy(2024, "200", scope="consolidated"),
            _fy(2025, "240", scope="consolidated"),
        ),
        decision_ts=DECISION_TS,
    )

    assert len(result.assessments) == 2
    assert {item.accounting_scope.consolidation for item in result.assessments} == {
        "consolidated",
        "standalone",
    }


def test_trend_and_anomaly_are_policy_derived() -> None:
    result = TemporalAnalysisService().analyze(
        (_fy(2023, "100"), _fy(2024, "110"), _fy(2025, "150")),
        decision_ts=DECISION_TS,
    )

    assessment = result.assessments[0]
    assert assessment.trend_state == "RISING"
    assert assessment.anomaly_flags == ("RELATIVE_CHANGE_EXCEEDS_THRESHOLD",)
    assert assessment.turning_point_state == "NOT_OBSERVED"
