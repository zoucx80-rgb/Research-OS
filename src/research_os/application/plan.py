"""Professional-phase plan compilation for Core API 2.0 research runs."""

from __future__ import annotations

from collections.abc import Iterable

from research_os.application.command import ResearchRunCommand
from research_os.contracts.artifact_values import (
    DecisionStateInput,
    DecisionStateProvenance,
    DecisionStateRecord as DecisionArtifactRecord,
    Thesis,
    ThesisPortfolio,
)
from research_os.contracts.artifacts import ArtifactCatalog, ArtifactSnapshot, ArtifactWrite
from research_os.contracts.errors import PluginError
from research_os.contracts.metrics import MetricSet
from research_os.decision.engine import DecisionEngine
from research_os.decision.models import (
    DecisionContext,
    ExpectationState,
    FundamentalState,
    ValuationState,
)
from research_os.metrics import builtin_metric_registry
from research_os.policies import builtin_policy_registry
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolution
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import (
    BUSINESS_MODEL_PROFILE,
    DECISION_RECORD,
    DECISION_STATE_PROVENANCE,
    KPI_METRICS,
    STRATEGY_RESOLUTION,
    THESIS_PORTFOLIO,
    build_core_artifact_catalog,
)
from research_os.runtime.module_plan import (
    ModulePlan,
    ModulePlanCompilationError,
    ModulePlanCompiler,
)
from research_os.runtime.modules import ModuleResult, ModuleSpec, ModuleStatus, ResearchModule
from research_os.runtime.state import ResearchStateView
from research_os.thesis.portfolio import ThesisPortfolioBuilder


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
            raise ModulePlanCompilationError("professional plan supports one primary KPI provider")
        self._provider = providers[0] if providers else None

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        state.require(STRATEGY_RESOLUTION)
        if self._provider is None:
            metrics = MetricSet()
            status: ModuleStatus = "INSUFFICIENT_EVIDENCE"
            diagnostics: tuple[str, ...] = ("no registered KPI provider for resolved strategy",)
        else:
            metrics = MetricSet(
                metrics=self._provider.calculate(
                    context.facts,
                    builtin_metric_registry().select(self._provider.metric_ids()),
                    builtin_policy_registry().snapshot(),
                )
            )
            status = (
                "PASS"
                if any(item.status == "valid" for item in metrics.metrics)
                else "INSUFFICIENT_EVIDENCE"
            )
            diagnostics = () if status == "PASS" else ("KPI provider produced no valid metrics",)
        evidence_refs = tuple(
            reference for metric in metrics.metrics for reference in metric.evidence_refs
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


class ThesisPortfolioModule:
    spec = ModuleSpec(
        module_id="core:thesis-portfolio",
        module_version="2.0.0",
        requires=frozenset(),
        provides=frozenset((THESIS_PORTFOLIO,)),
        required_for_completion=False,
    )

    def __init__(self, theses: tuple[Thesis, ...]) -> None:
        self._theses = theses
        self._builder = ThesisPortfolioBuilder()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        del context, state
        portfolio: ThesisPortfolio = self._builder.build(self._theses)
        return ModuleResult(
            module_id=self.spec.module_id,
            status=("PASS" if portfolio.primary is not None else "INSUFFICIENT_EVIDENCE"),
            writes=(
                ArtifactWrite(
                    key=THESIS_PORTFOLIO,
                    value=portfolio,
                    producer_id=self.spec.module_id,
                    evidence_refs=portfolio.evidence_refs,
                ),
            ),
        )


class PortfolioDecisionModule:
    spec = ModuleSpec(
        module_id="core:portfolio-decision",
        module_version="2.0.0",
        requires=frozenset((THESIS_PORTFOLIO,)),
        provides=frozenset((DECISION_RECORD, DECISION_STATE_PROVENANCE)),
        required_for_completion=False,
    )

    def __init__(
        self,
        *,
        fundamental_state: FundamentalState = "UNCERTAIN",
        valuation_state: ValuationState = "UNRELIABLE",
        expectation_state: ExpectationState = "UNKNOWN",
        evidence_confidence: float | None = None,
        claim_ids: tuple[str, ...] = (),
        material_funding_risk: bool = False,
    ) -> None:
        self._fundamental_state = fundamental_state
        self._valuation_state = valuation_state
        self._expectation_state = expectation_state
        self._evidence_confidence = evidence_confidence
        self._claim_ids = claim_ids
        self._material_funding_risk = material_funding_risk
        self._engine = DecisionEngine()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        portfolio = state.require(THESIS_PORTFOLIO)
        decision = self._engine.evaluate(
            DecisionContext(
                company_id=context.company.company_id,
                fundamental_state=self._fundamental_state,
                valuation_state=self._valuation_state,
                expectation_state=self._expectation_state,
                thesis_portfolio=portfolio,
                evidence_confidence=(
                    self._evidence_confidence
                    if self._evidence_confidence is not None
                    else (portfolio.primary.confidence or 0)
                    if portfolio.primary is not None
                    else 0
                ),
                claim_ids=self._claim_ids,
                decision_ts=context.decision_ts,
                material_funding_risk=self._material_funding_risk,
            )
        )
        record = DecisionArtifactRecord(
            domain_status=(
                "INSUFFICIENT_EVIDENCE"
                if decision.state == "INSUFFICIENT_EVIDENCE"
                else "SUPPORTED"
            ),
            company_id=decision.company_id,
            state=decision.state,
            decision_ts=decision.decision_ts,
            thesis_keys=decision.used_thesis_ids,
            claim_keys=decision.used_claim_ids,
            reason_codes=decision.reason_codes,
            evidence_refs=decision.evidence_refs,
        )
        provenance = DecisionStateProvenance(
            domain_status=record.domain_status,
            inputs=(
                DecisionStateInput(
                    dimension="thesis_portfolio",
                    state=decision.thesis_state or "UNRESOLVED",
                    thesis_keys=decision.used_thesis_ids,
                    claim_keys=decision.used_claim_ids,
                    evidence_refs=decision.evidence_refs,
                ),
            ),
            evidence_refs=decision.evidence_refs,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=(
                "INSUFFICIENT_EVIDENCE" if decision.state == "INSUFFICIENT_EVIDENCE" else "PASS"
            ),
            writes=(
                ArtifactWrite(
                    key=DECISION_RECORD,
                    value=record,
                    producer_id=self.spec.module_id,
                    evidence_refs=decision.evidence_refs,
                ),
                ArtifactWrite(
                    key=DECISION_STATE_PROVENANCE,
                    value=provenance,
                    producer_id=self.spec.module_id,
                    evidence_refs=decision.evidence_refs,
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
            ThesisPortfolioModule(command.thesis.prior_theses),
            PortfolioDecisionModule(),
            *self._downstream_modules,
        )
        return ModulePlanCompiler(self.catalog).compile(
            modules,
            initial_snapshot=bootstrap,
        )
