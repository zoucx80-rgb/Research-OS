from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ValuationResult(BaseModel):
    """Explicit valuation output; presentation must not infer missing values."""

    model_config = ConfigDict(frozen=True)

    currency: str
    valuation_date: date | None = None
    equity_value: float | None = None
    enterprise_value: float | None = None
    per_share_value: float | None = None
    bear_case: float | None = None
    base_case: float | None = None
    bull_case: float | None = None
    primary_range_low: float | None = None
    primary_range_high: float | None = None
    current_price: float | None = None
    implied_upside_downside: float | None = None
    method_result: dict[str, Any] = Field(default_factory=dict)
    sensitivities: list[dict[str, Any]] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    assumption_ids: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ValuationExecution(BaseModel):
    model_config = ConfigDict(frozen=True)

    selected_model: str
    model_fitness_score: float
    selection_reason: str
    executed_model: str
    business_model: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    scenario_logic: str
    lineage: dict[str, list[str]] = Field(default_factory=dict)
    driver_bridge: list[str] = Field(default_factory=list)
    result: ValuationResult | None = None


class ValuationExecutionResult(BaseModel):
    status: Literal["PASS", "VALUATION_GATE_FAIL", "INSUFFICIENT_EVIDENCE"]
    errors: list[str] = Field(default_factory=list)


_DISTRIBUTOR_DRIVER_BRIDGE = [
    "Revenue",
    "Gross Profit",
    "Working Capital",
    "Financing Requirement",
    "Financing Cost",
    "Credit / Inventory Loss",
    "Net Profit / Cash Economics",
    "Valuation",
]


class ValuationExecutionValidator:
    def validate(self, execution: ValuationExecution) -> ValuationExecutionResult:
        errors: list[str] = []
        if execution.selected_model != execution.executed_model:
            errors.append("selected valuation model does not match executed model")
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
            return ValuationExecutionResult(status="VALUATION_GATE_FAIL", errors=errors)
        if execution.model_fitness_score <= 0 or not execution.selection_reason.strip() or not execution.scenario_logic.strip():
            return ValuationExecutionResult(
                status="INSUFFICIENT_EVIDENCE",
                errors=["valuation model fitness or scenario rationale is insufficient"],
            )
        if not execution.inputs or not execution.lineage:
            return ValuationExecutionResult(
                status="INSUFFICIENT_EVIDENCE",
                errors=["valuation execution lacks input/evidence lineage"],
            )
        return ValuationExecutionResult(status="PASS")
