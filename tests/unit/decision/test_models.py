from datetime import datetime, timezone
from research_os.decision.models import DecisionStateRecord

def test_decision_state_is_research_only():
    s=DecisionStateRecord(company_id="X",state="WAIT_FOR_CONFIRMATION",decision_ts=datetime.now(timezone.utc))
    assert "BUY" not in s.state
