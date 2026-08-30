from __future__ import annotations

from research_os.presentation.artifacts import MarkdownPresentationArtifact
from research_os.reporting import ResearchReportDocument, ResearchReportMarkdownRenderer


class MarkdownArtifactRenderer:
    """Attach deterministic provenance to the existing Markdown renderer output."""

    version = ResearchReportMarkdownRenderer.version

    def __init__(self, renderer: ResearchReportMarkdownRenderer | None = None) -> None:
        self._renderer = renderer or ResearchReportMarkdownRenderer()

    def render(self, document: ResearchReportDocument) -> MarkdownPresentationArtifact:
        if not isinstance(document, ResearchReportDocument):
            raise TypeError("MarkdownArtifactRenderer.render requires ResearchReportDocument")
        content = self._renderer.render(document)
        return MarkdownPresentationArtifact.from_document(
            document=document,
            renderer_version=self.version,
            content=content,
        )
