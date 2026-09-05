"""Focused professional research modules: valuation sensitivity."""

from __future__ import annotations

from typing import Any

from research_os.application.command import ResearchRunCommand
from research_os.contracts.artifact_values import SensitivitySet
from research_os.contracts.artifact_values import ValuationExecution as ArtifactValuationExecution
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
from research_os.runtime.core_artifacts import VALUATION_MARKET_ANCHOR
from research_os.runtime.core_artifacts import VALUATION_MARKET_GAP
from research_os.runtime.core_artifacts import VALUATION_RECONCILIATION
from research_os.runtime.core_artifacts import VALUATION_RESULT
from research_os.runtime.core_artifacts import VALUATION_ROUTING
from research_os.runtime.modules import ModuleResult
from research_os.runtime.modules import ModuleSpec
from research_os.runtime.modules import ModuleStatus
from research_os.runtime.state import ResearchStateView
from research_os.valuation.execution import ControlledValuationExecutionService
from research_os.valuation.market import MarketAnchorValidator
from research_os.valuation.market import ValuationMarketGapService
from research_os.valuation.reconciliation import ValuationRange as DomainValuationRange
from research_os.valuation.reconciliation import ValuationReconciler
from research_os.valuation.registry import ValuationMethodRegistry
from research_os.valuation.registry import builtin_valuation_method_registry
from research_os.valuation.router import ValuationContext
from research_os.valuation.router import ValuationRouter
from research_os.application.professional_modules._common import _lineage_refs


class ValuationResearchModule:
    _base_spec = ModuleSpec(
        module_id="core:professional-valuation",
        module_version="2.0.1",
        requires=frozenset((BUSINESS_MODEL_PROFILE, CAPITAL_FUNDING_LOOP, PEERS_NORMALIZED)),
        provides=frozenset(
            (
                VALUATION_ROUTING,
                VALUATION_EXECUTION,
                VALUATION_RESULT,
                VALUATION_RECONCILIATION,
                VALUATION_MARKET_GAP,
            )
        ),
        required_for_completion=False,
    )

    def __init__(
        self,
        command: ResearchRunCommand,
        *,
        method_registry: ValuationMethodRegistry | None = None,
    ) -> None:
        self._input = command.valuation
        self._router = ValuationRouter()
        self._execution = ControlledValuationExecutionService(
            method_registry=method_registry or builtin_valuation_method_registry()
        )
        self._anchor_validator = MarketAnchorValidator()
        self._market_gap = ValuationMarketGapService()
        self.spec = self._base_spec.model_copy(
            update={
                "provides": (
                    self._base_spec.provides
                    if self._input.market_anchor is None
                    else frozenset((*self._base_spec.provides, VALUATION_MARKET_ANCHOR))
                )
            }
        )

    def run(self, context: ResearchContext, state: ResearchStateView) -> ModuleResult:
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
        preferred = (*routing.primary_model_keys, *routing.secondary_model_keys)
        request = next(
            (
                item
                for model_key in preferred
                for item in self._input.execution_requests
                if item.model_key == model_key
            ),
            None,
        )
        if request is not None:
            controlled = self._execution.execute(
                request=request,
                fitness=model_inputs[request.model_key],
                business_model=profile.primary_model,
                funding_state=funding.funding_state,
                funding_reason_codes=funding.reason_codes,
            )
            method_result = controlled.execution.result
            results = (
                ()
                if method_result is None
                else (
                    ValuationResult(
                        model_key=method_result.method_id,
                        status=method_result.status,
                        formula_version=f"{method_result.method_id}@1.0.0",
                        value=method_result.base_case,
                        unit=(
                            f"{method_result.currency}/share"
                            if method_result.basis == "per_share"
                            else method_result.currency
                        ),
                        evidence_refs=method_result.evidence_refs,
                        assumption_refs=method_result.assumption_refs,
                    ),
                )
            )
            execution = ArtifactValuationExecution(
                domain_status=(
                    "SUPPORTED" if controlled.validation.status == "PASS" else "INSUFFICIENT_EVIDENCE"
                ),
                execution_source="CONTROLLED",
                validation_status=controlled.validation.status,
                validation_errors=controlled.validation.errors,
                selected_model=request.model_key,
                results=results,
                evidence_refs=controlled.execution.evidence_refs,
                assumption_refs=controlled.execution.assumption_refs,
            )
        elif self._input.execution is not None:
            execution = self._validated_external_execution(
                self._input.execution,
                preferred=preferred,
            )
        else:
            errors = (
                "no routed valuation execution request"
                if self._input.execution_requests
                else "valuation execution was not provided"
            )
            execution = ArtifactValuationExecution(
                domain_status="INSUFFICIENT_EVIDENCE",
                execution_source="NONE",
                validation_status="INSUFFICIENT_EVIDENCE",
                validation_errors=(errors,),
            )
        execution_refs = _lineage_refs(execution)
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
            assumption_refs=tuple(
                {
                    (
                        reference.assumption_key,
                        reference.assumption_version,
                        reference.content_fingerprint,
                    ): reference
                    for item in self._input.ranges
                    for reference in item.assumption_refs
                }.values()
            ),
        )
        anchor = self._input.market_anchor
        if anchor is not None:
            anchor = self._anchor_validator.validate(
                anchor,
                company_id=context.company.company_id,
                decision_ts=context.decision_ts,
            )
        market_gap = self._market_gap.compare(reconciliation, self._input.ranges, anchor)
        status: ModuleStatus = (
            "PASS"
            if model_inputs or execution.results or self._input.ranges or anchor is not None
            else "INSUFFICIENT_EVIDENCE"
        )
        writes: list[ArtifactWrite[Any]] = [
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
            ArtifactWrite(
                key=VALUATION_MARKET_GAP,
                value=market_gap,
                producer_id=self.spec.module_id,
                evidence_refs=market_gap.evidence_refs,
            ),
        ]
        if anchor is not None:
            writes.append(
                ArtifactWrite(
                    key=VALUATION_MARKET_ANCHOR,
                    value=anchor,
                    producer_id=self.spec.module_id,
                    evidence_refs=anchor.evidence_refs,
                )
            )
        return ModuleResult(
            module_id=self.spec.module_id,
            status=status,
            writes=tuple(writes),
        )

    @staticmethod
    def _validated_external_execution(
        execution: ArtifactValuationExecution,
        *,
        preferred: tuple[str, ...],
    ) -> ArtifactValuationExecution:
        errors = []
        if not execution.results:
            errors.append("external valuation execution has no results")
        supported = tuple(item for item in execution.results if item.status == "SUPPORTED")
        if not supported:
            errors.append("external valuation execution has no supported result")
        if any(not (item.evidence_refs or item.assumption_refs) for item in supported):
            errors.append("external valuation result lacks lineage")
        selected = next(
            (item for model_key in preferred for item in supported if item.model_key == model_key),
            supported[0] if supported else None,
        )
        if preferred and selected is not None and selected.model_key not in preferred:
            errors.append("external valuation result does not match routed models")
        return execution.model_copy(
            update={
                "domain_status": "INSUFFICIENT_EVIDENCE" if errors else "SUPPORTED",
                "execution_source": "EXTERNAL",
                "validation_status": "INSUFFICIENT_EVIDENCE" if errors else "PASS",
                "validation_errors": tuple(errors),
                "selected_model": None if selected is None else selected.model_key,
            }
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
