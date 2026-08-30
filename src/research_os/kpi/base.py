from typing import Any, Mapping, Protocol

from pydantic import BaseModel, Field


class MetricResult(BaseModel):
    metric_id: str
    value: float | None
    unit: str | None = None
    status: str = "valid"
    formula_version: str
    evidence_ids: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    period_label: str | None = None
    period_days: int | None = None
    annualized: bool | None = None


class KpiPack(Protocol):
    """Low-level KPI calculation contract used behind industry plugins."""

    pack_id: str
    pack_version: str
    eligible_business_models: tuple[str, ...]
    required_facts: frozenset[str]
    optional_facts: frozenset[str]
    missing_policy: str
    valuation_preferences: tuple[str, ...]

    def calculate(self, facts: Mapping[str, Any]) -> list[MetricResult]: ...
