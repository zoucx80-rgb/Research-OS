from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from research_os.plugins.models import ApplicabilityResult, PluginManifest
from research_os.runtime.context import ResearchContext
from research_os.runtime.modules import ResearchModule
from research_os.runtime.state import ResearchStateView

if TYPE_CHECKING:
    from research_os.reporting.contributions import ReportContribution


@runtime_checkable
class IndustryStrategyPack(Protocol):
    manifest: PluginManifest

    def applicability(self, context: ResearchContext) -> ApplicabilityResult: ...
    def modules(self) -> list[ResearchModule]: ...
    def report_contributions(self) -> list["ReportContribution"]: ...


@runtime_checkable
class MethodologyPack(Protocol):
    manifest: PluginManifest

    def supports(self, context: ResearchContext, state: ResearchStateView) -> bool: ...
    def modules(self) -> list[ResearchModule]: ...


ResearchPlugin = IndustryStrategyPack | MethodologyPack
