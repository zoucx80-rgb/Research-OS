from research_os.completion.gate import REQUIRED_MODULES, ResearchCompletionGate
from research_os.completion.models import ResearchCompletionInput
from research_os.reporting.summary import DecisionSummaryBuilder


def completed_without_expectation_claim():
    statuses = {name: "PASS" for name in REQUIRED_MODULES}
    statuses["Forecast Discipline"] = "NOT_APPLICABLE"
    statuses["Expectation Evidence"] = "INSUFFICIENT_EVIDENCE"
    return ResearchCompletionGate().evaluate(
        ResearchCompletionInput(
            module_statuses=statuses,
            tool_completed=True,
            claimed_conclusions=[],
        )
    )


def test_reporting_consumes_completion_result_without_redefining_complete(
    canonical_report_result_factory,
):
    completion = completed_without_expectation_claim()
    assert completion.final_status == "COMPLETE"
    summary = DecisionSummaryBuilder().build(
        canonical_report_result_factory(completion=completion)
    )
    assert summary.final_status == completion.final_status
    assert summary.blocking_modules == completion.blocking_modules
    assert summary.module_statuses == completion.module_statuses
    assert summary.expectation_evidence_status == "INSUFFICIENT_EVIDENCE"


def test_incomplete_result_propagates_exact_blockers(canonical_report_result_factory):
    statuses = {name: "PASS" for name in REQUIRED_MODULES}
    statuses["Forecast Discipline"] = "NOT_APPLICABLE"
    statuses["Financial Sanity"] = "FAIL"
    completion = ResearchCompletionGate().evaluate(
        ResearchCompletionInput(
            module_statuses=statuses,
            tool_completed=True,
        )
    )
    summary = DecisionSummaryBuilder().build(
        canonical_report_result_factory(completion=completion)
    )
    assert summary.final_status == "INCOMPLETE"
    assert summary.blocking_modules == ["Financial Sanity"]
    assert summary.module_statuses["Financial Sanity"] == "FAIL"
