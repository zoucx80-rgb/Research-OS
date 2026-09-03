from datetime import date
from decimal import Decimal

from research_os.contracts.evidence import EvidenceRef
from research_os.valuation.execution import ValuationExecution
from research_os.valuation.methods import (
    PEMethod,
    ValuationMethodInput,
    ValuationSupportAssessment,
)


def _execution(**updates):
    data = {
        "selected_model": "pe",
        "support_assessment": ValuationSupportAssessment(
            method_id="pe",
            status="SUPPORTED",
            reason_codes=("STABLE_EARNINGS",),
            rationale="Earnings are sufficiently stable for a multiple cross-check.",
        ),
        "executed_model": "pe",
        "business_model": "manufacturing",
        "inputs": {"eps": Decimal("1"), "multiple": Decimal("15")},
        "scenario_logic": "explicit bear, base and bull multiples",
        "evidence_refs": (
            EvidenceRef(
                evidence_id="ev:eps",
                revision=1,
                content_fingerprint="a" * 64,
            ),
        ),
        "driver_bridge": ("Earnings", "Valuation"),
    }
    data.update(updates)
    return ValuationExecution(**data)


def test_valuation_execution_defaults_to_missing_without_supported_output():
    assert _execution().result is None


def test_valuation_result_carries_scenarios_sensitivity_and_lineage():
    inputs = ValuationMethodInput(
        currency="CNY",
        basis="equity_per_share",
        valuation_date=date(2026, 9, 3),
        values={
            "eps": Decimal("1.2"),
            "multiple": Decimal("15"),
            "bear_multiple": Decimal("12"),
            "bull_multiple": Decimal("18"),
        },
        evidence_refs=(
            EvidenceRef(
                evidence_id="ev:eps",
                revision=1,
                content_fingerprint="a" * 64,
            ),
        ),
    )
    result = PEMethod().execute(inputs)
    execution = _execution(result=result)

    assert execution.result is not None
    assert execution.result.bear_case == Decimal("14.4")
    assert execution.result.base_case == Decimal("18.0")
    assert execution.result.bull_case == Decimal("21.6")
    assert execution.result.sensitivities
    assert execution.result.evidence_refs == inputs.evidence_refs
