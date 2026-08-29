"""Stable Research OS runtime contracts."""

from .context import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    KnowledgeView,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from .factory import PluginProvider, ResearchRuntime, ResearchRuntimeFactory
from .inputs import ResearchInputs
from .result import ComponentFingerprint, ResearchRunResult

__all__ = [
    "BaselineFingerprint",
    "CompanyRef",
    "ComponentFingerprint",
    "EvidenceView",
    "FactView",
    "KnowledgeView",
    "LegacyEvidenceView",
    "LegacyFactView",
    "PluginProvider",
    "ResearchContext",
    "ResearchInputs",
    "ResearchOptions",
    "ResearchRunResult",
    "ResearchRuntime",
    "ResearchRuntimeFactory",
]
