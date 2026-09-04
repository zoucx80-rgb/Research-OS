from __future__ import annotations

from research_os.application.result import ResearchRunResult

from .fingerprint import semantic_fingerprint
from .models import HumanReadableResearchView, PresentedArtifact
from .projectors import project_artifact


class ResearchViewPresenter:
    """Project a frozen Core API 2.0 result without re-running research semantics."""

    version = "professional-research-view@2.1.0"

    def present(self, result: ResearchRunResult) -> HumanReadableResearchView:
        if not isinstance(result, ResearchRunResult):
            raise TypeError("ResearchViewPresenter.present requires ResearchRunResult")
        artifacts = []
        for envelope in result.artifacts.envelopes():
            projection = project_artifact(envelope.key.artifact_id, envelope.value)
            artifacts.append(
                PresentedArtifact(
                    artifact_id=envelope.key.artifact_id,
                    schema_version=envelope.key.schema_version,
                    type_id=envelope.key.value_type.__qualname__,
                    producer_ids=envelope.producer_ids,
                    evidence_refs=envelope.evidence_refs,
                    value_fingerprint=envelope.value_fingerprint,
                    section_id=projection.section_id,
                    title=projection.title,
                    audit_only=projection.audit_only,
                    payload=projection.payload,
                )
            )
        return HumanReadableResearchView(
            company_id=result.company.company_id,
            decision_ts=result.decision_ts,
            baseline=result.baseline,
            versions=result.versions,
            execution_completion=result.execution_completion.final_status,
            research_readiness=result.research_readiness.final_status,
            semantic_fingerprint=semantic_fingerprint(result.artifacts),
            artifacts=tuple(artifacts),
        )
