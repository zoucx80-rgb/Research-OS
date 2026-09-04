"""Focused professional research modules: valuation sensitivity."""

from __future__ import annotations

from research_os.application.command import ResearchRunCommand
from research_os.contracts.artifact_values import SensitivitySet
from research_os.contracts.artifact_values import ValuationExecution
from research_os.contracts.artifact_values import ValuationReconciliation
from research_os.contracts.artifact_values import ValuationResult
from research_os.contracts.artifact_values import ValuationRouting
from research_os.contracts.artifacts import ArtifactWrite
from research_os.runtime.context import ResearchContext
from research_os.runtime.core_artifacts import BUSINESS_MODEL_PROFILE
from research_os.runtime.core_artifacts import CAPITAL_FUNDING_LOOP
from research_os.runtime.core_artifacts import PEERS_NORMALIZED
from research_os.runtime.core_artifacts import SCENARIO_SENSITIVITIES
from research_os.runtime.core_artifacts import VALUATION_EXECUTION
from research_os.runtime.core_artifacts import VALUATION_RECONCILIATION
from research_os.runtime.core_artifacts import VALUATION_RESULT
from research_os.runtime.core_artifacts import VALUATION_ROUTING
from research_os.runtime.modules import ModuleResult
from research_os.runtime.modules import ModuleSpec
from research_os.runtime.modules import ModuleStatus
from research_os.runtime.state import ResearchStateView
from research_os.valuation.reconciliation import ValuationRange as DomainValuationRange
from research_os.valuation.reconciliation import ValuationReconciler
from research_os.valuation.router import ValuationContext
from research_os.valuation.router import ValuationRouter
from research_os.application.professional_modules._common import _lineage_refs


class ValuationResearchModule:
    spec = ModuleSpec(
        module_id="core:professional-valuation",
        module_version="2.0.1",
        requires=frozenset((BUSINESS_MODEL_PROFILE, CAPITAL_FUNDING_LOOP, PEERS_NORMALIZED)),
        provides=frozenset(
            (VALUATION_ROUTING, VALUATION_EXECUTION, VALUATION_RESULT, VALUATION_RECONCILIATION)
        ),
        required_for_completion=False,
    )

    def __init__(self, command: ResearchRunCommand) -> None:
        self._input = command.valuation
        self._router = ValuationRouter()

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        del context
        profile = state.require(BUSINESS_MODEL_PROFILE)
        funding = state.require(CAPITAL_FUNDING_LOOP)
        state.require(PEERS_NORMALIZED)
        model_inputs = {item.model_id: item.fitness for item in self._input.models}
        routed = self._router.route(
            ValuationContext(
                business_model=profile.primary_model,
                models=model_inputs,
                funding_state=funding.funding_state,
                funding_reason_codes=funding.reason_codes,
            )
        )
        routing_refs = _lineage_refs(self._input.models, funding)
        routing = ValuationRouting(
            domain_status="SUPPORTED" if model_inputs else "INSUFFICIENT_EVIDENCE",
            primary_model_keys=tuple(routed.primary_models),
            secondary_model_keys=tuple(routed.secondary_models),
            evidence_refs=routing_refs,
        )
        execution = self._input.execution or ValuationExecution()
        execution_refs = _lineage_refs(execution)
        preferred = (*routing.primary_model_keys, *routing.secondary_model_keys)
        selected_result = None
        if execution.results:
            selected_result = next(
                (
                    item
                    for model_key in preferred
                    for item in execution.results
                    if item.model_key == model_key
                ),
                execution.results[0],
            )
        result_value = selected_result or ValuationResult(
            model_key="unavailable",
            status="INSUFFICIENT_EVIDENCE",
            formula_version="unavailable",
        )
        result_refs = _lineage_refs(result_value)

        domain_ranges = tuple(
            DomainValuationRange(
                range_id=item.range_key,
                model_id=item.range_key,
                role=item.role,
                basis=item.basis,
                currency=item.currency,
                low=float(item.low),
                high=float(item.high),
                evidence_ids=tuple(ref.evidence_id for ref in item.evidence_refs),
                assumption_ids=tuple(ref.assumption_key for ref in item.assumption_refs),
            )
            for item in self._input.ranges
        )
        reconciled = ValuationReconciler.reconcile(domain_ranges)
        range_refs = _lineage_refs(self._input.ranges)
        reconciliation = ValuationReconciliation(
            domain_status=(
                "SUPPORTED"
                if reconciled.status in {"INTERSECTION", "CROSS_CHECK_BAND", "MODEL_DISAGREEMENT"}
                else "INSUFFICIENT_EVIDENCE"
            ),
            reconciliation_status=reconciled.status,
            method=reconciled.method,
            low=reconciled.low,
            high=reconciled.high,
            included_range_keys=reconciled.included_range_ids,
            evidence_refs=range_refs,
        )
        status: ModuleStatus = (
            "PASS"
            if model_inputs or execution.results or self._input.ranges
            else "INSUFFICIENT_EVIDENCE"
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            writes=(
                ArtifactWrite(
                    key=VALUATION_ROUTING,
                    value=routing,
                    producer_id=self.spec.module_id,
                    evidence_refs=routing_refs,
                ),
                ArtifactWrite(
                    key=VALUATION_EXECUTION,
                    value=execution,
                    producer_id=self.spec.module_id,
                    evidence_refs=execution_refs,
                ),
                ArtifactWrite(
                    key=VALUATION_RESULT,
                    value=result_value,
                    producer_id=self.spec.module_id,
                    evidence_refs=result_refs,
                ),
                ArtifactWrite(
                    key=VALUATION_RECONCILIATION,
                    value=reconciliation,
                    producer_id=self.spec.module_id,
                    evidence_refs=range_refs,
                ),
            ),
        )


class SensitivityResearchModule:
    spec = ModuleSpec(
        module_id="core:professional-sensitivity",
        module_version="2.0.1",
        requires=frozenset(),
        provides=frozenset((SCENARIO_SENSITIVITIES,)),
        required_for_completion=False,
    )

    def __init__(self, command: ResearchRunCommand) -> None:
        self._input = command.readiness

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
        del context, state
        refs = _lineage_refs(self._input.sensitivities)
        value = SensitivitySet(
            domain_status="SUPPORTED" if self._input.sensitivities else "INSUFFICIENT_EVIDENCE",
            cases=self._input.sensitivities,
            evidence_refs=refs,
        )
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS" if self._input.sensitivities else "INSUFFICIENT_EVIDENCE",
            writes=(
                ArtifactWrite(
                    key=SCENARIO_SENSITIVITIES,
                    value=value,
                    producer_id=self.spec.module_id,
                    evidence_refs=refs,
                ),
            ),
        )
