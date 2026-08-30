from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConsensusVintage(BaseModel):
    model_config = ConfigDict(frozen=True)
    company_id: str
    as_of: datetime
    forecast_period: str
    revenue: float | None = None
    net_profit: float | None = None
    eps: float | None = None
    gross_margin: float | None = None
    expectation_type: str = "sell_side"
    source_count: int | None = None
    source_quality: float | None = Field(default=None, ge=0, le=1)


class ExpectationSnapshot(ConsensusVintage):
    decision_ts: datetime


class ExpectationEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)
    expectation_source: str
    expectation_publish_ts: datetime
    expectation_period: str
    metric: str
    expected_value: float
    actual_value: float
    surprise: float
    vintage: str


class ExpectationGapResult(BaseModel):
    """Evidence-bounded gap between market expectation and the Research OS view."""

    model_config = ConfigDict(frozen=True)

    metric: str
    market_value: float | None = None
    market_range_low: float | None = None
    market_range_high: float | None = None
    market_direction: str | None = None
    os_value: float | None = None
    os_range_low: float | None = None
    os_range_high: float | None = None
    os_direction: str | None = None
    direction: str = "MIXED"
    magnitude: float | None = None
    unit: str | None = None
    comparison_basis: str | None = None
    source_count: int | None = None
    source_quality: float | None = Field(default=None, ge=0, le=1)
    age_days: int | None = None
    post_event_consensus: bool | None = None
    limitation: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExpectationService:
    def __init__(self):
        self._items = []

    def add(self, vintage: ConsensusVintage):
        self._items.append(vintage)
        return vintage

    def snapshot(
        self,
        company_id: str,
        decision_ts: datetime,
        expectation_type: str = "sell_side",
    ):
        candidates = [
            v
            for v in self._items
            if v.company_id == company_id
            and v.as_of <= decision_ts
            and v.expectation_type == expectation_type
        ]
        if not candidates:
            raise LookupError(f"no expectation available for {company_id} at {decision_ts}")
        v = max(candidates, key=lambda x: x.as_of)
        return ExpectationSnapshot(**v.model_dump(), decision_ts=decision_ts)
