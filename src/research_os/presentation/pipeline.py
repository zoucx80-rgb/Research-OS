from __future__ import annotations

from typing import Protocol, Self

from pydantic import BaseModel, ConfigDict, model_validator

from research_os.presentation.artifacts import (
    HtmlPresentationArtifact,
    MarkdownPresentationArtifact,
    PdfPresentationArtifact,
)
from research_os.presentation.html_renderer import ProfessionalHtmlRenderer
from research_os.presentation.markdown_artifact_renderer import MarkdownArtifactRenderer
from research_os.presentation.pdf_adapter import PlaywrightPdfAdapter
from research_os.reporting import ResearchReportDocument


class PdfArtifactRenderer(Protocol):
    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact: ...


class PresentationBundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    markdown: MarkdownPresentationArtifact
    html: HtmlPresentationArtifact
    pdf: PdfPresentationArtifact

    @model_validator(mode="after")
    def _validate_hash_chain(self) -> Self:
        if self.html.source_hash != self.markdown.content_hash:
            raise ValueError("HTML artifact is not derived from the bundled Markdown")
        if self.pdf.source_hash != self.html.content_hash:
            raise ValueError("PDF artifact is not derived from the bundled HTML")
        return self


class ProfessionalPresentationPipeline:
    """Execute the only permitted Document -> Markdown -> HTML -> PDF chain."""

    def __init__(
        self,
        *,
        markdown_renderer: MarkdownArtifactRenderer | None = None,
        html_renderer: ProfessionalHtmlRenderer | None = None,
        pdf_adapter: PdfArtifactRenderer | None = None,
    ) -> None:
        self._markdown_renderer = markdown_renderer or MarkdownArtifactRenderer()
        self._html_renderer = html_renderer or ProfessionalHtmlRenderer()
        self._pdf_adapter = pdf_adapter or PlaywrightPdfAdapter()

    def render(self, document: ResearchReportDocument) -> PresentationBundle:
        if not isinstance(document, ResearchReportDocument):
            raise TypeError(
                "ProfessionalPresentationPipeline.render requires ResearchReportDocument"
            )
        markdown = self._markdown_renderer.render(document)
        html = self._html_renderer.render(markdown)
        pdf = self._pdf_adapter.render(html)
        return PresentationBundle(markdown=markdown, html=html, pdf=pdf)
