from research_os.valuation.execution import ValuationExecution, ValuationResult


def _execution(**updates):
    data = {
        "selected_model": "dcf",
        "model_fitness_score": 0.8,
        "selection_reason": "cash economics",
        "executed_model": "dcf",
        "business_model": "manufacturing",
        "inputs": {"fcf": 1.0},
        "assumptions": [],
        "scenario_logic": "three cases",
        "lineage": {"fcf": ["e1"]},
        "driver_bridge": ["FCF", "Valuation"],
    }
    data.update(updates)
    return ValuationExecution(**data)


def test_valuation_result_defaults_to_missing_without_supported_output():
    execution = _execution()
    assert execution.result is None


def test_valuation_result_carries_scenarios_ranges_and_lineage():
    result = ValuationResult(
        currency="CNY",
        per_share_value=18.0,
        bear_case=14.0,
        base_case=18.0,
        bull_case=22.0,
        primary_range_low=16.0,
        primary_range_high=20.0,
        current_price=15.0,
        implied_upside_downside=0.20,
        evidence_ids=["v1"],
        assumption_ids=["a1"],
        sensitivities=[{"name": "wacc", "value": 0.09}],
    )
    execution = _execution(result=result)
    assert execution.result is not None
    assert execution.result.primary_range_low == 16.0
    assert execution.result.evidence_ids == ["v1"]
    assert execution.result.assumption_ids == ["a1"]


def test_valuation_result_does_not_derive_upside_from_price():
    result = ValuationResult(
        currency="CNY",
        per_share_value=18.0,
        current_price=15.0,
    )
    assert result.implied_upside_downside is None


def test_method_specific_payload_is_additive_and_loss_aware():
    result = ValuationResult(
        currency="CNY",
        method_result={"terminal_growth": 0.03},
    )
    assert result.per_share_value is None
    assert result.method_result == {"terminal_growth": 0.03}
