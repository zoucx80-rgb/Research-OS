from __future__ import annotations

from research_os.runtime.builtin_modules import (
    DecisionModule,
    DriverThesisModule,
    ExpectationModule,
    build_builtin_modules,
)
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.provenance import resolve_state_input


class ProfessionalDriverThesisModule(DriverThesisModule):
    """v1.5.03 driver/thesis contract under the canonical module identity."""

    spec = DriverThesisModule.spec.model_copy(update={"module_version": "1.2.0"})


class ProfessionalExpectationModule(ExpectationModule):
    """Make expectation quality relative to both calendar age and material events."""

    spec = ExpectationModule.spec.model_copy(update={"module_version": "1.2.0"})

    def run(self, context, state):
        result = super().run(context, state)
        quality = self.validator.assess_consensus_quality(
            vintage=self.inputs.expectation_vintage,
            decision_ts=context.decision_ts,
            latest_material_event_ts=self.inputs.latest_material_event_ts,
        )
        artifacts = dict(result.artifacts)
        artifacts["expectation.quality"] = quality
        validation = dict(artifacts.get("validation.expectation") or {})
        validation["quality_status"] = quality.status
        validation["quality_reason_codes"] = list(quality.reason_codes)
        artifacts["validation.expectation"] = validation
        return result.model_copy(update={"artifacts": artifacts})


class ProfessionalDecisionModule(DecisionModule):
    """Canonical decision module with explicit state provenance and exposure-aware risk."""

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


def build_professional_builtin_modules(*, registry, inputs: ResearchInputs | None = None):
    """Compose v1.5.03 behavior without duplicating the canonical pipeline."""

    run_inputs = inputs or ResearchInputs()
    modules = build_builtin_modules(registry=registry, inputs=run_inputs)
    result = []
    for module in modules:
        if isinstance(module, DriverThesisModule):
            result.append(ProfessionalDriverThesisModule())
        elif isinstance(module, ExpectationModule):
            result.append(ProfessionalExpectationModule(inputs=run_inputs))
        elif isinstance(module, DecisionModule):
            result.append(ProfessionalDecisionModule(inputs=run_inputs))
        else:
            result.append(module)
    return result
