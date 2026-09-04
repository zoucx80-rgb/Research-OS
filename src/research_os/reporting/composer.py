from __future__ import annotations

from collections import defaultdict

from .models import (
    AuditArtifactLineage,
    HumanReadableResearchView,
    ReportArtifactBlock,
    ReportSection,
    ResearchReportDocument,
)
from .projectors import section_title


_SECTION_ORDER = (
    "decision",
    "scope",
    "financial",
    "capital",
    "thesis",
    "expectation",
    "valuation",
    "monitoring",
    "readiness",
    "methodology",
    "other",
)


class ResearchReportComposer:
    """Compose a decision-first report document from presentation-safe projections only."""

    version = "research-report-composer@2.1.0"

    def compose(self, view: HumanReadableResearchView) -> ResearchReportDocument:
        if not isinstance(view, HumanReadableResearchView):
            raise TypeError("ResearchReportComposer.compose requires HumanReadableResearchView")
        grouped: dict[str, list[ReportArtifactBlock]] = defaultdict(list)
        for artifact in view.artifacts:
            if artifact.audit_only:
                continue
            grouped[artifact.section_id].append(
                ReportArtifactBlock(
                    artifact_id=artifact.artifact_id,
                    title=artifact.title or artifact.artifact_id,
                    schema_version=artifact.schema_version,
                    payload=artifact.payload,
                )
            )
        sections = tuple(
            ReportSection(
                section_id=section_id,
                title=section_title(section_id),
                artifacts=tuple(grouped.get(section_id, ())),
            )
            for section_id in _SECTION_ORDER
            if grouped.get(section_id)
        )
        audit = tuple(
            AuditArtifactLineage(
                artifact_id=artifact.artifact_id,
                schema_version=artifact.schema_version,
                type_id=artifact.type_id,
                producer_ids=artifact.producer_ids,
                evidence_refs=artifact.evidence_refs,
                value_fingerprint=artifact.value_fingerprint,
            )
            for artifact in view.artifacts
        )
        return ResearchReportDocument(
            company_id=view.company_id,
            decision_ts=view.decision_ts,
            research_os_version=view.versions.research_os_version,
            core_api_version=view.versions.core_api_version,
            plugin_api_version=view.versions.plugin_api_version,
            snapshot_schema_version=view.versions.snapshot_schema_version,
            execution_completion=view.execution_completion,
            research_readiness=view.research_readiness,
            semantic_fingerprint=view.semantic_fingerprint,
            sections=sections,
            audit_appendix=audit,
        )
