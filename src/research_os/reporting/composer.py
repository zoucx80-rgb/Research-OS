from __future__ import annotations

from collections import defaultdict

from .models import (
    AuditArtifactLineage,
    HumanReadableResearchView,
    ReportArtifactBlock,
    ReportSection,
    ResearchReportDocument,
)


_SECTION_ORDER = (
    ("scope", "研究范围与方法"),
    ("financial", "财务、经营与资本效率"),
    ("thesis", "驱动、投资逻辑与反证"),
    ("expectation", "市场预期与预测"),
    ("valuation", "同行、估值与决策"),
    ("monitoring", "监控、验证与研究就绪度"),
    ("quality", "证据质量与验证"),
    ("other", "其他类型化研究产物"),
)


def _section_id(artifact_id: str) -> str:
    if artifact_id.startswith(("business_model.", "strategy.", "methodology.")):
        return "scope"
    if artifact_id.startswith(("kpi.", "financial.", "capital.", "cash_flow.")):
        return "financial"
    if artifact_id.startswith(("drivers.", "thesis.", "semantic.")):
        return "thesis"
    if artifact_id.startswith(("expectation.", "forecast.")):
        return "expectation"
    if artifact_id.startswith(("peers.", "valuation.", "decision.")):
        return "valuation"
    if artifact_id.startswith(("monitoring.", "research.readiness")):
        return "monitoring"
    if artifact_id.startswith(("validation.", "evidence.")):
        return "quality"
    return "other"


def _display_title(artifact_id: str) -> str:
    return artifact_id.replace("_", " ").replace(".", " / ")


class ResearchReportComposer:
    """Compose a report document from presentation-safe typed artifacts only."""

    version = "research-report-composer@2.0.0"

    def compose(self, view: HumanReadableResearchView) -> ResearchReportDocument:
        if not isinstance(view, HumanReadableResearchView):
            raise TypeError(
                "ResearchReportComposer.compose requires HumanReadableResearchView"
            )
        grouped: dict[str, list[ReportArtifactBlock]] = defaultdict(list)
        for artifact in view.artifacts:
            grouped[_section_id(artifact.artifact_id)].append(
                ReportArtifactBlock(
                    artifact_id=artifact.artifact_id,
                    title=_display_title(artifact.artifact_id),
                    schema_version=artifact.schema_version,
                    payload=artifact.payload,
                )
            )
        sections = tuple(
            ReportSection(
                section_id=section_id,
                title=title,
                artifacts=tuple(
                    sorted(
                        grouped.get(section_id, ()),
                        key=lambda item: item.artifact_id,
                    )
                ),
            )
            for section_id, title in _SECTION_ORDER
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
