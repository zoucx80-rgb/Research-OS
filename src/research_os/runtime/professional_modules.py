from __future__ import annotations

from research_os.decision.models import DecisionContext
from research_os.decision.validation import validate_decision_state
from research_os.runtime.builtin_modules import (
    DecisionModule,
    DriverThesisModule,
    ExpectationModule,
    PITLineageModule,
    ValuationModule,
    build_builtin_modules,
)
from research_os.runtime.financial_snapshot import FinancialFactSnapshotModule
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.modules import ModuleResult
from research_os.runtime.provenance import StateInput, resolve_state_input
from research_os.runtime.research_completeness import ResearchCompletenessModule
from research_os.thesis.semantic_service_v1_5_11 import SemanticThesisService


class ProfessionalDriverThesisModule(DriverThesisModule):
    """Professional driver/thesis contract under the canonical module identity."""

    spec = DriverThesisModule.spec.model_copy(
        update={
            "module_version": "1.4.0",
            "provides": set(DriverThesisModule.spec.provides)
            | {"thesis.semantic_signal_assessment"},
        }
    )

    def __init__(self, *, inputs: ResearchInputs | None = None):
        run_inputs = inputs or ResearchInputs()
        super().__init__(
            theses=SemanticThesisService(
                comparison_rules=run_inputs.thesis_comparison_rules,
                prior_theses=run_inputs.prior_theses,
            )
        )
        self.inputs = run_inputs

    def run(self, context, state):
        result = super().run(context, state)
        evidence = list(state.get("evidence.pit", []) or [])
        artifacts = dict(result.artifacts)
        artifacts["thesis.semantic_signal_assessment"] = (
            self.theses.assess_signals(evidence) if evidence else None
        )
        return result.model_copy(update={"artifacts": artifacts})


class ProfessionalExpectationModule(ExpectationModule):
    """Make expectation quality relative to both calendar age and material events."""

    spec = ExpectationModule.spec.model_copy(
        update={
            "module_version": "1.3.0",
            "provides": set(ExpectationModule.spec.provides) | {"expectation.gap"},
        }
    )

    def run(self, context, state):
        result = super().run(context, state)
        quality = self.validator.assess_consensus_quality(
            vintage=self.inputs.expectation_vintage,
            decision_ts=context.decision_ts,
            latest_material_event_ts=self.inputs.latest_material_event_ts,
        )
        artifacts = dict(result.artifacts)
        artifacts["expectation.quality"] = quality
        artifacts["expectation.gap"] = self.inputs.expectation_gap
        validation = dict(artifacts.get("validation.expectation") or {})
        validation["quality_status"] = quality.status
        validation["quality_reason_codes"] = list(quality.reason_codes)
        artifacts["validation.expectation"] = validation
        return result.model_copy(update={"artifacts": artifacts})


class ProfessionalValuationModule(ValuationModule):
    """Expose explicit execution/result artifacts without deriving valuation values."""

    spec = ValuationModule.spec.model_copy(
        update={
            "module_version": "1.2.0",
            "provides": set(ValuationModule.spec.provides)
            | {"valuation.execution", "valuation.result"},
        }
    )

    def run(self, context, state):
        result = super().run(context, state)
        artifacts = dict(result.artifacts)
        execution = self.inputs.valuation_execution
        artifacts["valuation.execution"] = execution
        artifacts["valuation.result"] = (
            execution.result if execution is not None else None
        )
        return result.model_copy(update={"artifacts": artifacts})


