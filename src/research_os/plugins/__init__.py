"""Versioned Research OS plugin contracts and registry."""

from research_os.contracts.errors import (
    PluginContractError,
    PluginError,
    PluginVersionUnsupportedError,
)

from .discovery import (
    PLUGIN_ENTRY_POINT_GROUP,
    PluginDiscoveryError,
    discover_plugins,
)
from .models import (
    ApplicabilityResult,
    CoverageGap,
    ExtensionRequest,
    PluginManifest,
    ResolvedPlugin,
    SupportAssessment,
)
from .protocols import (
    IndustryPlugin,
    KpiProvider,
    MetricDefinitionRegistry,
    MethodologyPlugin,
    PluginServices,
    ResearchPlugin,
)
from .registry import (
    DuplicatePluginError,
    PluginRegistry,
)

__all__ = [
    "ApplicabilityResult",
    "CoverageGap",
    "DuplicatePluginError",
    "ExtensionRequest",
    "IndustryPlugin",
    "KpiProvider",
    "MetricDefinitionRegistry",
    "MethodologyPlugin",
    "PluginContractError",
    "PluginDiscoveryError",
    "PluginError",
    "PluginManifest",
    "PluginRegistry",
    "PluginServices",
    "PluginVersionUnsupportedError",
    "PLUGIN_ENTRY_POINT_GROUP",
    "ResearchPlugin",
    "ResolvedPlugin",
    "SupportAssessment",
    "discover_plugins",
]
