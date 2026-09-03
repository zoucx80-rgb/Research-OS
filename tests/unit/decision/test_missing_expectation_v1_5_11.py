from datetime import date, datetime, timezone

from research_os.contracts.artifact_values import Thesis, ThesisPortfolio
from research_os.contracts.evidence import EvidenceRef
from research_os.decision.engine import DecisionEngine
from research_os.decision.models import DecisionContext


def context(**updates):
    thesis_state = updates.pop("thesis_state", "ACTIVE")
    thesis = Thesis(
        thesis_key="thesis:test",
        company_id="GENERIC",
        title="Test",
        statement="Test",
        mechanism="Test",
        anti_thesis="Not test",
        status=thesis_state.lower(),
        falsifier_statements=("break",),
        next_check_date=date(2026, 12, 1),
        confidence=0.9,
        claim_strength="STRONG",
        evidence_refs=(EvidenceRef(evidence_id="ev:1", revision=1, content_fingerprint="a" * 64),),
    )
    portfolio = (
        ThesisPortfolio(unresolved=(thesis,), evidence_refs=thesis.evidence_refs)
        if thesis_state == "UNRESOLVED"
        else ThesisPortfolio(primary=thesis, evidence_refs=thesis.evidence_refs)
    )
    data = dict(
        company_id="GENERIC",
        fundamental_state="STABLE",
        valuation_state="FAIR",
        expectation_state="UNKNOWN",
        thesis_portfolio=portfolio,
        evidence_confidence=0.9,
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
    assert "PORTFOLIO_CONFLICT_UNRESOLVED" in record.reason_codes
