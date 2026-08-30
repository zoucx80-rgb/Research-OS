from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


QuestionStatus = Literal[
    "ANSWERED",
    "EVIDENCE_MISSING",
    "CAPABILITY_MISSING",
    "NOT_APPLICABLE",
]


class ResearchQuestionSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    text: str
    required_capabilities: list[str] = Field(default_factory=list)
    evidence_keys: list[str] = Field(default_factory=list)


class ResearchQuestionAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    question_id: str
    text: str
    status: QuestionStatus
    answer: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence_keys: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)


class ReportContribution(BaseModel):
    model_config = ConfigDict(frozen=True)

    contribution_id: str
    section: str
    order: int
    artifact_keys: list[str] = Field(default_factory=list)
    required: bool = False
    title: str = ""
    description: str = ""
    research_questions: list[str] = Field(default_factory=list)
    question_specs: list[ResearchQuestionSpec] = Field(default_factory=list)
