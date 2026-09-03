from __future__ import annotations

from research_os.contracts.artifact_values import ModelFitnessInputs
from research_os.policies import PolicyRegistry, builtin_policy_registry
from research_os.valuation.methods import ValuationSupportAssessment


class ValuationFitnessPolicy:
    def __init__(self, *, policy_registry: PolicyRegistry | None = None) -> None:
        self._policy = policy_registry or builtin_policy_registry()

    def _threshold(self, name: str) -> float:
        return float(self._policy.decimal_value("valuation_fitness", name))

    def assess(
        self,
        *,
        method_id: str,
        inputs: ModelFitnessInputs,
        business_model: str,
        funding_state: str | None = None,
        funding_reason_codes: tuple[str, ...] = (),
    ) -> ValuationSupportAssessment:
        if inputs.data_quality < self._threshold("minimum_data_quality"):
            return ValuationSupportAssessment(
                method_id=method_id,
                status="INSUFFICIENT_EVIDENCE",
                reason_codes=("DATA_QUALITY_BELOW_MINIMUM",),
                rationale="Available inputs do not support a traceable valuation conclusion.",
            )
        contraindicated = self._threshold("contraindicated_factor_maximum")
        sanity = self._threshold("sanity_check_factor_minimum")
        supported = self._threshold("supported_factor_minimum")
        if (
            method_id == "dcf"
            and business_model == "distributor"
            and inputs.cash_flow_visibility <= contraindicated
        ):
            return ValuationSupportAssessment(
                method_id=method_id,
                status="CONTRAINDICATED",
                reason_codes=("DISTRIBUTOR_CASH_FLOW_NOT_VISIBLE",),
                rationale="Working-capital volatility makes long-horizon cash-flow estimates economically unreliable.",
            )
        if (
            method_id == "pe"
            and funding_state == "debt_funded"
            and "NEGATIVE_OCF" in funding_reason_codes
        ):
            return ValuationSupportAssessment(
                method_id=method_id,
                status="CONDITIONALLY_SUPPORTED",
                reason_codes=("EARNINGS_NOT_CONVERTING_TO_CASH",),
                rationale="Earnings multiples require a cash-conversion cross-check under debt-funded growth.",
            )
        method_factor = {
            "dcf": inputs.cash_flow_visibility,
            "pe": inputs.earnings_stability,
            "pb": inputs.business_model_fit,
            "sotp": inputs.business_model_fit,
        }.get(method_id, inputs.business_model_fit)
        if method_factor < sanity:
            return ValuationSupportAssessment(
                method_id=method_id,
                status="CONTRAINDICATED",
                reason_codes=("METHOD_ECONOMICS_CONTRAINDICATED",),
                rationale="The method does not represent the available economic evidence.",
            )
        if method_factor < supported:
            return ValuationSupportAssessment(
                method_id=method_id,
                status="SANITY_CHECK_ONLY" if method_factor < 0.4 else "CONDITIONALLY_SUPPORTED",
                reason_codes=("METHOD_FACTOR_BELOW_FULL_SUPPORT",),
                rationale="The method is useful only as a bounded cross-check under current evidence quality.",
            )
        weak_factors = tuple(
            name
            for name, value in (
                ("capital_structure_fit", inputs.capital_structure_fit),
                ("business_model_fit", inputs.business_model_fit),
                ("forecast_stability", inputs.forecast_stability),
            )
            if value < supported
        )
        if weak_factors:
            return ValuationSupportAssessment(
                method_id=method_id,
                status="CONDITIONALLY_SUPPORTED",
                reason_codes=tuple(f"LOW_{name.upper()}" for name in weak_factors),
                rationale="The method requires explicit limitations for weaker economic fit dimensions.",
            )
        return ValuationSupportAssessment(
            method_id=method_id,
            status="SUPPORTED",
            reason_codes=("ECONOMIC_INPUT_CONTRACT_SUPPORTED",),
            rationale="The method matches the business economics and available traceable inputs.",
        )


__all__ = ["ModelFitnessInputs", "ValuationFitnessPolicy"]
