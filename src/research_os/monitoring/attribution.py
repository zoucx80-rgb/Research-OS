from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_os.contracts.evidence import EvidenceRef


AttributionCategory = Literal[
    "DATA",
    "BASIS",
    "FORMULA",
    "MODEL",
    "ASSUMPTION",
    "DRIVER",
    "TIMING",
    "EXOGENOUS",
    "PRESENTATION",
    "UNKNOWN",
]
ProposedAttributionCategory = Literal[
    "DATA",
    "BASIS",
    "FORMULA",
    "MODEL",
    "ASSUMPTION",
    "DRIVER",
    "TIMING",
    "EXOGENOUS",
    "PRESENTATION",
]


class PriorStatementRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    artifact_key: str
    statement_key: str
    statement: str
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)

    @field_validator("run_id", "artifact_key", "statement_key", "statement")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("prior-statement reference fields must be non-empty")
        return normalized


class AnalysisMethodRef(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    method_id: str
    method_version: str
    description: str

    @field_validator("method_id", "method_version", "description")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("analysis-method reference fields must be non-empty")
        return normalized


class AttributionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    attribution_id: str
    proposed_category: ProposedAttributionCategory
    prior_statement: PriorStatementRef
    realized_evidence_refs: tuple[EvidenceRef, ...]
    analysis_method: AnalysisMethodRef
    rationale: str
    exogenous_event: bool = False

    @field_validator("attribution_id", "rationale")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("attribution fields must be non-empty")
        return normalized


class AttributionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    attribution_id: str
    proposed_category: ProposedAttributionCategory
    category: AttributionCategory
    prior_statement: PriorStatementRef
    realized_evidence_refs: tuple[EvidenceRef, ...]
    analysis_method: AnalysisMethodRef
    rationale: str


class ProcessChangeTarget(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    target_type: Literal["POLICY", "METRIC", "PROCEDURE"]
    target_id: str

    @field_validator("target_id")
    @classmethod
    def _specific_target_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("process-change target must be specific")
        return normalized


class ProcessChangeCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str
    target: ProcessChangeTarget
    rationale: str
    attribution_ids: tuple[str, ...] = Field(min_length=1)

    @field_validator("candidate_id", "rationale")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("process-change candidate fields must be non-empty")
        return normalized


def attribute_error(request: AttributionRequest) -> AttributionRecord:
    if not request.realized_evidence_refs:
        category: AttributionCategory = "UNKNOWN"
        rationale = "Insufficient realized evidence for supported attribution."
    elif request.exogenous_event:
        category = "EXOGENOUS"
        rationale = request.rationale
    elif request.proposed_category == "EXOGENOUS":
        category = "UNKNOWN"
        rationale = "Insufficient evidence that the error was caused by an exogenous event."
    else:
        category = request.proposed_category
        rationale = request.rationale
    return AttributionRecord(
        attribution_id=request.attribution_id,
        proposed_category=request.proposed_category,
        category=category,
        prior_statement=request.prior_statement,
        realized_evidence_refs=request.realized_evidence_refs,
        analysis_method=request.analysis_method,
        rationale=rationale,
    )


__all__ = [
    "AnalysisMethodRef",
    "AttributionCategory",
    "AttributionRecord",
    "AttributionRequest",
    "PriorStatementRef",
    "ProcessChangeCandidate",
    "ProcessChangeTarget",
    "attribute_error",
]
