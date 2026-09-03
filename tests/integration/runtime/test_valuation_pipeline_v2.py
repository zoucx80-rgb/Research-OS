from __future__ import annotations

from datetime import date
from decimal import Decimal

from research_os.contracts.evidence import EvidenceRef
from research_os.valuation.fitness import ModelFitnessInputs
from research_os.valuation.methods import PEMethod, ValuationMethodInput
from research_os.valuation.reconciliation import ValuationRange, ValuationReconciler
from research_os.valuation.router import ValuationContext, ValuationRouter


def test_supported_method_executes_and_incompatible_basis_fails_reconciliation() -> None:
    routing = ValuationRouter().route(
        ValuationContext(
            business_model="manufacturing",
            models={
                "pe": ModelFitnessInputs(
                    data_quality=0.9,
                    earnings_stability=0.9,
                    cash_flow_visibility=0.8,
                    capital_structure_fit=0.8,
                    business_model_fit=0.9,
                    forecast_stability=0.8,
                )
            },
        )
    )
    result = PEMethod().execute(
        ValuationMethodInput(
            currency="CNY",
            basis="equity_per_share",
            valuation_date=date(2026, 9, 3),
            values={"eps": Decimal("1"), "multiple": Decimal("15")},
            evidence_refs=(EvidenceRef(evidence_id="ev:eps", revision=1, content_fingerprint="a" * 64),),
        )
    )
    reconciliation = ValuationReconciler.reconcile(
        (
            ValuationRange(range_id="pe", model_id="pe", role="model_implied", basis="equity_per_share", currency="CNY", low=12, high=18),
            ValuationRange(range_id="dcf", model_id="dcf", role="model_implied", basis="enterprise_value", currency="CNY", low=100, high=120),
        )
    )

    assert routing.models["pe"].status == "SUPPORTED"
    assert routing.primary_models == ["pe"]
    assert result.base_case == Decimal("15")
    assert reconciliation.status == "NOT_COMPARABLE"
