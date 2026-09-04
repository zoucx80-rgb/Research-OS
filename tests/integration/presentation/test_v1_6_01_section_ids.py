from datetime import datetime, timezone

from research_os.presentation.artifacts import (
    MarkdownPresentationArtifact,
    canonical_document_hash,
)
from research_os.presentation.html_renderer import ProfessionalHtmlRenderer
from research_os.reporting import ResearchReportDocument


def _markdown(content: str) -> MarkdownPresentationArtifact:
    document = ResearchReportDocument(
        company_id="synthetic:section-id",
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        research_os_version="1.6.01",
        core_api_version="2.0",
        plugin_api_version="2.0",
        snapshot_schema_version="2.0",
        execution_completion="COMPLETE",
        research_readiness="READY",
        semantic_fingerprint="a" * 64,
    )
    assert canonical_document_hash(document)
    return MarkdownPresentationArtifact.from_document(
        document=document,
        renderer_version="test@1",
        content=content,
    )


def test_html_layout_routes_by_stable_section_id_not_localized_title() -> None:
    artifact = _markdown(
        "# Report\n\n<!-- section-id:decision -->\n## 任意本地化标题\n\n- 状态：风险审查\n"
    )
    html = ProfessionalHtmlRenderer().render(artifact).content

    assert '<section id="decision"' in html
    assert "decision-snapshot" in html
    assert "report-section-1" not in html
