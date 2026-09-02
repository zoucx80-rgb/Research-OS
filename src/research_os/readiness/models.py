from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research_os.completion.models import FinalStatus as ExecutionStatus
from research_os.contracts.artifacts import ArtifactKey


ReadinessStatus = Literal["READY", "NOT_READY"]
DimensionStatus = Literal["PASS", "INCOMPLETE", "NOT_APPLICABLE"]


@dataclass(frozen=True, slots=True)
class ReadinessRequirement:
    dimension_id: str
    artifact_keys: tuple[ArtifactKey[Any], ...] = ()

    def __post_init__(self) -> None:
        if not self.dimension_id.strip():
            raise ValueError("readiness dimension_id must be non-empty")
        if any(not isinstance(key, ArtifactKey) for key in self.artifact_keys):
            raise TypeError("readiness requirements must use typed ArtifactKey values")


class ReadinessDimension(BaseModel):
    model_config = ConfigDict(frozen=True)

    dimension_id: str
    status: DimensionStatus
    required_artifacts: tuple[str, ...] = Field(default_factory=tuple)


class ResearchReadinessAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    final_status: ReadinessStatus
    dimensions: tuple[ReadinessDimension, ...]
    blocking_dimensions: tuple[str, ...] = Field(default_factory=tuple)
    execution_status: ExecutionStatus

    @model_validator(mode="after")
    def _validate_statuses(self) -> ResearchReadinessAssessment:
        blocking = tuple(sorted(set(self.blocking_dimensions)))
        if self.execution_status == "INCOMPLETE" and self.final_status == "READY":
            raise ValueError("INCOMPLETE execution cannot be READY")
        if (self.final_status == "READY") != (not blocking):
            raise ValueError("readiness status must match blocking dimensions")
        if len({item.dimension_id for item in self.dimensions}) != len(self.dimensions):
            raise ValueError("readiness dimensions must be unique")
        object.__setattr__(self, "blocking_dimensions", blocking)
        return self
