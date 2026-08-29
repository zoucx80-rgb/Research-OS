from datetime import datetime, timezone
from research_os.decision.models import DecisionContext
from research_os.decision.engine import DecisionEngine

def ctx(**kw):
    d=dict(company_id="X",fundamental_state="DETERIORATING",valuation_state="CHEAP",expectation_state="MIXED",thesis_state="FALSIFIED",evidence_confidence=.9,evidence_ids=["e1"],claim_ids=["c1"],decision_ts=datetime.now(timezone.utc)); d.update(kw); return DecisionContext(**d)

def test_falsified_thesis_forces_thesis_broken():
    assert DecisionEngine().evaluate(ctx()).state=="THESIS_BROKEN"

def test_insufficient_evidence_has_highest_precedence():
    assert DecisionEngine().evaluate(ctx(evidence_confidence=.1)).state=="INSUFFICIENT_EVIDENCE"
