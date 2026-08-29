"""Versioned Research OS plugin contracts and registry."""

from .models import (
    ApplicabilityResult,
    CoverageGap,
    ExtensionRequest,
    PluginManifest,
    ResolvedPlugin,
)
from .protocols import IndustryStrategyPack, MethodologyPack, ResearchPlugin
from .registry import DuplicatePluginError, PluginCompatibilityError, PluginRegistry

__all__ = [
    "ApplicabilityResult",
    "CoverageGap",
    "DuplicatePluginError",
    "ExtensionRequest",
    "IndustryStrategyPack",
    "MethodologyPack",
    "PluginCompatibilityError",
    "PluginManifest",
    "PluginRegistry",
    "ResearchPlugin",
    "ResolvedPlugin",
]
