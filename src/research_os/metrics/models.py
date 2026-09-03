from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_os.contracts.metrics import MetricDefinition as ContractMetricDefinition


class ComparisonBasis(StrEnum):
    YOY_PERIOD = "YOY_PERIOD"
    QOQ_PERIOD = "QOQ_PERIOD"
    END_VS_BEGIN = "END_VS_BEGIN"
    POINT_IN_TIME = "POINT_IN_TIME"
    SAME_PERIOD = "SAME_PERIOD"


class MetricInputDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fact_id: str
    role: str
    required: bool = True

    @field_validator("fact_id", "role")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("metric input fields must be non-empty")
        return normalized


class MetricDefinition(ContractMetricDefinition):
    """Implemented metric semantics extending the frozen M1 minimum contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    economic_meaning: str
    formula_id: str
    required_inputs: tuple[MetricInputDefinition, ...] = Field(default_factory=tuple)
    valid_comparison_bases: frozenset[ComparisonBasis] = Field(default_factory=frozenset)
    annualization_policy: str | None = None
    accounting_scope_policy: str = "exact"

    @field_validator(
        "economic_meaning",
        "formula_id",
        "accounting_scope_policy",
    )
    @classmethod
    def _implemented_fields_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("implemented metric definition fields must be non-empty")
        return normalized


__all__ = ["ComparisonBasis", "MetricDefinition", "MetricInputDefinition"]
