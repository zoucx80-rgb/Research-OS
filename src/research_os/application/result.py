from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research_os.completion import ExecutionCompletionResult
from research_os.contracts.artifacts import ArtifactSnapshot
from research_os.plugins.resolver import StrategyResolution
from research_os.readiness import ResearchReadinessAssessment
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.runtime.modules import ModuleResult


class _FrozenResultModel(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    def __getattribute__(self, name: str) -> Any:
        value = super().__getattribute__(name)
        if name == "module_results":
            return copy.deepcopy(value)
        return value

    def model_post_init(self, __context: object) -> None:
        object.__setattr__(
            self,
            "module_results",
            copy.deepcopy(object.__getattribute__(self, "module_results")),
        )


class VersionIdentity(BaseModel):
    model_config = ConfigDict(frozen=True)

    component_id: str
    version: str


class RunVersionSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    research_os_version: str
    core_api_version: str
    plugin_api_version: str
    snapshot_schema_version: str
    http_api_version: str
    modules: tuple[VersionIdentity, ...] = Field(default_factory=tuple)
    plugins: tuple[VersionIdentity, ...] = Field(default_factory=tuple)
    metrics: tuple[VersionIdentity, ...] = Field(default_factory=tuple)
    policies: tuple[VersionIdentity, ...] = Field(default_factory=tuple)
    external: tuple[VersionIdentity, ...] = Field(default_factory=tuple)


class ComponentFingerprint(BaseModel):
    model_config = ConfigDict(frozen=True)

    component_id: str
    component_type: Literal["module", "plugin"]
    component_version: str
    api_version: str | None = None
    fingerprint: str


class ResearchSnapshotDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    schema_version: Literal["2.0"] = "2.0"
    research_digest: str
    integrity_digest: str


class ResearchRunResult(_FrozenResultModel):
    run_id: str
    company: CompanyRef
    decision_ts: datetime
    baseline: BaselineFingerprint
    strategy_resolution: StrategyResolution
    artifacts: ArtifactSnapshot
    module_results: tuple[ModuleResult, ...]
    execution_completion: ExecutionCompletionResult
    research_readiness: ResearchReadinessAssessment
    versions: RunVersionSet
    component_fingerprints: tuple[ComponentFingerprint, ...]
    snapshot: ResearchSnapshotDescriptor | None = None

    @model_validator(mode="after")
    def _reject_incomplete_ready(self) -> ResearchRunResult:
        if (
            self.execution_completion.final_status == "INCOMPLETE"
            and self.research_readiness.final_status == "READY"
        ):
            raise ValueError("INCOMPLETE execution cannot produce READY research")
        return self
