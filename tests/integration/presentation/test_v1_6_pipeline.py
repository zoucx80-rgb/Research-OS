from __future__ import annotations

from datetime import datetime, timezone

from research_os.presentation import ProfessionalPresentationPipeline, canonical_document_hash
from research_os.reporting import (
    AuditArtifactLineage,
    ReportArtifactBlock,
    ReportSection,
    ResearchReportDocument,
)


def _document() -> ResearchReportDocument:
    return ResearchReportDocument(
        company_id="synthetic:m4-presentation",
        decision_ts=datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc),
        research_os_version="1.6.0",
        core_api_version="2.0",
        plugin_api_version="2.0",
        snapshot_schema_version="2.0",
        execution_completion="COMPLETE",
        research_readiness="READY",
        semantic_fingerprint="a" * 64,
        sections=(
            ReportSection(
                section_id="thesis",
                title="驱动、投资逻辑与反证",
                artifacts=(
                    ReportArtifactBlock(
                        artifact_id="thesis.portfolio",
                        title="thesis / portfolio",
                        schema_version="2.0",
                        payload={
                            "domain_status": "SUPPORTED",
                            "primary": {
                                "title": "需求与盈利能力验证",
                                "statement": "仅展示已冻结的类型化研究结论",
                            },
                        },
                    ),
                ),
            ),
        ),
        audit_appendix=(
            AuditArtifactLineage(
                artifact_id="thesis.portfolio",
                schema_version="2.0",
                type_id="ThesisPortfolio",
                producer_ids=("core:thesis",),
                value_fingerprint="b" * 64,
            ),
        ),
    )


def test_current_document_markdown_html_pdf_hash_chain_is_auditable() -> None:
    document = _document()

    bundle = ProfessionalPresentationPipeline().render(document)

    assert bundle.markdown.source_hash == canonical_document_hash(document)
    assert bundle.html.source_hash == bundle.markdown.content_hash
    assert bundle.pdf.source_hash == bundle.html.content_hash
    assert bundle.pdf.content.startswith(b"%PDF-")
    assert "驱动、投资逻辑与反证" in bundle.markdown.content
    assert "synthetic:m4-presentation" in bundle.markdown.content
    assert "aaaaaaaaaaaaaaaa" in bundle.markdown.content
    assert "驱动、投资逻辑与反证" in bundle.html.content


def test_presentation_pipeline_does_not_recalculate_research_semantics() -> None:
    document = _document()
    changed_display = document.model_copy(
        update={
            "sections": (
                ReportSection(
                    section_id="thesis",
                    title="展示标题变化",
                    artifacts=document.sections[0].artifacts,
                ),
            )
        }
    )

    original = ProfessionalPresentationPipeline().render(document)
    changed = ProfessionalPresentationPipeline().render(changed_display)

    assert document.semantic_fingerprint == changed_display.semantic_fingerprint
    assert original.markdown.content_hash != changed.markdown.content_hash
    assert original.pdf.content_hash != changed.pdf.content_hash
