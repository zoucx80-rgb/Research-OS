"""Professional-phase plan compilation for Core API 2.0 research runs."""

from __future__ import annotations

from collections.abc import Iterable

from research_os.application.command import ResearchRunCommand
from research_os.contracts.artifacts import ArtifactCatalog, ArtifactSnapshot, ArtifactWrite
from research_os.contracts.errors import PluginError
from research_os.contracts.metrics import MetricDefinition, MetricSet
from research_os.contracts.policies import PolicySnapshot
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolution
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import (
    BUSINESS_MODEL_PROFILE,
    KPI_METRICS,
    STRATEGY_RESOLUTION,
    build_core_artifact_catalog,
)
from research_os.runtime.module_plan import (
    ModulePlan,
    ModulePlanCompilationError,
    ModulePlanCompiler,
)
from research_os.runtime.modules import ModuleResult, ModuleSpec, ModuleStatus, ResearchModule
from research_os.runtime.state import ResearchStateView


class ResolvedStrategyModule:
    """Write the precomputed strategy as an Engine-owned typed artifact."""

    spec = ModuleSpec(
        module_id="core:resolved-strategy",
        module_version="2.0.0",
        requires=frozenset((BUSINESS_MODEL_PROFILE,)),
        provides=frozenset((STRATEGY_RESOLUTION,)),
    )

    def __init__(self, strategy: StrategyResolution) -> None:
        self._strategy = strategy

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        state.require(BUSINESS_MODEL_PROFILE)
        covered = bool(self._strategy.industry_plugins)
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS" if covered else "INSUFFICIENT_EVIDENCE",
            diagnostics=() if covered else ("no industry plugin coverage",),
            writes=(
                ArtifactWrite(
                    key=STRATEGY_RESOLUTION,
                    value=self._strategy,
                    producer_id=self.spec.module_id,
                    evidence_refs=self._strategy.evidence_refs,
                ),
            ),
        )


class _MetricDefinitions:
    def __init__(self, metric_ids: frozenset[str]) -> None:
        self._definitions = {
            metric_id: MetricDefinition(
                metric_id=metric_id,
                definition_version="2.0.0",
                output_kind="ratio",
                output_unit="provider-defined",
            )
            for metric_id in metric_ids
        }

    def get(self, metric_id: str) -> MetricDefinition | None:
        return self._definitions.get(metric_id)


class KpiProviderModule:
    spec = ModuleSpec(
        module_id="core:kpi-provider",
        module_version="2.0.0",
        requires=frozenset((STRATEGY_RESOLUTION,)),
        provides=frozenset((KPI_METRICS,)),
    )

    def __init__(self, strategy: StrategyResolution, registry: PluginRegistry) -> None:
        providers = []
        resolved_plugins = (*strategy.industry_plugins, *strategy.methodology_plugins)
        for resolved in resolved_plugins:
            try:
                registered = registry.require(resolved.plugin_id)
            except PluginError as exc:
                raise ModulePlanCompilationError(
                    f"resolved plugin is not registered: {resolved.plugin_id}",
                    context={"plugin_id": resolved.plugin_id},
                ) from exc
            manifest = registered.manifest
            resolved_identity = (
                resolved.plugin_type,
                resolved.plugin_version,
                resolved.plugin_api_version,
            )
            registered_identity = (
                manifest.plugin_type,
                manifest.plugin_version,
                manifest.plugin_api_version,
            )
            if resolved_identity != registered_identity:
                raise ModulePlanCompilationError(
                    f"resolved plugin identity does not match registry: {resolved.plugin_id}",
                    context={"plugin_id": resolved.plugin_id},
                )
            services = registry.services(resolved.plugin_id)
            if services is None:
                raise ModulePlanCompilationError(
                    f"resolved plugin services are not registered: {resolved.plugin_id}",
                    context={"plugin_id": resolved.plugin_id},
                )
            if services.kpi_provider is not None:
                providers.append(services.kpi_provider)
        if len(providers) > 1:
            raise ModulePlanCompilationError(
                "professional plan supports one primary KPI provider"
            )
        self._provider = providers[0] if providers else None

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        state.require(STRATEGY_RESOLUTION)
        if self._provider is None:
            metrics = MetricSet()
            status: ModuleStatus = "INSUFFICIENT_EVIDENCE"
            diagnostics: tuple[str, ...] = (
                "no registered KPI provider for resolved strategy",
            )
        else:
            metrics = MetricSet(
                metrics=self._provider.calculate(
                    context.facts,
                    _MetricDefinitions(self._provider.metric_ids()),
                    PolicySnapshot(),
                )
            )
            status = (
                "PASS"
                if any(item.status == "valid" for item in metrics.metrics)
                else "INSUFFICIENT_EVIDENCE"
            )
            diagnostics = () if status == "PASS" else ("KPI provider produced no valid metrics",)
        evidence_refs = tuple(
            reference
            for metric in metrics.metrics
            for reference in metric.evidence_refs
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            diagnostics=diagnostics,
            writes=(
                ArtifactWrite(
                    key=KPI_METRICS,
                    value=metrics,
                    producer_id=self.spec.module_id,
                    evidence_refs=evidence_refs,
                ),
            ),
        )


class ResearchPlanCompiler:
    """Compile Phase B against the immutable ArtifactSnapshot from Bootstrap."""

    def __init__(
        self,
        catalog: ArtifactCatalog | None = None,
        *,
        registry: PluginRegistry | None = None,
        downstream_modules: Iterable[ResearchModule] = (),
    ) -> None:
        self.catalog = catalog or build_core_artifact_catalog()
        self._registry = registry or PluginRegistry(
            core_api_version="2.0",
            research_os_version="1.6.0",
        )
        self._downstream_modules = tuple(downstream_modules)

    def compile(
        self,
        command: ResearchRunCommand,
        bootstrap: ArtifactSnapshot,
        strategy: StrategyResolution,
    ) -> ModulePlan:
        modules: tuple[ResearchModule, ...] = (
            ResolvedStrategyModule(strategy),
            KpiProviderModule(strategy, self._registry),
            *self._downstream_modules,
        )
        return ModulePlanCompiler(self.catalog).compile(
            modules,
            initial_snapshot=bootstrap,
        )
