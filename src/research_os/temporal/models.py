from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from research_os.contracts.artifact_values import DomainArtifact, LineageValue
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod


TemporalComparisonBasis = Literal["YOY_PERIOD", "QOQ_PERIOD", "TTM", "SAME_PERIOD"]
PeriodKind = Literal["FLOW", "STOCK", "FLOW_RATIO", "STOCK_RATIO"]
TrendState = Literal["RISING", "FALLING", "STABLE", "MIXED", "UNKNOWN"]
TurningPointState = Literal["CONFIRMED", "POSSIBLE", "NOT_OBSERVED", "UNKNOWN"]


class FinancialPeriodObservation(LineageValue):
    metric_id: str
    reporting_period: ReportingPeriod
    period_kind: PeriodKind
    value: Decimal
    unit: str
    accounting_scope: AccountingScope
    value_kind: Literal["reported", "derived"]
    annualized: bool = False
    comparison_basis: TemporalComparisonBasis | None = None
    available_ts: datetime

    @field_validator("metric_id", "unit")
    @classmethod
    def _normalize_identity(cls, value: str, info: object) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError(f"{getattr(info, 'field_name', 'identity')} must be non-empty")
        if getattr(info, "field_name", None) == "unit" and len(normalized) == 3:
            return normalized.upper()
        return normalized

    @field_validator("available_ts")
    @classmethod
    def _normalize_availability(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("available_ts must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("value")
    @classmethod
    def _finite_value(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("period observation value must be finite")
        return value

    @model_validator(mode="after")
    def _validate_lineage_and_period(self) -> FinancialPeriodObservation:
        if self.reporting_period.period_end is None:
            raise ValueError("period observation requires period_end")
        if self.value_kind == "reported" and not self.evidence_refs:
            raise ValueError("reported observation requires evidence lineage")
        if self.value_kind == "derived" and not (self.evidence_refs or self.assumption_refs):
            raise ValueError("derived observation requires lineage")
        if self.value_kind == "reported" and self.annualized:
            raise ValueError("annualized observation must be derived")
        return self


class MetricTemporalAssessment(LineageValue):
    metric_id: str
    unit: str
    period_kind: PeriodKind = "FLOW"
    accounting_scope: AccountingScope = Field(default_factory=AccountingScope)
    comparison_basis: TemporalComparisonBasis | None = None
    latest_period: ReportingPeriod | None = None
    point_count: int = Field(ge=0)
    comparable_point_count: int = Field(ge=0)
    temporal_span_days: int | None = Field(default=None, ge=0)
    yoy_change: Decimal | None = None
    qoq_change: Decimal | None = None
    ttm_value: Decimal | None = None
    trend_state: TrendState = "UNKNOWN"
    turning_point_state: TurningPointState = "UNKNOWN"
    anomaly_flags: tuple[str, ...] = ()
    comparison_status: Literal["PASS", "NOT_COMPARABLE", "INSUFFICIENT_EVIDENCE"]
    reason_codes: tuple[str, ...] = ()

    @field_validator("metric_id", "unit")
    @classmethod
    def _non_empty_identity(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("temporal assessment identity must be non-empty")
        return normalized

    @field_validator("anomaly_flags", "reason_codes")
    @classmethod
    def _canonical_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("temporal codes must be non-empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("temporal codes must be unique")
        return tuple(sorted(normalized))

    @model_validator(mode="after")
    def _counts_are_consistent(self) -> MetricTemporalAssessment:
        if self.comparable_point_count > self.point_count:
            raise ValueError("comparable point count cannot exceed point count")
        return self


class FinancialTemporalAnalysis(DomainArtifact):
    observations: tuple[FinancialPeriodObservation, ...] = ()
    assessments: tuple[MetricTemporalAssessment, ...] = ()
    temporal_coverage: Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT_EVIDENCE"] = (
        "INSUFFICIENT_EVIDENCE"
    )
    unresolved_gaps: tuple[str, ...] = ()

    @field_validator("observations")
    @classmethod
    def _canonical_observations(
        cls,
        value: tuple[FinancialPeriodObservation, ...],
    ) -> tuple[FinancialPeriodObservation, ...]:
        def identity(item: FinancialPeriodObservation) -> tuple[object, ...]:
            period = item.reporting_period
            return (
                item.metric_id,
                item.unit,
                item.accounting_scope.model_dump_json(),
                item.period_kind,
                period.period_type,
                period.period_start,
                period.period_end,
                period.period_days,
                period.is_cumulative,
            )

        identities = tuple(identity(item) for item in value)
        if len(identities) != len(set(identities)):
            raise ValueError("period observation identities must be unique")

        def sort_key(item: FinancialPeriodObservation) -> tuple[object, ...]:
            period = item.reporting_period
            return (
                item.metric_id,
                item.unit,
                item.accounting_scope.model_dump_json(),
                item.period_kind,
                period.period_type,
                period.period_end.isoformat() if period.period_end is not None else "",
                period.period_start.isoformat() if period.period_start is not None else "",
                period.period_days if period.period_days is not None else 0,
                period.is_cumulative,
                item.available_ts,
            )

        return tuple(sorted(value, key=sort_key))

    @field_validator("assessments")
    @classmethod
    def _canonical_assessments(
        cls,
        value: tuple[MetricTemporalAssessment, ...],
    ) -> tuple[MetricTemporalAssessment, ...]:
        identities = tuple(
            (
                item.metric_id,
                item.unit,
                item.period_kind,
                item.accounting_scope.model_dump_json(),
            )
            for item in value
        )
        if len(identities) != len(set(identities)):
            raise ValueError("assessment identities must be unique")
        return tuple(
            sorted(
                value,
                key=lambda item: (
                    item.metric_id,
                    item.unit,
                    item.period_kind,
                    item.accounting_scope.model_dump_json(),
                ),
            )
        )

    @field_validator("unresolved_gaps")
    @classmethod
    def _canonical_gaps(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("unresolved gaps must be non-empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("unresolved gaps must be unique")
        return tuple(sorted(normalized))
