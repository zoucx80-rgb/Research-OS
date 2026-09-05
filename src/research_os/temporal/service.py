from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from research_os.contracts.artifact_values import AssumptionRef, DomainStatus
from research_os.contracts.evidence import EvidenceRef
from research_os.policies import PolicyRegistry, builtin_policy_registry
from research_os.temporal.models import (
    FinancialPeriodObservation,
    FinancialTemporalAnalysis,
    MetricTemporalAssessment,
    TemporalComparisonBasis,
    TrendState,
    TurningPointState,
)


class ComparisonBasisValidator:
    """Validate whether two observations support one declared comparison."""

    def validate(
        self,
        prior: FinancialPeriodObservation,
        current: FinancialPeriodObservation,
        *,
        expected_basis: TemporalComparisonBasis,
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        if prior.metric_id != current.metric_id:
            reasons.append("METRIC_ID_MISMATCH")
        if prior.unit != current.unit:
            reasons.append("UNIT_MISMATCH")
        if prior.accounting_scope != current.accounting_scope:
            reasons.append("ACCOUNTING_SCOPE_MISMATCH")
        if prior.period_kind != current.period_kind:
            reasons.append("PERIOD_KIND_MISMATCH")
        if prior.annualized != current.annualized:
            reasons.append("ANNUALIZATION_MISMATCH")
        if prior.comparison_basis is None or current.comparison_basis is None:
            reasons.append("COMPARISON_BASIS_REQUIRED")
        elif (
            prior.comparison_basis != current.comparison_basis
            or current.comparison_basis != expected_basis
        ):
            reasons.append("COMPARISON_BASIS_MISMATCH")

        prior_period = prior.reporting_period
        current_period = current.reporting_period
        if prior_period.period_end is None or current_period.period_end is None:
            reasons.append("PERIOD_END_REQUIRED")
            return tuple(reasons)
        if current_period.period_end <= prior_period.period_end:
            reasons.append("PERIOD_ORDER_INVALID")

        if expected_basis == "YOY_PERIOD":
            if (
                prior_period.period_type != current_period.period_type
                or prior_period.is_cumulative != current_period.is_cumulative
            ):
                reasons.append("REPORTING_PERIOD_MISMATCH")
            if current_period.period_end.year != prior_period.period_end.year + 1:
                reasons.append("YOY_PERIOD_NOT_CONTIGUOUS")
            if (
                current_period.period_end.month,
                current_period.period_end.day,
            ) != (prior_period.period_end.month, prior_period.period_end.day):
                reasons.append("YOY_PERIOD_NOT_ALIGNED")
        elif expected_basis == "QOQ_PERIOD":
            if (
                prior_period.period_type != "CUSTOM"
                or current_period.period_type != "CUSTOM"
                or prior_period.is_cumulative
                or current_period.is_cumulative
            ):
                reasons.append("QOQ_REQUIRES_NON_CUMULATIVE_QUARTERS")
            if (
                current_period.period_start is None
                or current_period.period_start != prior_period.period_end + timedelta(days=1)
            ):
                reasons.append("QOQ_PERIOD_NOT_CONTIGUOUS")
        else:
            reasons.append("UNSUPPORTED_PAIR_COMPARISON_BASIS")
        return tuple(dict.fromkeys(reasons))


class TemporalAnalysisService:
    def __init__(self, policy_registry: PolicyRegistry | None = None) -> None:
        self._policies = policy_registry or builtin_policy_registry()
        self._basis_validator = ComparisonBasisValidator()

    def analyze(
        self,
        observations: tuple[FinancialPeriodObservation, ...],
        *,
        decision_ts: datetime,
    ) -> FinancialTemporalAnalysis:
        decision_ts = self._utc(decision_ts, field="decision_ts")
        ordered = FinancialTemporalAnalysis(observations=observations).observations
        for item in ordered:
            if item.available_ts > decision_ts:
                raise ValueError(
                    f"available_ts exceeds decision_ts: {item.metric_id} "
                    f"{item.available_ts.isoformat()} > {decision_ts.isoformat()}"
                )

        groups: dict[tuple[str, str, str], list[FinancialPeriodObservation]] = {}
        for item in ordered:
            key = (
                item.metric_id,
                item.unit,
                item.accounting_scope.model_dump_json(),
            )
            groups.setdefault(key, []).append(item)

        assessments = tuple(
            self._assess(
                tuple(
                    sorted(
                        items,
                        key=lambda item: (
                            item.reporting_period.period_end.isoformat()
                            if item.reporting_period.period_end is not None
                            else "",
                            item.reporting_period.period_start.isoformat()
                            if item.reporting_period.period_start is not None
                            else "",
                            item.reporting_period.period_type,
                            item.period_kind,
                            item.available_ts,
                        ),
                    )
                )
            )
            for _, items in sorted(groups.items(), key=lambda pair: pair[0])
        )
        passing = sum(item.comparison_status == "PASS" for item in assessments)
        if assessments and passing == len(assessments):
            temporal_coverage: Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT_EVIDENCE"] = (
                "SUFFICIENT"
            )
            domain_status: DomainStatus = "SUPPORTED"
        elif passing:
            temporal_coverage = "LIMITED"
            domain_status = "SUPPORTED"
        else:
            temporal_coverage = "INSUFFICIENT_EVIDENCE"
            domain_status = "INSUFFICIENT_EVIDENCE"

        gaps = tuple(
            sorted(
                {
                    f"{item.metric_id}:{reason}"
                    for item in assessments
                    if item.comparison_status != "PASS"
                    for reason in item.reason_codes
                }
            )
        )
        evidence_refs = self._evidence_refs(ordered)
        assumption_refs = self._assumption_refs(ordered)
        return FinancialTemporalAnalysis(
            domain_status=domain_status,
            observations=ordered,
            assessments=assessments,
            temporal_coverage=temporal_coverage,
            unresolved_gaps=gaps,
            evidence_refs=evidence_refs,
            assumption_refs=assumption_refs,
        )

    def _assess(
        self,
        observations: tuple[FinancialPeriodObservation, ...],
    ) -> MetricTemporalAssessment:
        first = observations[0]
        period_ends = tuple(
            item.reporting_period.period_end
            for item in observations
            if item.reporting_period.period_end is not None
        )
        span = (max(period_ends) - min(period_ends)).days if len(period_ends) >= 2 else None
        bases = {
            item.comparison_basis for item in observations if item.comparison_basis is not None
        }
        evidence_refs = self._evidence_refs(observations)
        assumption_refs = self._assumption_refs(observations)

        if len(observations) < self._minimum_points:
            return self._assessment(
                first,
                observations,
                temporal_span_days=span,
                comparison_status="INSUFFICIENT_EVIDENCE",
                reason_codes=("INSUFFICIENT_COMPARABLE_POINTS",),
                evidence_refs=evidence_refs,
                assumption_refs=assumption_refs,
            )
        if not bases:
            return self._assessment(
                first,
                observations,
                temporal_span_days=span,
                comparison_status="INSUFFICIENT_EVIDENCE",
                reason_codes=("COMPARISON_BASIS_REQUIRED",),
                evidence_refs=evidence_refs,
                assumption_refs=assumption_refs,
            )
        if len(bases) != 1:
            return self._assessment(
                first,
                observations,
                temporal_span_days=span,
                comparison_status="NOT_COMPARABLE",
                reason_codes=("COMPARISON_BASIS_MISMATCH",),
                evidence_refs=evidence_refs,
                assumption_refs=assumption_refs,
            )

        basis = next(iter(bases))
        if basis == "TTM":
            return self._assess_ttm(
                observations,
                temporal_span_days=span,
                evidence_refs=evidence_refs,
                assumption_refs=assumption_refs,
            )
        if basis not in {"YOY_PERIOD", "QOQ_PERIOD"}:
            return self._assessment(
                first,
                observations,
                temporal_span_days=span,
                comparison_status="NOT_COMPARABLE",
                reason_codes=("UNSUPPORTED_PAIR_COMPARISON_BASIS",),
                evidence_refs=evidence_refs,
                assumption_refs=assumption_refs,
            )

        changes: list[Decimal] = []
        compared_ids: set[int] = set()
        reasons: list[str] = []
        for index, (prior, current) in enumerate(zip(observations, observations[1:])):
            pair_reasons = self._basis_validator.validate(
                prior,
                current,
                expected_basis=basis,
            )
            if pair_reasons:
                reasons.extend(pair_reasons)
                continue
            if prior.value == 0:
                reasons.append("ZERO_COMPARISON_DENOMINATOR")
                continue
            changes.append((current.value / prior.value) - Decimal(1))
            compared_ids.update((index, index + 1))

        if not changes:
            return self._assessment(
                first,
                observations,
                temporal_span_days=span,
                comparison_status="NOT_COMPARABLE",
                reason_codes=tuple(sorted(set(reasons))) or ("NO_COMPARABLE_PERIODS",),
                evidence_refs=evidence_refs,
                assumption_refs=assumption_refs,
            )

        anomaly_flags = (
            ("RELATIVE_CHANGE_EXCEEDS_THRESHOLD",)
            if any(abs(change) >= self._anomaly_threshold for change in changes)
            else ()
        )
        return self._assessment(
            first,
            observations,
            comparable_point_count=len(compared_ids),
            temporal_span_days=span,
            yoy_change=changes[-1] if basis == "YOY_PERIOD" else None,
            qoq_change=changes[-1] if basis == "QOQ_PERIOD" else None,
            trend_state=self._trend(changes),
            turning_point_state=self._turning_point(changes),
            anomaly_flags=anomaly_flags,
            comparison_status="PASS",
            evidence_refs=evidence_refs,
            assumption_refs=assumption_refs,
        )

    def _assess_ttm(
        self,
        observations: tuple[FinancialPeriodObservation, ...],
        *,
        temporal_span_days: int | None,
        evidence_refs: tuple[EvidenceRef, ...],
        assumption_refs: tuple[AssumptionRef, ...],
    ) -> MetricTemporalAssessment:
        first = observations[0]
        latest = observations[-4:]
        valid = len(latest) == 4 and all(
            item.period_kind == "FLOW"
            and item.reporting_period.period_type == "CUSTOM"
            and not item.reporting_period.is_cumulative
            for item in latest
        )
        if valid:
            valid = all(
                current.reporting_period.period_start
                == prior.reporting_period.period_end + timedelta(days=1)
                for prior, current in zip(latest, latest[1:])
                if prior.reporting_period.period_end is not None
            )
        if not valid:
            return self._assessment(
                first,
                observations,
                temporal_span_days=temporal_span_days,
                comparison_status="NOT_COMPARABLE",
                reason_codes=("TTM_REQUIRES_FOUR_CONTIGUOUS_FLOW_QUARTERS",),
                evidence_refs=evidence_refs,
                assumption_refs=assumption_refs,
            )
        return self._assessment(
            first,
            observations,
            comparable_point_count=4,
            temporal_span_days=temporal_span_days,
            ttm_value=sum((item.value for item in latest), Decimal(0)),
            comparison_status="PASS",
            turning_point_state="UNKNOWN",
            evidence_refs=evidence_refs,
            assumption_refs=assumption_refs,
        )

    @staticmethod
    def _assessment(
        first: FinancialPeriodObservation,
        observations: tuple[FinancialPeriodObservation, ...],
        *,
        comparison_status: Literal["PASS", "NOT_COMPARABLE", "INSUFFICIENT_EVIDENCE"],
        evidence_refs: tuple[EvidenceRef, ...],
        assumption_refs: tuple[AssumptionRef, ...],
        comparable_point_count: int = 0,
        temporal_span_days: int | None = None,
        yoy_change: Decimal | None = None,
        qoq_change: Decimal | None = None,
        ttm_value: Decimal | None = None,
        trend_state: TrendState = "UNKNOWN",
        turning_point_state: TurningPointState = "UNKNOWN",
        anomaly_flags: tuple[str, ...] = (),
        reason_codes: tuple[str, ...] = (),
    ) -> MetricTemporalAssessment:
        return MetricTemporalAssessment(
            evidence_refs=evidence_refs,
            assumption_refs=assumption_refs,
            metric_id=first.metric_id,
            unit=first.unit,
            period_kind=first.period_kind,
            accounting_scope=first.accounting_scope,
            comparison_basis=first.comparison_basis,
            latest_period=observations[-1].reporting_period,
            point_count=len(observations),
            comparable_point_count=comparable_point_count,
            temporal_span_days=temporal_span_days,
            yoy_change=yoy_change,
            qoq_change=qoq_change,
            ttm_value=ttm_value,
            trend_state=trend_state,
            turning_point_state=turning_point_state,
            anomaly_flags=anomaly_flags,
            comparison_status=comparison_status,
            reason_codes=reason_codes,
        )

    def _trend(self, changes: Sequence[Decimal]) -> TrendState:
        directions = tuple(
            1 if change > self._stable_threshold else -1 if change < -self._stable_threshold else 0
            for change in changes
        )
        if all(item == 1 for item in directions):
            return "RISING"
        if all(item == -1 for item in directions):
            return "FALLING"
        if all(item == 0 for item in directions):
            return "STABLE"
        return "MIXED"

    def _turning_point(self, changes: Sequence[Decimal]) -> TurningPointState:
        directions = tuple(
            1 if change > self._stable_threshold else -1 if change < -self._stable_threshold else 0
            for change in changes
        )
        non_stable = tuple(item for item in directions if item)
        if len(non_stable) < 2 or len(set(non_stable)) == 1:
            return "NOT_OBSERVED"
        if len(non_stable) >= 3 and non_stable[-1] == non_stable[-2] != non_stable[-3]:
            return "CONFIRMED"
        return "POSSIBLE"

    @property
    def _minimum_points(self) -> int:
        return self._policies.integer_value("temporal_analysis", "minimum_comparable_points")

    @property
    def _stable_threshold(self) -> Decimal:
        return self._policies.decimal_value("temporal_analysis", "stable_relative_change")

    @property
    def _anomaly_threshold(self) -> Decimal:
        return self._policies.decimal_value("temporal_analysis", "anomaly_relative_change")

    @staticmethod
    def _utc(value: datetime, *, field: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field} must be timezone-aware")
        return value.astimezone(timezone.utc)

    @staticmethod
    def _evidence_refs(
        observations: Sequence[FinancialPeriodObservation],
    ) -> tuple[EvidenceRef, ...]:
        values = {
            (item.evidence_id, item.revision, item.content_fingerprint): item
            for observation in observations
            for item in observation.evidence_refs
        }
        return tuple(values[key] for key in sorted(values))

    @staticmethod
    def _assumption_refs(
        observations: Sequence[FinancialPeriodObservation],
    ) -> tuple[AssumptionRef, ...]:
        values = {
            (item.assumption_key, item.assumption_version, item.content_fingerprint): item
            for observation in observations
            for item in observation.assumption_refs
        }
        return tuple(values[key] for key in sorted(values))
