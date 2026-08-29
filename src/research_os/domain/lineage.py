from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CalculationLineage(BaseModel):
    model_config = ConfigDict(frozen=True)
    formula: str
    input_evidence_ids: list[str] = Field(min_length=1)
    output: Any
    unit: str | None = None
    calculation_version: str


class AssumptionLineage(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: Literal["ASSUMPTION"] = "ASSUMPTION"
    value: Any
    unit: str | None = None
    rationale: str
    source_evidence_ids: list[str] = Field(default_factory=list)


class InferenceLineage(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: Literal["INFERENCE"] = "INFERENCE"
    statement: str
    evidence_ids: list[str] = Field(min_length=1)
    confidence_grade: str
