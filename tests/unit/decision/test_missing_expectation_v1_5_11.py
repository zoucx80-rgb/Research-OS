from datetime import datetime, timezone

from research_os.decision.engine import DecisionEngine
from research_os.decision.models import DecisionContext


def context(**updates):
    data = dict(
        company_id="GENERIC",
        fundamental_state="STABLE",
        valuation_state="FAIR",
        expectation_state="UNKNOWN",
        thesis_state="ACTIVE",
        evidence_confidence=0.9,
        evidence_ids=["ev:1"],
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
    )
    data.update(updates)
    return DecisionContext(**data)


def test_unknown_expectation_is_a_valid_missingness_state():
    assert context().expectation_state == "UNKNOWN"


def test_unknown_expectation_does_not_trigger_directional_risk_review():
    record = DecisionEngine().evaluate(
        context(fundamental_state="DETERIORATING", expectation_state="UNKNOWN")
    )
    assert record.state != "RISK_REVIEW"
    assert "FUNDAMENTAL_RISK" not in record.reason_codes


def test_unresolved_thesis_waits_for_confirmation_instead_of_becoming_active():
    record = DecisionEngine().evaluate(context(thesis_state="UNRESOLVED"))
    assert record.state == "WAIT_FOR_CONFIRMATION"
    assert "CONFIRMATION_REQUIRED" in record.reason_codes
