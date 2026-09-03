from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_os.contracts.artifact_values import ThesisPortfolio
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

    @field_validator("decision_ts")
    @classmethod
    def _decision_time_is_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("decision_ts must be timezone-aware")
        return value.astimezone(timezone.utc)


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
    "DecisionStateRecord",
    "ExpectationState",
    "FundamentalState",
    "ResearchDecisionState",
    "ThesisState",
    "ValuationState",
]
