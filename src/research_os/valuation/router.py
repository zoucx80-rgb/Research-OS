from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from research_os.contracts.artifact_values import ModelFitnessInputs
from research_os.valuation.fitness import ValuationFitnessPolicy
from research_os.valuation.methods import ValuationSupportStatus


class RoutedModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_name: str
    status: ValuationSupportStatus
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    rationale: str


class ValuationContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    business_model: str
    models: dict[str, ModelFitnessInputs]
    funding_state: str | None = None
    funding_reason_codes: tuple[str, ...] = Field(default_factory=tuple)


class ValuationRoutingResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    models: dict[str, RoutedModel]
    primary_models: list[str] = Field(default_factory=list)
    secondary_models: list[str] = Field(default_factory=list)
    disagreement_diagnosis: str


class ValuationRouter:
    def __init__(self, *, fitness_policy: ValuationFitnessPolicy | None = None) -> None:
        self._fitness = fitness_policy or ValuationFitnessPolicy()

    def route(self, context: ValuationContext) -> ValuationRoutingResult:
        routed = {
            model_name: RoutedModel(
                model_name=model_name,
                **self._fitness.assess(
                    method_id=model_name,
                    inputs=inputs,
                    business_model=context.business_model,
                    funding_state=context.funding_state,
                    funding_reason_codes=context.funding_reason_codes,
                ).model_dump(exclude={"method_id"}),
            )
            for model_name, inputs in sorted(context.models.items())
        }
        primary = [
            name for name, result in routed.items() if result.status == "SUPPORTED"
        ]
        secondary = [
            name
            for name, result in routed.items()
            if result.status == "CONDITIONALLY_SUPPORTED"
        ]
        diagnosis = (
            "; ".join(
                f"{name}:{result.status}:{','.join(result.reason_codes)}"
                for name, result in routed.items()
            )
            or "No applicable valuation method"
        )
        return ValuationRoutingResult(
            models=routed,
            primary_models=primary,
            secondary_models=secondary,
            disagreement_diagnosis=diagnosis,
        )


__all__ = ["RoutedModel", "ValuationContext", "ValuationRouter", "ValuationRoutingResult"]
