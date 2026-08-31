from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Scalar = float | int | str | bool | None


class OperatingObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    category: str
    metric_id: str
    value: Scalar = None
    unit: str | None = None
    period: str | None = None
    as_of: datetime | None = None
    entity_label: str | None = None
    segment_label: str | None = None
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class FinancialSeriesPoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    period: str
    period_end: datetime
    value: float | None = None
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class FinancialTimeSeries(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric_id: str
    unit: str | None = None
    points: tuple[FinancialSeriesPoint, ...] = Field(default_factory=tuple)


class CashFlowQualityInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    net_profit: float | None = None
    operating_cash_flow: float | None = None
    working_capital_contribution: float | None = None
    other_adjustments: float | None = None
    capex_cash: float | None = None
    unit: str = "CNY"
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    assumption_ids: tuple[str, ...] = Field(default_factory=tuple)


class CashFlowQualityBridge(BaseModel):
    model_config = ConfigDict(frozen=True)

    net_profit: float | None = None
    operating_cash_flow: float | None = None
    working_capital_contribution: float | None = None
    other_adjustments: float | None = None
    capex_cash: float | None = None
    simplified_fcf: float | None = None
    unit: str = "CNY"
    methodology: Literal["simplified_fcf_not_fcff"] = "simplified_fcf_not_fcff"
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    assumption_ids: tuple[str, ...] = Field(default_factory=tuple)


class ConsensusObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    publish_ts: datetime
    forecast_period: str
    metric: str
    value: float
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class ConsensusDistribution(BaseModel):
    model_config = ConfigDict(frozen=True)

    metric: str
    forecast_period: str
    source_count: int = 0
    low: float | None = None
    median: float | None = None
    high: float | None = None
    dispersion: float | None = None
    breadth: Literal["none", "single_source", "multi_source"] = "none"
    source_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class PeerComparableObservation(BaseModel):
    model_config = ConfigDict(frozen=True)

    peer_id: str
    peer_role: str
    metric: str
    value: float | None = None
    period: str
    period_type: str
    scope: str
    accounting_definition: str
    frequency: str
    share_count_convention: str
    business_model_interpretation: str
    product_or_segment: str | None = None
    unit: str | None = None
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class SensitivityCase(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    driver_id: str
    base_value: float | None = None
    shock_label: str
    shock_value: float | None = None
    affected_metric: str
    result: float | None = None
    result_low: float | None = None
    result_high: float | None = None
    probability: float | None = Field(default=None, ge=0, le=1)
    formula_version: str
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    assumption_ids: tuple[str, ...] = Field(default_factory=tuple)


class MonitoringRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    rule_id: str
    metric: str
    operator: Literal["lt", "lte", "gt", "gte", "eq"]
    threshold: float
    frequency: str
    rationale: str
    source_type: Literal["analyst_assumption", "company_guidance", "contract", "industry_reference", "other"]
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    assumption_ids: tuple[str, ...] = Field(default_factory=tuple)


class VerificationCalendarEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    label: str
    event_type: str
    due_ts: datetime | None = None
    status: Literal["scheduled", "pending_date", "completed"] = "pending_date"
    information_value: str | None = None
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class PriorRunReviewInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    prior_statement: str
    metric: str | None = None
    period: str | None = None
    predicted_value: float | None = None
    actual_value: float | None = None
    tolerance: float | None = Field(default=None, ge=0)
    prior_evidence_ids: tuple[str, ...] = Field(default_factory=tuple)
    actual_evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class PriorRunReviewItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    prior_statement: str
    metric: str | None = None
    period: str | None = None
    predicted_value: float | None = None
    actual_value: float | None = None
    tolerance: float | None = None
    error: float | None = None
    absolute_error: float | None = None
    status: Literal["HIT", "MISS", "UNKNOWN"] = "UNKNOWN"
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class PriorRunReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: tuple[PriorRunReviewItem, ...] = Field(default_factory=tuple)
    scored_count: int = 0
    hit_count: int = 0
    miss_count: int = 0
    process_change_candidates: tuple[str, ...] = Field(default_factory=tuple)
