from research_os.completion.gate import REQUIRED_MODULES, ResearchCompletionGate
from research_os.completion.models import ResearchCompletionInput
from research_os.reporting.summary import DecisionSummaryBuilder


def completed_without_expectation_claim():
    statuses = {name: "PASS" for name in REQUIRED_MODULES}
    statuses["Forecast Discipline"] = "NOT_APPLICABLE"
    statuses["Expectation Evidence"] = "INSUFFICIENT_EVIDENCE"
    return ResearchCompletionGate().evaluate(ResearchCompletionInput(
        module_statuses=statuses,
        tool_completed=True,
        claimed_conclusions=[],
    ))


def base_context(completion):
    return {
        "company_id": "synthetic",
        "business_model": "distributor",
        "primary_thesis": "synthetic thesis",
        "thesis_state": "ACTIVE",
        "fundamental_state": "STABLE",
        "expectation_state": "MIXED",
        "valuation_state": "FAIR",
        "evidence_confidence": .8,
        "top_drivers": ["driver"],
        "top_risks": ["risk"],
        "next_verification_event": "next disclosure",
        "research_os_version": "1.2.0",
        "decision_state": "HOLD_AND_MONITOR",
        "completion": completion,
    }


def test_reporting_consumes_completion_result_without_redefining_complete():
    completion = completed_without_expectation_claim()
    assert completion.final_status == "COMPLETE"
    summary = DecisionSummaryBuilder().build(base_context(completion))
    assert summary.final_status == completion.final_status
    assert summary.blocking_modules == completion.blocking_modules
    assert summary.module_statuses == completion.module_statuses
    assert summary.expectation_evidence_status == "INSUFFICIENT_EVIDENCE"


def test_incomplete_result_propagates_exact_blockers():
    statuses = {name: "PASS" for name in REQUIRED_MODULES}
    statuses["Forecast Discipline"] = "NOT_APPLICABLE"
    statuses["Financial Sanity"] = "FAIL"
    completion = ResearchCompletionGate().evaluate(ResearchCompletionInput(
        module_statuses=statuses,
        tool_completed=True,
    ))
    summary = DecisionSummaryBuilder().build(base_context(completion))
    assert summary.final_status == "INCOMPLETE"
    assert summary.blocking_modules == ["Financial Sanity"]
    assert summary.module_statuses["Financial Sanity"] == "FAIL"
