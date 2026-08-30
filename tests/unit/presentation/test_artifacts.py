from __future__ import annotations

from hashlib import sha256
import importlib
import importlib.util

import pytest
from pydantic import ValidationError

from research_os.reporting import (
    AuditAppendix,
    InvestmentDecisionSnapshot,
    ResearchReportDocument,
    SemanticValue,
)


def _presentation_api():
    assert importlib.util.find_spec("research_os.presentation") is not None, (
        "v1.5.08 requires the public research_os.presentation package"
    )
    module = importlib.import_module("research_os.presentation")
    required = (
        "HtmlPresentationArtifact",
        "MarkdownPresentationArtifact",
        "PdfPresentationArtifact",
        "canonical_document_hash",
    )
    assert all(hasattr(module, name) for name in required), (
        "v1.5.08 requires typed Markdown/HTML/PDF presentation artifacts"
    )
    return module


def _semantic(code: str, label: str) -> SemanticValue:
    return SemanticValue(code=code, label=label, explanation=label)


def _document() -> ResearchReportDocument:
    return ResearchReportDocument(
        metadata={"company_id": "synthetic:artifact", "locale": "zh-CN"},
        decision_snapshot=InvestmentDecisionSnapshot(
            company_id="synthetic:artifact",
            decision_ts="2026-08-30T00:00:00Z",
            business_model=_semantic("manufacturing", "制造业"),
            decision_state=_semantic("WAIT_FOR_CONFIRMATION", "等待进一步确认"),
            fundamental_state=_semantic("MIXED", "基本面信号混合"),
            thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
            expectation_state=_semantic("INSUFFICIENT", "市场预期证据不足"),
            valuation_state=_semantic("MISSING", "估值缺失"),
            primary_thesis="现金回报仍待验证。",
            evidence_confidence=0.7,
        ),
        audit_appendix=AuditAppendix(
            repository="zoucx80-rgb/Research-OS",
            repository_commit="eebeb35595d8260d45ea561e970bbe13464d90e5",
            research_os_version="1.5.7",
            core_api_version="1.0",
            presentation_version="professional-research-view@1.3.0",
        ),
    )


def test_canonical_document_hash_is_stable_for_equivalent_documents():
    api = _presentation_api()
    first = _document()
    reordered = first.model_dump(mode="json")
    reordered["metadata"] = {"locale": "zh-CN", "company_id": "synthetic:artifact"}
    second = ResearchReportDocument.model_validate(reordered)

    assert api.canonical_document_hash(first) == api.canonical_document_hash(second)


def test_canonical_document_hash_rejects_non_finite_numbers():
    api = _presentation_api()
    document = _document().model_copy(
        update={"metadata": {"company_id": "synthetic:artifact", "invalid": float("nan")}}
    )

    with pytest.raises(ValueError, match="non-finite"):
        api.canonical_document_hash(document)


def test_markdown_artifact_hashes_exact_document_and_utf8_content():
    api = _presentation_api()
    content = "# 投资研究报告\n"

    artifact = api.MarkdownPresentationArtifact.from_document(
        document=_document(),
        renderer_version="professional-markdown-renderer@1.0.0",
        content=content,
    )

    assert artifact.source_hash == api.canonical_document_hash(_document())
    assert artifact.content_hash == sha256(content.encode("utf-8")).hexdigest()
    assert artifact.media_type == "text/markdown; charset=utf-8"


def test_html_and_pdf_artifacts_form_an_exact_upstream_hash_chain():
    api = _presentation_api()
    markdown = api.MarkdownPresentationArtifact.from_document(
        document=_document(),
        renderer_version="professional-markdown-renderer@1.0.0",
        content="# 报告\n",
    )
    css = "@page { size: A4; }"
    html_content = f'<!doctype html><html lang="zh-CN"><style>{css}</style></html>'

    html = api.HtmlPresentationArtifact.from_markdown(
        markdown=markdown,
        renderer_version="professional-html-renderer@1.0.0",
        style=css,
        content=html_content,
    )
    pdf = api.PdfPresentationArtifact.from_html(
        html=html,
        renderer_version="professional-pdf-adapter@1.0.0",
        backend_version="playwright@1.62.0/chromium@140.0",
        content=b"%PDF-1.7\nsynthetic",
    )

    assert html.source_hash == markdown.content_hash
    assert html.style_hash == sha256(css.encode("utf-8")).hexdigest()
    assert html.content_hash == sha256(html_content.encode("utf-8")).hexdigest()
    assert pdf.source_hash == html.content_hash
    assert pdf.content_hash == sha256(pdf.content).hexdigest()


def test_artifacts_reject_invalid_hashes_and_content_hash_mismatches():
    api = _presentation_api()
    markdown = api.MarkdownPresentationArtifact.from_document(
        document=_document(),
        renderer_version="professional-markdown-renderer@1.0.0",
        content="# 报告\n",
    )

    with pytest.raises(ValidationError):
        api.MarkdownPresentationArtifact(
            source_hash="not-a-sha",
            content_hash=markdown.content_hash,
            renderer_version=markdown.renderer_version,
            content=markdown.content,
        )
    with pytest.raises(ValidationError):
        api.MarkdownPresentationArtifact(
            source_hash=markdown.source_hash,
            content_hash="0" * 64,
            renderer_version=markdown.renderer_version,
            content=markdown.content,
        )


def test_artifacts_are_immutable():
    api = _presentation_api()
    artifact = api.MarkdownPresentationArtifact.from_document(
        document=_document(),
        renderer_version="professional-markdown-renderer@1.0.0",
        content="# 报告\n",
    )

    with pytest.raises(ValidationError):
        artifact.content = "changed"


def test_artifact_model_copy_revalidates_hashes():
    api = _presentation_api()
    artifact = api.MarkdownPresentationArtifact.from_document(
        document=_document(),
        renderer_version="professional-markdown-renderer@1.0.0",
        content="# 报告\n",
    )

    with pytest.raises(ValidationError, match="content_hash"):
        artifact.model_copy(update={"content": "tampered"})


def test_html_artifact_requires_the_exact_hashed_style_to_be_embedded_once():
    api = _presentation_api()
    markdown = api.MarkdownPresentationArtifact.from_document(
        document=_document(),
        renderer_version="professional-markdown-renderer@1.0.0",
        content="# 报告\n",
    )
    css = "@page { size: A4; }"

    with pytest.raises(ValidationError, match="style_hash"):
        api.HtmlPresentationArtifact.from_markdown(
            markdown=markdown,
            renderer_version="professional-html-renderer@1.0.0",
            style=css,
            content="<!doctype html><html><style>different</style></html>",
        )

    with pytest.raises(ValidationError, match="exactly one"):
        api.HtmlPresentationArtifact.from_markdown(
            markdown=markdown,
            renderer_version="professional-html-renderer@1.0.0",
            style=css,
            content=f"<style>{css}</style><style>{css}</style>",
        )
