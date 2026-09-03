from datetime import date, datetime, timezone
from research_os.contracts.artifact_values import Thesis, ThesisPortfolio
from research_os.contracts.evidence import EvidenceRef
from research_os.decision.models import DecisionContext
from research_os.decision.engine import DecisionEngine


def ctx(**kw):
    thesis_status = kw.pop("thesis_state", "FALSIFIED")
    thesis = Thesis(
        thesis_key="thesis:test",
        company_id="X",
        title="Test",
        statement="Test",
        mechanism="Test",
        anti_thesis="Not test",
        status=thesis_status.lower(),
        falsifier_statements=("break",),
        next_check_date=date(2026, 12, 1),
        confidence=0.9,
        claim_strength="STRONG",
        evidence_refs=(
            EvidenceRef(
                evidence_id="e1",
                revision=1,
                content_fingerprint="a" * 64,
            ),
        ),
    )
    portfolio = (
        ThesisPortfolio(falsified=(thesis,), evidence_refs=thesis.evidence_refs)
        if thesis_status == "FALSIFIED"
        else ThesisPortfolio(primary=thesis, evidence_refs=thesis.evidence_refs)
    )
    d = dict(
        company_id="X",
        fundamental_state="DETERIORATING",
        valuation_state="CHEAP",
        expectation_state="MIXED",
        thesis_portfolio=portfolio,
        evidence_confidence=0.9,
        claim_ids=("c1",),
        decision_ts=datetime.now(timezone.utc),
    )
    d.update(kw)
    return DecisionContext(**d)


def test_falsified_thesis_forces_thesis_broken():
    assert DecisionEngine().evaluate(ctx()).state == "THESIS_BROKEN"


def test_insufficient_evidence_has_highest_precedence():
    assert DecisionEngine().evaluate(ctx(evidence_confidence=0.1)).state == "INSUFFICIENT_EVIDENCE"


def test_decision_record_preserves_context_needed_by_canonical_reporting():
    record = DecisionEngine().evaluate(
        ctx(
            fundamental_state="IMPROVING",
            valuation_state="FAIR",
            expectation_state="UNDER_EXPECTED",
            thesis_state="ACTIVE",
            evidence_confidence=0.85,
        )
    )
    assert record.fundamental_state == "IMPROVING"
    assert record.valuation_state == "FAIR"
    assert record.expectation_state == "UNDER_EXPECTED"
    assert record.thesis_state == "ACTIVE"
    assert record.evidence_confidence == 0.85
