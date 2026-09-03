from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from research_os.contracts.artifact_values import AssumptionRef
from research_os.contracts.evidence import EvidenceRef
from research_os.valuation.methods import (
    ValuationMethodResult,
    ValuationSupportAssessment,
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
            return ValuationExecutionResult(
                status="VALUATION_GATE_FAIL", errors=tuple(errors)
            )
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
        return ValuationExecutionResult(status="PASS")


__all__ = [
    "ValuationExecution",
    "ValuationExecutionResult",
    "ValuationExecutionValidator",
    "ValuationResult",
]
