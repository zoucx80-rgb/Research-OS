from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.contracts.artifact_values import DomainArtifact, LineageValue, ThesisPortfolio
from research_os.contracts.evidence import EvidenceRef
from research_os.version import RESEARCH_OS_VERSION


FundamentalState = Literal["IMPROVING", "STABLE", "DETERIORATING", "UNCERTAIN"]
ValuationState = Literal["CHEAP", "FAIR", "EXPENSIVE", "UNRELIABLE"]
ExpectationState = Literal["UNDER_EXPECTED", "IN_LINE", "OVER_EXPECTED", "MIXED", "UNKNOWN"]
ThesisState = Literal["STRENGTHENING", "ACTIVE", "WEAKENING", "FALSIFIED", "UNRESOLVED"]
ResearchDecisionState = Literal[
    "HIGH_CONVICTION_WATCH",
    "ACCUMULATION_CANDIDATE",
    "WAIT_FOR_CONFIRMATION",
    "HOLD_AND_MONITOR",
    "RISK_REVIEW",
    "THESIS_BROKEN",
    "INSUFFICIENT_EVIDENCE",
]


class DecisionContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    company_id: str
    fundamental_state: FundamentalState
    valuation_state: ValuationState
    expectation_state: ExpectationState
    thesis_portfolio: ThesisPortfolio
    evidence_confidence: float = Field(ge=0, le=1)
    claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    decision_ts: datetime
    research_os_version: str = RESEARCH_OS_VERSION
    material_funding_risk: bool = False
    forecast_state: Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE", "UNKNOWN"] = (
        "UNKNOWN"
    )
    sufficiency_state: Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT_EVIDENCE"] = (
        "INSUFFICIENT_EVIDENCE"
    )
    scenario_state: Literal["AVAILABLE", "UNAVAILABLE", "ADVERSE"] = "UNAVAILABLE"

    @field_validator("decision_ts")
    @classmethod
    def _decision_time_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decision_ts must be timezone-aware")
        return value.astimezone(timezone.utc)


class DecisionDimensionAssessment(LineageValue):
    dimension: str
    state: str
    availability: Literal["AVAILABLE", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"]
    artifact_ids: tuple[str, ...] = Field(default_factory=tuple)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("dimension", "state")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("decision dimension identity and state must be non-empty")
        return normalized

    @field_validator("artifact_ids", "reason_codes")
    @classmethod
    def _canonical_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("decision dimension values must be non-empty")
        return tuple(sorted(set(normalized)))


class DecisionInputAssessment(DomainArtifact):
    dimensions: tuple[DecisionDimensionAssessment, ...] = Field(default_factory=tuple)
    evidence_confidence: Decimal = Field(ge=0, le=1)
    blocking_reason_codes: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("blocking_reason_codes")
    @classmethod
    def _canonical_reasons(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(set(value)))

    @model_validator(mode="after")
    def _unique_dimensions(self) -> Self:
        names = tuple(item.dimension for item in self.dimensions)
        if len(names) != len(set(names)):
            raise ValueError("decision assessment dimensions must be unique")
        canonical = tuple(sorted(self.dimensions, key=lambda item: item.dimension))
        if canonical != self.dimensions:
            object.__setattr__(self, "dimensions", canonical)
        return self

    def require_dimension(self, dimension: str) -> DecisionDimensionAssessment:
        item = next((item for item in self.dimensions if item.dimension == dimension), None)
        if item is None:
            raise KeyError(f"missing decision dimension: {dimension}")
        return item


class DecisionDerivation(DomainArtifact):
    rule_id: str
    rule_version: str
    input_states: tuple[DecisionDimensionAssessment, ...]
    output_state: ResearchDecisionState
    supporting_reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    blocking_reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    used_thesis_ids: tuple[str, ...] = Field(default_factory=tuple)
    used_claim_ids: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("rule_id", "rule_version")
    @classmethod
    def _rule_identity(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("decision derivation rule identity must be non-empty")
        return normalized

    @field_validator(
        "supporting_reason_codes",
        "blocking_reason_codes",
        "used_thesis_ids",
        "used_claim_ids",
    )
    @classmethod
    def _canonical_derivation_values(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(set(value)))

    @model_validator(mode="after")
    def _unique_input_states(self) -> Self:
        names = tuple(item.dimension for item in self.input_states)
        if len(names) != len(set(names)):
            raise ValueError("decision derivation input dimensions must be unique")
        canonical = tuple(sorted(self.input_states, key=lambda item: item.dimension))
        if canonical != self.input_states:
            object.__setattr__(self, "input_states", canonical)
        return self


class DecisionStateRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    company_id: str
    state: ResearchDecisionState
    decision_ts: datetime
    used_thesis_ids: tuple[str, ...] = Field(default_factory=tuple)
    used_claim_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    research_os_version: str = RESEARCH_OS_VERSION
    fundamental_state: FundamentalState | None = None
    valuation_state: ValuationState | None = None
    expectation_state: ExpectationState | None = None
    thesis_state: ThesisState | None = None
    evidence_confidence: float | None = Field(default=None, ge=0, le=1)


__all__ = [
    "DecisionContext",
    "DecisionDerivation",
    "DecisionDimensionAssessment",
    "DecisionInputAssessment",
    "DecisionStateRecord",
    "ExpectationState",
    "FundamentalState",
    "ResearchDecisionState",
    "ThesisState",
    "ValuationState",
]