class ProfessionalDecisionModule(DecisionModule):
    """Canonical decision module with explicit state provenance and missingness safety."""

    spec = DecisionModule.spec.model_copy(
        update={
            "module_version": "1.3.0",
            "provides": set(DecisionModule.spec.provides) | {"decision.state_provenance"},
        }
    )

    @staticmethod
    def _funding_material_risk(funding) -> bool:
        if funding is None:
            return False
        state = getattr(funding, "funding_state", None)
        reasons = set(getattr(funding, "reason_codes", []) or [])
        if state == "stressed":
            return True
        if (
            state == "debt_funded"
            and {"DEBT_FUNDS_NWC", "NEGATIVE_OCF"}.issubset(reasons)
        ):
            return True
        if "MATERIAL_FACTORING_EXPOSURE" in reasons and reasons.intersection(
            {"NEGATIVE_OCF", "HIGH_IWCR", "DEBT_FUNDS_NWC"}
        ):
            return True
        return False

    def _has_explicit_expectation_state(self) -> bool:
        return (
            self.inputs.expectation_state_input is not None
            or "expectation_state" in self.inputs.model_fields_set
        )

    def _effective_expectation_state(self, state) -> str:
        if self.inputs.expectation_state_input is not None:
            return self.inputs.expectation_state_input.value
        if self._has_explicit_expectation_state():
            return self.inputs.expectation_state
        snapshot = state.get("expectation.snapshot")
        validation = state.get("validation.expectation") or {}
        validation_status = (
            validation.get("status")
            if isinstance(validation, dict)
            else getattr(validation, "status", None)
        )
        if snapshot is None or validation_status == "INSUFFICIENT_EVIDENCE":
            return "UNKNOWN"
        return self.inputs.expectation_state

    def _state_provenance(self, state=None):
        if state is not None and not self._has_explicit_expectation_state():
            expectation_state = self._effective_expectation_state(state)
            if expectation_state == "UNKNOWN":
                expectation = StateInput(
                    value="UNKNOWN",
                    source="derived",
                    method="no PIT-compliant expectation snapshot available",
                )
            else:
                expectation = resolve_state_input(None, expectation_state)
        else:
            expectation = resolve_state_input(
                self.inputs.expectation_state_input,
                self.inputs.expectation_state,
            )
        return {
            "fundamental": resolve_state_input(
                self.inputs.fundamental_state_input,
                self.inputs.fundamental_state,
            ),
            "valuation": resolve_state_input(
                self.inputs.valuation_state_input,
                self.inputs.valuation_state,
            ),
            "expectation": expectation,
        }

    def run(self, context, state):
        theses = list(state.get("thesis.items", []) or [])
        claims = list(state.get("claims.items", []) or [])
        evidence = list(state.get("evidence.pit", []) or [])
        funding = state.get("capital.funding_loop")
        if not theses:
            result = ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                artifacts={
                    "decision.record": None,
                    "validation.decision": {"status": "INSUFFICIENT_EVIDENCE"},
                    "decision.state_provenance": self._state_provenance(state),
                },
            )
            return result

        thesis_state = theses[0].status.upper()
        if thesis_state not in {
            "STRENGTHENING",
            "ACTIVE",
            "WEAKENING",
            "FALSIFIED",
            "UNRESOLVED",
        }:
            thesis_state = "ACTIVE"

        decision = self.engine.evaluate(
            DecisionContext(
                company_id=context.company.company_id,
                fundamental_state=self.inputs.fundamental_state,
                valuation_state=self.inputs.valuation_state,
                expectation_state=self._effective_expectation_state(state),
                thesis_state=thesis_state,
                evidence_confidence=self._confidence(evidence),
                evidence_ids=[item.evidence_id for item in evidence],
                claim_ids=[claim.claim_id for claim in claims],
                decision_ts=context.decision_ts,
                research_os_version=self.inputs.versions.get(
                    "research_os_version",
                    context.baseline.research_os_version,
                ),
                material_risk=self._funding_material_risk(funding),
            )
        )
        validate_decision_state(decision.state)
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS",
            artifacts={
                "decision.record": decision,
                "validation.decision": {"status": "PASS"},
                "decision.state_provenance": self._state_provenance(state),
            },
            evidence_ids=[item.evidence_id for item in evidence],
        )


def build_professional_builtin_modules(*, registry, inputs: ResearchInputs | None = None):
    """Compose professional behavior without duplicating the canonical pipeline."""

    run_inputs = inputs or ResearchInputs()
    modules = build_builtin_modules(registry=registry, inputs=run_inputs)
    result = []
    for module in modules:
        if isinstance(module, PITLineageModule):
            result.append(module)
            result.append(FinancialFactSnapshotModule())
            result.append(ResearchCompletenessModule(inputs=run_inputs))
        elif isinstance(module, DriverThesisModule):
            result.append(ProfessionalDriverThesisModule(inputs=run_inputs))
        elif isinstance(module, ExpectationModule):
            result.append(ProfessionalExpectationModule(inputs=run_inputs))
        elif isinstance(module, ValuationModule):
            result.append(ProfessionalValuationModule(inputs=run_inputs))
        elif isinstance(module, DecisionModule):
            result.append(ProfessionalDecisionModule(inputs=run_inputs))
        else:
            result.append(module)
    return result
