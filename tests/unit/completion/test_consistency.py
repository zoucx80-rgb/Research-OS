from research_os.completion.gate import REQUIRED_MODULES, ResearchCompletionGate, normalize_claim_capabilities
from research_os.completion.models import ResearchCompletionInput


def statuses(**updates):
    data = {name: "PASS" for name in REQUIRED_MODULES}
    data["Forecast Discipline"] = "NOT_APPLICABLE"
    data.update(updates)
    return data


def evaluate(module_statuses, claims=None):
    return ResearchCompletionGate().evaluate(ResearchCompletionInput(
        module_statuses=module_statuses,
        tool_completed=True,
        claimed_conclusions=claims or [],
    ))


def test_expectation_aliases_normalize_to_one_capability():
    assert normalize_claim_capabilities(["beat", "priced_in", "expectation_gap"]) == {"EXPECTATION"}


def test_valuation_aliases_normalize_to_one_capability():
    assert normalize_claim_capabilities(["valuation", "target_price", "fair_value"]) == {"VALUATION"}


def test_decision_state_is_not_implicitly_a_valuation_claim():
    assert normalize_claim_capabilities(["decision_state"]) == {"DECISION"}


def test_unclaimed_expectation_gap_does_not_block_completion():
    result = evaluate(statuses(**{"Expectation Evidence": "INSUFFICIENT_EVIDENCE"}))
    assert result.final_status == "COMPLETE"
    assert "Expectation Evidence" not in result.blocking_modules


def test_claimed_expectation_requires_expectation_evidence():
    result = evaluate(statuses(**{"Expectation Evidence": "INSUFFICIENT_EVIDENCE"}), ["beat"])
    assert result.final_status == "INCOMPLETE"
    assert "Expectation Evidence" in result.blocking_modules


def test_unclaimed_valuation_execution_does_not_block_nonvaluation_decision():
    result = evaluate(statuses(**{"Valuation Execution": "INSUFFICIENT_EVIDENCE"}), ["decision_state"])
    assert result.final_status == "COMPLETE"
    assert "Valuation Execution" not in result.blocking_modules


def test_target_price_claim_requires_valuation_execution():
    result = evaluate(statuses(**{"Valuation Execution": "INSUFFICIENT_EVIDENCE"}), ["target_price"])
    assert result.final_status == "INCOMPLETE"
    assert "Valuation Execution" in result.blocking_modules
