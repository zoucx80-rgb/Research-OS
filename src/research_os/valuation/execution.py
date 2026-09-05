from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from research_os.contracts.artifact_values import AssumptionRef
from research_os.contracts.artifact_values import ModelFitnessInputs
from research_os.contracts.evidence import EvidenceRef
from research_os.valuation.fitness import ValuationFitnessPolicy
from research_os.valuation.methods import (
    ValuationMethodInput,
    ValuationMethodResult,
    ValuationSupportAssessment,
)
from research_os.valuation.registry import (
    ValuationMethodRegistry,
    builtin_valuation_method_registry,
)


ValuationResult = ValuationMethodResult


class ValuationExecution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    selected_model: str
    support_assessment: ValuationSupportAssessment
    executed_model: str
    business_model: str
    inputs: Mapping[str, object] = Field(default_factory=dict)
    assumption_refs: tuple[AssumptionRef, ...] = Field(default_factory=tuple)
    scenario_logic: str
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    driver_bridge: tuple[str, ...] = Field(default_factory=tuple)
    result: ValuationMethodResult | None = None

    @field_validator("inputs")
    @classmethod
    def _freeze_inputs(cls, value: Mapping[str, object]) -> Mapping[str, object]:
        return MappingProxyType(dict(value))

    @field_serializer("inputs")
    def _serialize_inputs(self, value: Mapping[str, object]) -> dict[str, object]:
        return dict(value)


class ValuationExecutionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: Literal["PASS", "VALUATION_GATE_FAIL", "INSUFFICIENT_EVIDENCE"]
    errors: tuple[str, ...] = Field(default_factory=tuple)


class ValuationExecutionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_key: str
    method_input: ValuationMethodInput
    scenario_logic: str
    driver_bridge: tuple[str, ...] = ()

    @field_validator("model_key", "scenario_logic")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("valuation execution request fields must be non-empty")
        return normalized

    @field_validator("driver_bridge")
    @classmethod
    def _canonical_driver_bridge(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("valuation driver bridge steps must be non-empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("valuation driver bridge steps must be unique")
        return normalized


class ControlledValuationExecution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    execution: ValuationExecution
    validation: ValuationExecutionResult

    @property
    def supported(self) -> bool:
        return self.validation.status == "PASS"


_DISTRIBUTOR_DRIVER_BRIDGE = (
    "Revenue",
    "Gross Profit",
    "Working Capital",
    "Financing Requirement",
    "Financing Cost",
    "Credit / Inventory Loss",
    "Net Profit / Cash Economics",
    "Valuation",
)


class ValuationExecutionValidator:
    def validate(self, execution: ValuationExecution) -> ValuationExecutionResult:
        errors: list[str] = []
        if execution.selected_model != execution.executed_model:
            errors.append("selected valuation model does not match executed model")
        if execution.support_assessment.method_id != execution.selected_model:
            errors.append("valuation support assessment does not match selected model")
        if execution.result is not None and execution.result.method_id != execution.executed_model:
            errors.append("valuation method result does not match executed model")
        if execution.result is not None and (
            execution.result.currency != execution.inputs.get("currency", execution.result.currency)
        ):
            errors.append("valuation result currency does not match execution inputs")
        if execution.business_model == "distributor":
            positions = []
            for step in _DISTRIBUTOR_DRIVER_BRIDGE:
                try:
                    positions.append(execution.driver_bridge.index(step))
                except ValueError:
                    errors.append(f"distributor driver bridge missing: {step}")
            if positions and positions != sorted(positions):
                errors.append("distributor driver bridge is out of causal order")
        if errors:
            return ValuationExecutionResult(status="VALUATION_GATE_FAIL", errors=tuple(errors))
        if execution.support_assessment.status in {
            "CONTRAINDICATED",
            "INSUFFICIENT_EVIDENCE",
        }:
            return ValuationExecutionResult(
                status="INSUFFICIENT_EVIDENCE",
                errors=("valuation method is not economically supported",),
            )
        if not execution.scenario_logic.strip() or not execution.inputs:
            return ValuationExecutionResult(
                status="INSUFFICIENT_EVIDENCE",
                errors=("valuation execution lacks inputs or scenario rationale",),
            )
        if not execution.evidence_refs:
            return ValuationExecutionResult(
                status="INSUFFICIENT_EVIDENCE",
                errors=("valuation execution lacks revision-bound evidence lineage",),
            )
        if execution.result is None or execution.result.status == "INSUFFICIENT_EVIDENCE":
            return ValuationExecutionResult(
                status="INSUFFICIENT_EVIDENCE",
                errors=("valuation method did not produce a supported result",),
            )
        return ValuationExecutionResult(status="PASS")


class ControlledValuationExecutionService:
    def __init__(
        self,
        *,
        method_registry: ValuationMethodRegistry | None = None,
        fitness_policy: ValuationFitnessPolicy | None = None,
        validator: ValuationExecutionValidator | None = None,
    ) -> None:
        self._methods = method_registry or builtin_valuation_method_registry()
        self._fitness = fitness_policy or ValuationFitnessPolicy()
        self._validator = validator or ValuationExecutionValidator()

    def execute(
        self,
        *,
        request: ValuationExecutionRequest,
        fitness: ModelFitnessInputs,
        business_model: str,
        funding_state: str | None = None,
        funding_reason_codes: tuple[str, ...] = (),
    ) -> ControlledValuationExecution:
        method = self._methods.require(request.model_key)
        support = self._fitness.assess(
            method_id=request.model_key,
            inputs=fitness,
            business_model=business_model,
            funding_state=funding_state,
            funding_reason_codes=funding_reason_codes,
        )
        result = None
        if support.status not in {"CONTRAINDICATED", "INSUFFICIENT_EVIDENCE"}:
            result = method.execute(request.method_input)
        execution = ValuationExecution(
            selected_model=request.model_key,
            support_assessment=support,
            executed_model=request.model_key,
            business_model=business_model,
            inputs={
                **dict(request.method_input.values),
                "currency": request.method_input.currency,
                "basis": request.method_input.basis,
                "valuation_date": request.method_input.valuation_date,
            },
            assumption_refs=request.method_input.assumption_refs,
            scenario_logic=request.scenario_logic,
            evidence_refs=request.method_input.evidence_refs,
            driver_bridge=request.driver_bridge,
            result=result,
        )
        return ControlledValuationExecution(
            execution=execution,
            validation=self._validator.validate(execution),
        )


__all__ = [
    "ControlledValuationExecution",
    "ControlledValuationExecutionService",
    "ValuationExecution",
    "ValuationExecutionRequest",
    "ValuationExecutionResult",
    "ValuationExecutionValidator",
    "ValuationResult",
]
