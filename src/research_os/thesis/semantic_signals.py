from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SignalDirection = Literal["POSITIVE", "NEGATIVE", "NEUTRAL", "UNKNOWN"]
ComparisonStatus = Literal["COMPARABLE", "NOT_COMPARABLE", "INSUFFICIENT_EVIDENCE"]


class GrowthComparisonRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    left_metric: str
    right_metric: str
    spread_threshold: float
    adverse_label: str


class DirectionalSignal(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric: str
    direction: SignalDirection
    semantic_label: str
    value: float | None = None
    comparison_basis: str | None = None
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    reason_code: str | None = None


class ComparisonAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    left_metric: str
    right_metric: str
    status: ComparisonStatus
    reason: str
    left_basis: str | None = None
    right_basis: str | None = None
    left_kind: str | None = None
    right_kind: str | None = None


class SemanticSignalAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["SUPPORTED", "MIXED", "INSUFFICIENT"]
    signals: tuple[DirectionalSignal, ...] = Field(default_factory=tuple)
    comparisons: tuple[ComparisonAssessment, ...] = Field(default_factory=tuple)
    positive_signals: tuple[str, ...] = Field(default_factory=tuple)
    negative_signals: tuple[str, ...] = Field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


def assess_comparability(*, rule: GrowthComparisonRule, left, right) -> ComparisonAssessment:
    if left is None or right is None:
        return ComparisonAssessment(
            rule_id=rule.rule_id,
            left_metric=rule.left_metric,
            right_metric=rule.right_metric,
            status="INSUFFICIENT_EVIDENCE",
            reason="comparison requires both metrics",
        )

    left_basis = getattr(left, "comparison_basis", None)
    right_basis = getattr(right, "comparison_basis", None)
    left_kind = getattr(left, "metric_kind", None)
    right_kind = getattr(right, "metric_kind", None)

    if not left_basis or not right_basis or not left_kind or not right_kind:
        return ComparisonAssessment(
            rule_id=rule.rule_id,
            left_metric=rule.left_metric,
            right_metric=rule.right_metric,
            status="NOT_COMPARABLE",
            reason="comparison basis or metric kind is missing",
            left_basis=left_basis,
            right_basis=right_basis,
            left_kind=left_kind,
            right_kind=right_kind,
        )

    if left_basis != right_basis:
        return ComparisonAssessment(
            rule_id=rule.rule_id,
            left_metric=rule.left_metric,
            right_metric=rule.right_metric,
            status="NOT_COMPARABLE",
            reason="comparison bases differ",
            left_basis=left_basis,
            right_basis=right_basis,
            left_kind=left_kind,
            right_kind=right_kind,
        )

    if left_kind != right_kind:
        return ComparisonAssessment(
            rule_id=rule.rule_id,
            left_metric=rule.left_metric,
            right_metric=rule.right_metric,
            status="NOT_COMPARABLE",
            reason="metric economic kinds differ",
            left_basis=left_basis,
            right_basis=right_basis,
            left_kind=left_kind,
            right_kind=right_kind,
        )

    if left_basis not in {"YOY_PERIOD", "QOQ_PERIOD", "END_VS_BEGIN", "POINT_IN_TIME"}:
        return ComparisonAssessment(
            rule_id=rule.rule_id,
            left_metric=rule.left_metric,
            right_metric=rule.right_metric,
            status="NOT_COMPARABLE",
            reason="comparison basis is not recognized",
            left_basis=left_basis,
            right_basis=right_basis,
            left_kind=left_kind,
            right_kind=right_kind,
        )

    return ComparisonAssessment(
        rule_id=rule.rule_id,
        left_metric=rule.left_metric,
        right_metric=rule.right_metric,
        status="COMPARABLE",
        reason="comparison basis and metric kind are compatible",
        left_basis=left_basis,
        right_basis=right_basis,
        left_kind=left_kind,
        right_kind=right_kind,
    )
