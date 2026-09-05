"""Professional-phase plan compilation for Core API 2.0 research runs."""

from __future__ import annotations

from collections.abc import Iterable

from research_os.application.command import ResearchRunCommand
from research_os.application.professional_modules import (
    CapitalResearchModule,
    DriverSemanticResearchModule,
    ExpectationResearchModule,
    FinancialResearchModule,
    ForecastResearchModule,
    MethodologyDisclosureModule,
    MonitoringResearchModule,
    PeerResearchModule,
    ResearchSufficiencyModule,
    SensitivityResearchModule,
    ValuationResearchModule,
)
from research_os.contracts.artifact_values import (
    DecisionStateInput,
    DecisionStateProvenance,
    DecisionStateRecord as DecisionArtifactRecord,
    ExpectationGap,
    FundingLoop,
    SemanticSignalAssessment,
    Thesis,
    ThesisPortfolio,
    ValuationReconciliation,
)
from research_os.contracts.artifacts import ArtifactCatalog, ArtifactSnapshot, ArtifactWrite
from research_os.contracts.errors import PluginError
from research_os.contracts.metrics import MetricSet
from research_os.decision.context import DecisionContextBuilder
from research_os.decision.engine import DecisionEngine
from research_os.decision.models import (
    ExpectationState,
    FundamentalState,
    ValuationState,
)
from research_os.metrics import builtin_metric_registry
from research_os.forecasting.benchmarks import builtin_benchmark_registry
from research_os.policies import builtin_policy_registry
from research_os.valuation.registry import builtin_valuation_method_registry
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolution
from research_os.version import RESEARCH_OS_VERSION
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import (
    BUSINESS_MODEL_PROFILE,
    CAPITAL_FUNDING_LOOP,
    CAPITAL_EFFICIENCY,
    DECISION_DERIVATION,
    DECISION_INPUT_ASSESSMENT,
    DECISION_RECORD,
    DECISION_STATE_PROVENANCE,
    EXPECTATION_GAP,
    FINANCIAL_TEMPORAL_ANALYSIS,
    FORECAST_BENCHMARK_EVIDENCE,
    KPI_METRICS,
    RESEARCH_SUFFICIENCY,
    SCENARIO_SENSITIVITIES,
    SEMANTIC_CLAIMS,
    STRATEGY_RESOLUTION,
    THESIS_PORTFOLIO,
    THESIS_SEMANTIC_SIGNAL_ASSESSMENT,
    VALUATION_RECONCILIATION,
    VALUATION_MARKET_GAP,
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
        module_version="2.0.1",
        requires=frozenset(
            (
                THESIS_PORTFOLIO,
                FINANCIAL_TEMPORAL_ANALYSIS,
                CAPITAL_EFFICIENCY,
                CAPITAL_FUNDING_LOOP,
                EXPECTATION_GAP,
                VALUATION_RECONCILIATION,
                VALUATION_MARKET_GAP,
                FORECAST_BENCHMARK_EVIDENCE,
                SCENARIO_SENSITIVITIES,
                THESIS_SEMANTIC_SIGNAL_ASSESSMENT,
                SEMANTIC_CLAIMS,
                RESEARCH_SUFFICIENCY,
            )
        ),
        provides=frozenset(
            (
                DECISION_RECORD,
                DECISION_STATE_PROVENANCE,
                DECISION_INPUT_ASSESSMENT,
                DECISION_DERIVATION,
            )
        ),
        required_for_completion=False,
    )

    def __init__(
        self,
        *,
        fundamental_state: FundamentalState | None = None,
        valuation_state: ValuationState | None = None,
        expectation_state: ExpectationState | None = None,
        evidence_confidence: float | None = None,
        claim_ids: tuple[str, ...] | None = None,
        material_funding_risk: bool | None = None,
    ) -> None:
        # Explicit values remain useful for direct module tests; the canonical
        # application path passes none and derives every state from artifacts.
        self._fundamental_override = fundamental_state
        self._valuation_override = valuation_state
        self._expectation_override = expectation_state
        self._evidence_confidence_override = evidence_confidence
        self._claim_ids_override = claim_ids
        self._funding_override = material_funding_risk
        self._engine = DecisionEngine()
        self._context_builder = DecisionContextBuilder()

    @staticmethod
    def _fundamental_state(
        funding: FundingLoop, semantic: SemanticSignalAssessment
    ) -> FundamentalState:
        if (
            funding.funding_state in {"stressed", "debt_funded"}
            and "NEGATIVE_OCF" in funding.reason_codes
        ):
            return "DETERIORATING"
        cycle = next(
            (item for item in semantic.signals if item.metric_id == "cycle_recovery"),
            None,
        )
        if cycle is not None and cycle.direction == "POSITIVE":
            return "IMPROVING"
        if funding.funding_state in {"self_funded", "mixed"}:
            return "STABLE"
        return "UNCERTAIN"

    @staticmethod
    def _valuation_state(reconciliation: ValuationReconciliation) -> ValuationState:
        # Reconciliation proves model consistency, not cheap/expensive vs market.
        # Without a market anchor the fail-closed state remains UNRELIABLE.
        return "UNRELIABLE"

    @staticmethod
    def _expectation_state(gap: ExpectationGap) -> ExpectationState:
        direction = (gap.direction or "").upper()
        if direction in {"BELOW_MARKET", "UNDER_EXPECTED", "NEGATIVE"}:
            return "UNDER_EXPECTED"
        if direction in {"ABOVE_MARKET", "OVER_EXPECTED", "POSITIVE"}:
            return "OVER_EXPECTED"
        if direction in {"IN_LINE", "INLINE"}:
            return "IN_LINE"
        if direction == "MIXED":
            return "MIXED"
        return "UNKNOWN"

    @staticmethod
    def _material_funding_risk(funding: FundingLoop) -> bool:
        return funding.funding_state in {"stressed", "debt_funded"} and bool(
            set(funding.reason_codes) & {"NEGATIVE_OCF", "MATERIAL_FACTORING_EXPOSURE"}
        )

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        decision_context, assessment = self._context_builder.build(context, state)
        updates = {
            key: value
            for key, value in (
                ("fundamental_state", self._fundamental_override),
                ("valuation_state", self._valuation_override),
                ("expectation_state", self._expectation_override),
                ("evidence_confidence", self._evidence_confidence_override),
                ("claim_ids", self._claim_ids_override),
                ("material_funding_risk", self._funding_override),
            )
            if value is not None
        }
        if updates:
            decision_context = decision_context.model_copy(update=updates)
        decision, derivation = self._engine.evaluate_with_derivation(
            decision_context,
            assessment,
        )
        evidence_refs = assessment.evidence_refs
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
            evidence_refs=evidence_refs,
        )
        provenance_inputs = tuple(
            DecisionStateInput(
                dimension={
                    "expectation_gap": "expectation",
                    "valuation_market_gap": "valuation",
                }.get(item.dimension, item.dimension),
                state=item.state,
                thesis_keys=(
                    decision.used_thesis_ids if item.dimension == "thesis_portfolio" else ()
                ),
                claim_keys=(
                    decision.used_claim_ids if item.dimension == "semantic_signals" else ()
                ),
                evidence_refs=item.evidence_refs,
            )
            for item in assessment.dimensions
        )
        provenance = DecisionStateProvenance(
            domain_status=record.domain_status,
            inputs=provenance_inputs,
            evidence_refs=evidence_refs,
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
                    evidence_refs=evidence_refs,
                ),
                ArtifactWrite(
                    key=DECISION_STATE_PROVENANCE,
                    value=provenance,
                    producer_id=self.spec.module_id,
                    evidence_refs=evidence_refs,
                ),
                ArtifactWrite(
                    key=DECISION_INPUT_ASSESSMENT,
                    value=assessment,
                    producer_id=self.spec.module_id,
                    evidence_refs=assessment.evidence_refs,
                ),
                ArtifactWrite(
                    key=DECISION_DERIVATION,
                    value=derivation,
                    producer_id=self.spec.module_id,
                    evidence_refs=derivation.evidence_refs,
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
            research_os_version=RESEARCH_OS_VERSION,
        )
        self._downstream_modules = tuple(downstream_modules)

    def compile(
        self,
        command: ResearchRunCommand,
        bootstrap: ArtifactSnapshot,
        strategy: StrategyResolution,
    ) -> ModulePlan:
        benchmark_registry = builtin_benchmark_registry()
        valuation_method_registry = builtin_valuation_method_registry()
        modules: tuple[ResearchModule, ...] = (
            ResolvedStrategyModule(strategy),
            KpiProviderModule(strategy, self._registry),
            FinancialResearchModule(command),
            CapitalResearchModule(),
            ThesisPortfolioModule(command.thesis.prior_theses),
            DriverSemanticResearchModule(command),
            ExpectationResearchModule(command),
            ForecastResearchModule(command, benchmark_registry=benchmark_registry),
            PeerResearchModule(command),
            ValuationResearchModule(command, method_registry=valuation_method_registry),
            SensitivityResearchModule(command),
            MonitoringResearchModule(command),
            MethodologyDisclosureModule(),
            ResearchSufficiencyModule(),
            PortfolioDecisionModule(),
            *self._downstream_modules,
        )
        return ModulePlanCompiler(self.catalog).compile(
            modules,
            initial_snapshot=bootstrap,
        )
