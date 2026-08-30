from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Falsifier(BaseModel):
    metric: str
    operator: Literal["<", "<=", ">", ">=", "=="]
    threshold: float
    description: str | None = None

    def label(self):
        return f"{self.metric} {self.operator} {float(self.threshold)}"


class ThesisSignalAssessment(BaseModel):
    status: Literal["SUPPORTED", "MIXED", "INSUFFICIENT"]
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class Thesis(BaseModel):
    thesis_id: str
    company_id: str
    title: str
    statement: str
    mechanism: str
    anti_thesis: str | None = None
    status: Literal["new", "active", "strengthening", "weakening", "falsified", "expired"] = "new"
    time_horizon: str | None = None
    supporting_drivers: list[str] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    falsifiers: list[Falsifier] = Field(default_factory=list)
    verification_metrics: list[str] = Field(default_factory=list)
    next_check_date: date | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    triggered_falsifiers: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_active(self):
        if not self.anti_thesis:
            raise ValueError("thesis requires explicit anti-thesis")
        if self.status in {"active", "strengthening", "weakening"} and (
            not self.falsifiers or self.next_check_date is None
        ):
            raise ValueError("active thesis requires falsifier and next check")
        return self
