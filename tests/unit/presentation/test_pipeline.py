from __future__ import annotations

import importlib

import pytest

from research_os.presentation import HtmlPresentationArtifact, PdfPresentationArtifact
from research_os.reporting import (
    AuditAppendix,
    InvestmentDecisionSnapshot,
    ResearchReportDocument,
    SemanticValue,
)


def _pipeline_cls():
    presentation = importlib.import_module("research_os.presentation")
    assert hasattr(presentation, "ProfessionalPresentationPipeline"), (
        "v1.5.08 requires ProfessionalPresentationPipeline"
    )
    return presentation.ProfessionalPresentationPipeline


def _semantic(code: str, label: str) -> SemanticValue:
    return SemanticValue(code=code, label=label, explanation=label)


def _document() -> ResearchReportDocument:
    return ResearchReportDocument(
        decision_snapshot=InvestmentDecisionSnapshot(
            company_id="synthetic:pipeline",
            decision_ts="2026-08-30T00:00:00Z",
            business_model=_semantic("manufacturing", "制造业"),
            decision_state=_semantic("WAIT_FOR_CONFIRMATION", "等待进一步确认"),
            fundamental_state=_semantic("MIXED", "基本面信号混合"),
            thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
            expectation_state=_semantic("MISSING", "市场预期缺失"),
            valuation_state=_semantic("MISSING", "估值缺失"),
            primary_thesis="增长质量取决于现金回报。",
            evidence_confidence=0.5,
        ),
        audit_appendix=AuditAppendix(
            repository="zoucx80-rgb/Research-OS",
            repository_commit="eebeb35595d8260d45ea561e970bbe13464d90e5",
            research_os_version="1.5.7",
            core_api_version="1.0",
            presentation_version="professional-research-view@1.3.0",
        ),
    )


class _DeterministicPdfAdapter:
    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact:
        return PdfPresentationArtifact.from_html(
            html=html,
            renderer_version="professional-pdf-adapter@1.0.0",
            backend_version="test-backend@1.0",
            content=b"%PDF-1.7\ntyped-pipeline",
        )


def test_pipeline_produces_an_unbroken_document_markdown_html_pdf_hash_chain():
    bundle = _pipeline_cls()(pdf_adapter=_DeterministicPdfAdapter()).render(
        _document()
    )

    assert bundle.html.source_hash == bundle.markdown.content_hash
    assert bundle.pdf.source_hash == bundle.html.content_hash
    assert bundle.markdown.content.startswith("# 投资研究报告")
    assert bundle.html.content.startswith("<!doctype html>")
    assert bundle.pdf.content.startswith(b"%PDF-")


@pytest.mark.parametrize("invalid", [{}, "report", object()])
def test_pipeline_rejects_non_document_inputs_before_any_renderer_runs(invalid):
    with pytest.raises(TypeError, match="ResearchReportDocument"):
        _pipeline_cls()(pdf_adapter=_DeterministicPdfAdapter()).render(invalid)
