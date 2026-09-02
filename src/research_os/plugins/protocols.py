from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from research_os.contracts.metrics import MetricDefinition, MetricResult
from research_os.contracts.policies import PolicySnapshot
from research_os.plugins.models import (
    ApplicabilityResult,
    PluginManifest,
    SupportAssessment,
)
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import FactView, ResearchContext

if TYPE_CHECKING:
    from research_os.reporting.contributions import ReportContribution


@runtime_checkable
class MetricDefinitionRegistry(Protocol):
    def get(self, metric_id: str) -> MetricDefinition | None: ...


@runtime_checkable
class KpiProvider(Protocol):
    provider_id: str
    provider_version: str

    def metric_ids(self) -> frozenset[str]: ...

    def calculate(
        self,
        facts: FactView,
        definitions: MetricDefinitionRegistry,
        policy: PolicySnapshot,
    ) -> tuple[MetricResult, ...]: ...


@dataclass(frozen=True, slots=True)
class PluginServices:
    kpi_provider: KpiProvider | None = None
    valuation_methods: tuple[Any, ...] = ()
    forecast_methods: tuple[Any, ...] = ()
    policy_contributions: tuple[Any, ...] = ()
    report_contributions: tuple["ReportContribution", ...] = ()


@runtime_checkable
class IndustryPlugin(Protocol):
    manifest: PluginManifest

    def applicability(
        self,
        context: ResearchContext,
        business_model: BusinessModelProfile,
    ) -> ApplicabilityResult: ...

    def services(self) -> PluginServices: ...


@runtime_checkable
class MethodologyPlugin(Protocol):
    manifest: PluginManifest

    def supports(
        self,
        context: ResearchContext,
        available_capabilities: frozenset[str],
    ) -> SupportAssessment: ...

    def services(self) -> PluginServices: ...


ResearchPlugin = IndustryPlugin | MethodologyPlugin
