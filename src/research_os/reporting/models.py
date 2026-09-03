from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from research_os.application.result import RunVersionSet
from research_os.contracts.evidence import EvidenceRef
from research_os.runtime.context import BaselineFingerprint


class _FrozenReportModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PresentedArtifact(_FrozenReportModel):
    artifact_id: str
    schema_version: str
    type_id: str
    producer_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    value_fingerprint: str
    payload: JsonValue


class HumanReadableResearchView(_FrozenReportModel):
    company_id: str
    decision_ts: datetime
    baseline: BaselineFingerprint
    versions: RunVersionSet
    execution_completion: str
    research_readiness: str
    semantic_fingerprint: str
    artifacts: tuple[PresentedArtifact, ...] = Field(default_factory=tuple)

    def artifact(self, artifact_id: str) -> PresentedArtifact | None:
        return next(
            (item for item in self.artifacts if item.artifact_id == artifact_id),
            None,
        )


class ReportArtifactBlock(_FrozenReportModel):
    artifact_id: str
    title: str
    schema_version: str
    payload: JsonValue


class ReportSection(_FrozenReportModel):
    section_id: str
    title: str
    artifacts: tuple[ReportArtifactBlock, ...] = Field(default_factory=tuple)


class AuditArtifactLineage(_FrozenReportModel):
    artifact_id: str
    schema_version: str
    type_id: str
    producer_ids: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    value_fingerprint: str


class ResearchReportDocument(_FrozenReportModel):
    company_id: str
    decision_ts: datetime
    research_os_version: str
    core_api_version: str
    plugin_api_version: str
    snapshot_schema_version: str
    execution_completion: str
    research_readiness: str
    semantic_fingerprint: str
    sections: tuple[ReportSection, ...] = Field(default_factory=tuple)
    audit_appendix: tuple[AuditArtifactLineage, ...] = Field(default_factory=tuple)


class MarkdownRenderResult(_FrozenReportModel):
    content: str
    semantic_fingerprint: str
    renderer_version: str


JsonObject = dict[str, Any]
