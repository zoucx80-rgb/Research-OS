from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from research_os.contracts.artifact_values import AssumptionRef
from research_os.contracts.evidence import EvidenceRef
from research_os.valuation.fitness import ModelFitnessInputs, ValuationFitnessPolicy
from research_os.valuation.methods import (
    DCFMethod,
    PBMethod,
    PEMethod,
    SOTPMethod,
    ValuationMethodInput,
)


def _fitness(**updates: float) -> ModelFitnessInputs:
    values = {
        "data_quality": 0.9,
        "earnings_stability": 0.9,
        "cash_flow_visibility": 0.9,
        "capital_structure_fit": 0.9,
        "business_model_fit": 0.9,
        "forecast_stability": 0.9,
    }
    values.update(updates)
    return ModelFitnessInputs(**values)


@pytest.mark.parametrize(
    "method_id,fitness,business_model,expected",
    (
        ("pe", _fitness(), "manufacturing", "SUPPORTED"),
        ("dcf", _fitness(cash_flow_visibility=0.5), "manufacturing", "CONDITIONALLY_SUPPORTED"),
        ("pb", _fitness(business_model_fit=0.35), "financial", "SANITY_CHECK_ONLY"),
        ("dcf", _fitness(cash_flow_visibility=0.2), "distributor", "CONTRAINDICATED"),
        ("pe", _fitness(data_quality=0.2), "manufacturing", "INSUFFICIENT_EVIDENCE"),
    ),
)
def test_fitness_policy_emits_explainable_support_states(
    method_id: str,
    fitness: ModelFitnessInputs,
    business_model: str,
    expected: str,
) -> None:
    result = ValuationFitnessPolicy().assess(
        method_id=method_id,
        inputs=fitness,
        business_model=business_model,
    )

    assert result.status == expected
    assert result.reason_codes
    assert "1.6.0" not in result.rationale


def test_method_rationale_rejects_software_version_explanations() -> None:
    assessment = ValuationFitnessPolicy().assess(
        method_id="pe", inputs=_fitness(), business_model="manufacturing"
    )

    with pytest.raises(ValidationError, match="version"):
        assessment.model_copy(
            update={"rationale": "Research OS v1.6.0 selected PE"}
        ).model_validate(
            {
                **assessment.model_dump(),
                "rationale": "Research OS v1.6.0 selected PE",
            }
        )


def _input(values: dict[str, object]) -> ValuationMethodInput:
    return ValuationMethodInput(
        currency="CNY",
        basis="equity_per_share",
        valuation_date=date(2026, 9, 3),
        values=values,
        evidence_refs=(
            EvidenceRef(
                evidence_id="ev:valuation",
                revision=1,
                content_fingerprint="a" * 64,
            ),
        ),
        assumption_refs=(
            AssumptionRef(
                assumption_key="assumption:multiple",
                assumption_version="1.0.0",
                content_fingerprint="b" * 64,
            ),
        ),
    )


@pytest.mark.parametrize("method", (PEMethod(), PBMethod(), DCFMethod(), SOTPMethod()))
def test_methods_do_not_generate_values_when_required_inputs_are_missing(method) -> None:
    result = method.execute(_input({}))

    assert result.status == "INSUFFICIENT_EVIDENCE"
    assert result.base_case is None
    assert result.bear_case is None
    assert result.bull_case is None
    assert result.limitations


def test_pe_method_preserves_scenarios_assumptions_sensitivity_and_lineage() -> None:
    result = PEMethod().execute(
        _input(
            {
                "eps": Decimal("1.20"),
                "multiple": Decimal("15"),
                "bear_multiple": Decimal("12"),
                "bull_multiple": Decimal("18"),
            }
        )
    )

    assert result.status == "SUPPORTED"
    assert result.bear_case == Decimal("14.40")
    assert result.base_case == Decimal("18.00")
    assert result.bull_case == Decimal("21.60")
    assert result.evidence_refs[0].evidence_id == "ev:valuation"
    assert result.assumption_refs[0].assumption_key == "assumption:multiple"
    assert result.sensitivities
