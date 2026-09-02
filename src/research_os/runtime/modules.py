from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_os.contracts.artifacts import ArtifactKey, ArtifactWrite
from research_os.runtime.context import ResearchContext
from research_os.runtime.state import ResearchStateView


ModuleStatus = Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"]


class ModuleSpec(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    module_id: str
    module_version: str
    requires: frozenset[ArtifactKey[Any]] = Field(default_factory=frozenset)
    provides: frozenset[ArtifactKey[Any]] = Field(default_factory=frozenset)
    required_for_completion: bool = True

    @field_validator("module_id", "module_version")
    @classmethod
    def _non_empty_identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("module identity fields must be non-empty")
        return value

    @field_validator("requires", "provides")
    @classmethod
    def _valid_artifact_keys(
        cls, values: frozenset[ArtifactKey[Any]]
    ) -> frozenset[ArtifactKey[Any]]:
        if any(not isinstance(value, ArtifactKey) for value in values):
            raise ValueError("typed artifact fields must contain ArtifactKey values")
        return values


class ModuleResult(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")

    module_id: str
    status: ModuleStatus
    diagnostics: tuple[str, ...] = ()
    writes: tuple[ArtifactWrite[Any], ...] = ()


@runtime_checkable
class ResearchModule(Protocol):
    spec: ModuleSpec

    def run(
        self,
        context: ResearchContext,
        state: ResearchStateView,
    ) -> ModuleResult: ...
