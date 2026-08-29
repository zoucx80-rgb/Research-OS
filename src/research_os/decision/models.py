from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from research_os.version import RESEARCH_OS_VERSION

FundamentalState = Literal["IMPROVING", "STABLE", "DETERIORATING", "UNCERTAIN"]
ValuationState = Literal["CHEAP", "FAIR", "EXPENSIVE", "UNRELIABLE"]
ExpectationState = Literal["UNDER_EXPECTED", "IN_LINE", "OVER_EXPECTED", "MIXED"]
ThesisState = Literal["STRENGTHENING", "ACTIVE", "WEAKENING", "FALSIFIED"]
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
    company_id: str
    fundamental_state: FundamentalState
    valuation_state: ValuationState
    expectation_state: ExpectationState
    thesis_state: ThesisState
    evidence_confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    claim_ids: list[str] = Field(default_factory=list)
    decision_ts: datetime
    research_os_version: str = RESEARCH_OS_VERSION
    material_risk: bool = False


class DecisionStateRecord(BaseModel):
    company_id: str
    state: ResearchDecisionState
    decision_ts: datetime
    evidence_ids: list[str]
    claim_ids: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    research_os_version: str = RESEARCH_OS_VERSION
