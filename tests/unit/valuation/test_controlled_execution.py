from __future__ import annotations

from datetime import date
from decimal import Decimal

from research_os.contracts.artifact_values import ModelFitnessInputs
from research_os.contracts.evidence import EvidenceRef
from research_os.valuation.execution import (
    ControlledValuationExecutionService,
    ValuationExecutionRequest,
)
from research_os.valuation.methods import ValuationMethodInput


def _reference() -> EvidenceRef:
    return EvidenceRef(
        evidence_id="ev:valuation:pe",
        revision=1,
        content_fingerprint="a" * 64,
    )


def _fitness(**updates: float) -> ModelFitnessInputs:
    payload = {
        "data_quality": 0.9,
        "earnings_stability": 0.9,
        "cash_flow_visibility": 0.9,
        "capital_structure_fit": 0.9,
        "business_model_fit": 0.9,
        "forecast_stability": 0.9,
    }
    payload.update(updates)
    return ModelFitnessInputs(**payload)


def _request() -> ValuationExecutionRequest:
    return ValuationExecutionRequest(
        model_key="pe",
        method_input=ValuationMethodInput(
            currency="CNY",
            basis="equity_per_share",
            valuation_date=date(2026, 8, 29),
            values={
                "eps": Decimal("2"),
                "multiple": Decimal("10"),
                "bear_multiple": Decimal("8"),
                "bull_multiple": Decimal("12"),
            },
            evidence_refs=(_reference(),),
        ),
        scenario_logic="EPS multiplied by explicit bear, base, and bull PE multiples.",
    )


def test_controlled_execution_calls_selected_method_and_validator() -> None:
    result = ControlledValuationExecutionService().execute(
        request=_request(),
        fitness=_fitness(),
        business_model="manufacturing",
        funding_state="self_funded",
        funding_reason_codes=(),
    )

    assert result.validation.status == "PASS"
    assert result.execution.executed_model == "pe"
    assert result.execution.result is not None
    assert result.execution.result.base_case == Decimal("20")


def test_controlled_execution_does_not_run_contraindicated_method() -> None:
    result = ControlledValuationExecutionService().execute(
        request=_request(),
        fitness=_fitness(earnings_stability=0.1),
        business_model="manufacturing",
        funding_state="self_funded",
        funding_reason_codes=(),
    )

    assert result.validation.status == "INSUFFICIENT_EVIDENCE"
    assert result.execution.support_assessment.status == "CONTRAINDICATED"
    assert result.execution.result is None
