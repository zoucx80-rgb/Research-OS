import pytest
from pydantic import ValidationError

from research_os.valuation.reconciliation import (
    ValuationModelRationale,
    ValuationRange,
    ValuationReconciliation,
    ValuationReconciler,
)


def _range(range_id, low, high, *, basis="equity_per_share", role="model_implied"):
    return ValuationRange(
        range_id=range_id,
        model_id=range_id,
        role=role,
        basis=basis,
        currency="CNY",
        low=low,
        high=high,
        evidence_ids=(f"ev:{range_id}",),
    )


def test_compatible_model_ranges_produce_true_mathematical_intersection():
    result = ValuationReconciler.reconcile(
        (
            _range("pe", 12.0, 18.0),
            _range("ev-ebitda", 15.0, 20.0),
        )
    )

    assert result.status == "INTERSECTION"
    assert result.low == 15.0
    assert result.high == 18.0
    assert result.included_range_ids == ("pe", "ev-ebitda")


def test_non_overlapping_model_ranges_report_disagreement_without_fake_band():
    result = ValuationReconciler.reconcile(
        (
            _range("pe", 12.0, 14.0),
            _range("dcf", 17.0, 20.0),
        )
    )

    assert result.status == "MODEL_DISAGREEMENT"
    assert result.low is None
    assert result.high is None


def test_incompatible_valuation_bases_are_not_comparable():
    result = ValuationReconciler.reconcile(
        (
            _range("pe", 12.0, 18.0, basis="equity_per_share"),
            _range("ev-ebitda", 150.0, 200.0, basis="enterprise_value"),
        )
    )

    assert result.status == "NOT_COMPARABLE"
    assert result.low is None
    assert result.high is None


def test_scenario_and_market_anchor_are_not_forced_into_model_intersection():
    result = ValuationReconciler.reconcile(
        (
            _range("bear-bull", 10.0, 22.0, role="scenario"),
            _range("market-anchor", 14.0, 17.0, role="market_anchor"),
        )
    )

    assert result.status == "NOT_COMPARABLE"


def test_compatible_cross_checks_are_explicitly_an_envelope_not_intersection():
    result = ValuationReconciler.reconcile(
        (
            _range("peer-check", 13.0, 16.0, role="cross_check"),
            _range("transaction-check", 15.0, 19.0, role="cross_check"),
        )
    )

    assert result.status == "CROSS_CHECK_BAND"
    assert result.low == 13.0
    assert result.high == 19.0
    assert result.method == "cross_check_envelope"


def test_valuation_range_rejects_reversed_bounds():
    with pytest.raises(ValidationError):
        _range("pe", 18.0, 12.0)


@pytest.mark.parametrize("field", ("range_id", "model_id", "basis", "currency"))
def test_valuation_range_rejects_blank_canonical_identifiers(field):
    data = {
        "range_id": "pe",
        "model_id": "pe",
        "role": "model_implied",
        "basis": "equity_per_share",
        "currency": "CNY",
        "low": 12.0,
        "high": 18.0,
    }
    data[field] = "   "

    with pytest.raises(ValidationError):
        ValuationRange(**data)


@pytest.mark.parametrize("field,value", (("low", float("nan")), ("high", float("inf"))))
def test_valuation_range_rejects_non_finite_bounds(field, value):
    data = {
        "range_id": "pe",
        "model_id": "pe",
        "role": "model_implied",
        "basis": "equity_per_share",
        "currency": "CNY",
        "low": 12.0,
        "high": 18.0,
    }
    data[field] = value

    with pytest.raises(ValidationError):
        ValuationRange(**data)


def test_reconciliation_rejects_duplicate_range_ids():
    with pytest.raises(ValueError, match="range_id values must be unique"):
        ValuationReconciler.reconcile(
            (
                _range("pe", 12.0, 18.0),
                _range("pe", 15.0, 20.0),
            )
        )


def test_reconciliation_result_rejects_status_method_and_bounds_mismatch():
    with pytest.raises(ValidationError):
        ValuationReconciliation(
            status="INTERSECTION",
            method="none",
            reason="invalid result",
        )


@pytest.mark.parametrize(
    "payload",
    (
        {
            "status": "INTERSECTION",
            "method": "mathematical_intersection",
            "low": 12.0,
            "high": 18.0,
            "basis": "equity_per_share",
            "currency": "CNY",
            "included_range_ids": ("pe",),
            "reason": "invalid one-range intersection",
        },
        {
            "status": "CROSS_CHECK_BAND",
            "method": "cross_check_envelope",
            "low": 12.0,
            "high": 18.0,
            "basis": "equity_per_share",
            "currency": "CNY",
            "included_range_ids": ("peer",),
            "reason": "invalid one-range envelope",
        },
        {
            "status": "MODEL_DISAGREEMENT",
            "method": "none",
            "basis": "equity_per_share",
            "currency": "CNY",
            "included_range_ids": ("dcf",),
            "reason": "invalid one-range disagreement",
        },
    ),
)
def test_reconciliation_statuses_requiring_comparison_need_two_ranges(payload):
    with pytest.raises(ValidationError):
        ValuationReconciliation(**payload)

    with pytest.raises(ValidationError):
        ValuationReconciliation(
            status="NOT_COMPARABLE",
            method="none",
            low=12.0,
            high=18.0,
            reason="invalid result",
        )


def test_model_rationale_accepts_economic_fitness_reason():
    rationale = ValuationModelRationale(
        model_id="dcf",
        status="DOWNGRADED",
        economic_factors=("cash_flow_visibility", "terminal_value_sensitivity"),
        explanation="cash-flow visibility is limited and terminal value dominates the estimate",
    )

    assert rationale.status == "DOWNGRADED"


@pytest.mark.parametrize(
    "explanation",
    (
        "DCF downgraded because Research OS v1.5.12 is conservative",
        "renderer version requires DCF downgrade",
        "release version caused this model to be unsuitable",
        "build 1.5.12 dictated the downgrade",
        "release 1.5.12 changed the result",
        "版本v1.5.12导致模型降级",
        "构建版本 1.5.12 改变了结果",
        "发布版1.5.12要求下调DCF权重",
    ),
)
def test_model_rationale_rejects_software_version_as_economic_reason(explanation):
    with pytest.raises(ValidationError):
        ValuationModelRationale(
            model_id="dcf",
            status="DOWNGRADED",
            economic_factors=("cash_flow_visibility",),
            explanation=explanation,
        )
