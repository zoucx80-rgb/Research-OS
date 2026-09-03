from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import FinancialValue


class CalculationLineage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lineage_type: Literal["CALCULATION"] = "CALCULATION"
    formula: str
    input_evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)
    output: FinancialValue
    calculation_version: str


class AssumptionLineage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lineage_type: Literal["ANALYST_ASSUMPTION"] = "ANALYST_ASSUMPTION"
    value: FinancialValue
    rationale: str
    source_evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)


class InferenceLineage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lineage_type: Literal["INFERENCE"] = "INFERENCE"
    statement: str
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)
    confidence_grade: str
