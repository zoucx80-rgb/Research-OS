import pytest
from pydantic import ValidationError

from research_os.reporting.summary import DecisionSummary


def _base(**updates):
    data = dict(
        company_id="synthetic",
        business_model="distributor",
        primary_thesis="Growth converts to cash",
        thesis_state="ACTIVE",
        fundamental_state="IMPROVING",
        expectation_state="UNDER_EXPECTED",
        valuation_state="FAIR",
        evidence_confidence="B",
        top_drivers=["revenue", "working_capital", "financing"],
        top_risks=["inventory", "credit", "funding"],
        next_verification_event="next material disclosure",
        research_os_version="1.2.0",
        decision_state="WAIT_FOR_CONFIRMATION",
        final_status="COMPLETE",
        expectation_evidence_status="PASS",
        valuation_execution_status="PASS",
    )
    data.update(updates)
    return data


def test_report_rejects_illegal_decision_state_by_canonical_enum():
    with pytest.raises(ValidationError):
        DecisionSummary(**_base(decision_state="NEUTRAL"))


def test_reporting_model_does_not_redefine_completion_policy():
    summary = DecisionSummary(**_base(expectation_evidence_status="INSUFFICIENT_EVIDENCE"))
    assert summary.final_status == "COMPLETE"
    assert summary.expectation_evidence_status == "INSUFFICIENT_EVIDENCE"


def test_incomplete_report_can_surface_insufficient_expectation_evidence_without_fake_state():
    summary = DecisionSummary(**_base(
        final_status="INCOMPLETE",
        expectation_state="INSUFFICIENT_EVIDENCE",
        expectation_evidence_status="INSUFFICIENT_EVIDENCE",
    ))
    assert summary.final_status == "INCOMPLETE"
    assert summary.expectation_state == "INSUFFICIENT_EVIDENCE"
