from __future__ import annotations

import importlib

import pytest

from research_os.presentation import canonical_document_hash
from research_os.reporting import (
    AuditAppendix,
    InvestmentDecisionSnapshot,
    ResearchReportDocument,
    SemanticValue,
)
from research_os.reporting.markdown_renderer import (
    ResearchReportMarkdownRenderer as LegacyMarkdownRenderer,
)


def _renderer_cls():
    presentation = importlib.import_module("research_os.presentation")
    assert hasattr(presentation, "MarkdownArtifactRenderer"), (
        "v1.5.08 requires MarkdownArtifactRenderer"
    )
    return presentation.MarkdownArtifactRenderer


def _renderer():
    return _renderer_cls()(renderer=LegacyMarkdownRenderer())


def _semantic(code: str, label: str) -> SemanticValue:
    return SemanticValue(code=code, label=label, explanation=label)


def _document() -> ResearchReportDocument:
    return ResearchReportDocument(
        metadata={"company_id": "synthetic:markdown-artifact"},
        decision_snapshot=InvestmentDecisionSnapshot(
            company_id="synthetic:markdown-artifact",
            decision_ts="2026-08-30T00:00:00Z",
            business_model=_semantic("distributor", "分销业务"),
            decision_state=_semantic("WAIT_FOR_CONFIRMATION", "等待进一步确认"),
            fundamental_state=_semantic("MIXED", "基本面信号混合"),
            thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
            expectation_state=_semantic("MISSING", "市场预期缺失"),
            valuation_state=_semantic("MISSING", "估值缺失"),
            primary_thesis="营运资金现金转化仍待验证。",
            evidence_confidence=0.6,
        ),
        audit_appendix=AuditAppendix(
            repository="zoucx80-rgb/Research-OS",
            repository_commit="eebeb35595d8260d45ea561e970bbe13464d90e5",
            research_os_version="1.5.7",
            core_api_version="1.0",
            presentation_version="professional-research-view@1.3.0",
        ),
    )


def test_markdown_artifact_preserves_exact_existing_renderer_bytes_and_version():
    renderer = _renderer()
    document = _document()
    expected = LegacyMarkdownRenderer().render(document)

    artifact = renderer.render(document)

    assert artifact.content == expected
    assert artifact.renderer_version == "professional-markdown-renderer@1.0.0"
    assert renderer.version == LegacyMarkdownRenderer.version


def test_markdown_artifact_links_to_canonical_document_hash():
    document = _document()

    artifact = _renderer().render(document)

    assert artifact.source_hash == canonical_document_hash(document)


@pytest.mark.parametrize("invalid", [{}, "markdown", object()])
def test_markdown_artifact_renderer_rejects_non_document_inputs(invalid):
    with pytest.raises(TypeError, match="ResearchReportDocument"):
        _renderer().render(invalid)
