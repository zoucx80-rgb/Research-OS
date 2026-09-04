"""Stable current Reporting API for Core/Plugin API 2.0."""

from .composer import ResearchReportComposer
from .contributions import ReportContribution, ResearchQuestionSpec
from .fingerprint import semantic_fingerprint
from .formatting import HumanValueFormatter
from .markdown_renderer import MarkdownArtifactRenderer, ResearchReportMarkdownRenderer
from .models import (
    AuditArtifactLineage,
    HumanReadableResearchView,
    MarkdownRenderResult,
    PresentedArtifact,
    ReportArtifactBlock,
    ReportSection,
    ResearchReportDocument,
)
from .projectors import ArtifactProjection, project_artifact
from .research_view import ResearchViewPresenter

__all__ = [
    "AuditArtifactLineage",
    "HumanReadableResearchView",
    "HumanValueFormatter",
    "MarkdownArtifactRenderer",
    "MarkdownRenderResult",
    "PresentedArtifact",
    "ReportArtifactBlock",
    "ReportContribution",
    "ReportSection",
    "ResearchQuestionSpec",
    "ResearchReportComposer",
    "ResearchReportDocument",
    "ResearchReportMarkdownRenderer",
    "ResearchViewPresenter",
    "ArtifactProjection",
    "project_artifact",
    "semantic_fingerprint",
]
