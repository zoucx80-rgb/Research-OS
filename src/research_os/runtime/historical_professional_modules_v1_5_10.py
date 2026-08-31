from __future__ import annotations

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
from research_os.runtime.professional_modules import (
    ProfessionalExpectationModule,
    ProfessionalValuationModule,
)
from research_os.runtime.provenance import resolve_state_input
from research_os.runtime.research_completeness import ResearchCompletenessModule


class ProfessionalDriverThesisModuleV1_5_10(DriverThesisModule):
    """Frozen pre-v1.5.11 thesis semantics for historical report replay."""

    spec = DriverThesisModule.spec.model_copy(update={"module_version": "1.3.0"})


class ProfessionalDecisionModuleV1_5_10(DecisionModule):
    """Frozen pre-v1.5.11 decision semantics for historical report replay."""

    spec = DecisionModule.spec.model_copy(
        update={
            "module_version": "1.2.0",
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

    def _state_provenance(self):
        return {
            "fundamental": resolve_state_input(
                self.inputs.fundamental_state_input,
                self.inputs.fundamental_state,
            ),
            "valuation": resolve_state_input(
                self.inputs.valuation_state_input,
                self.inputs.valuation_state,
            ),
            "expectation": resolve_state_input(
                self.inputs.expectation_state_input,
                self.inputs.expectation_state,
            ),
        }

    def run(self, context, state):
        result = super().run(context, state)
        artifacts = dict(result.artifacts)
        artifacts["decision.state_provenance"] = self._state_provenance()
        return result.model_copy(update={"artifacts": artifacts})


def build_professional_builtin_modules_v1_5_10(
    *,
    registry,
    inputs: ResearchInputs | None = None,
):
    """Recompose the v1.5.10 professional runtime for deterministic replay."""

    run_inputs = inputs or ResearchInputs()
    modules = build_builtin_modules(registry=registry, inputs=run_inputs)
    result = []
    for module in modules:
        if isinstance(module, PITLineageModule):
            result.append(module)
            result.append(FinancialFactSnapshotModule())
            result.append(ResearchCompletenessModule(inputs=run_inputs))
        elif isinstance(module, DriverThesisModule):
            result.append(ProfessionalDriverThesisModuleV1_5_10())
        elif isinstance(module, ExpectationModule):
            result.append(ProfessionalExpectationModule(inputs=run_inputs))
        elif isinstance(module, ValuationModule):
            result.append(ProfessionalValuationModule(inputs=run_inputs))
        elif isinstance(module, DecisionModule):
            result.append(ProfessionalDecisionModuleV1_5_10(inputs=run_inputs))
        else:
            result.append(module)
    return result
