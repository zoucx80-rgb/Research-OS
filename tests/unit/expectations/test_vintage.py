from datetime import datetime, timezone
from research_os.expectations.models import ConsensusVintage, ExpectationService

def v(as_of,np): return ConsensusVintage(company_id="300034.SZ",as_of=datetime.fromisoformat(as_of).replace(tzinfo=timezone.utc),forecast_period="2026FY",net_profit=np)

def test_snapshot_uses_latest_vintage_known_at_decision_time():
    s=ExpectationService(); s.add(v("2026-05-01",2.5)); s.add(v("2026-08-26",2.1))
    snap=s.snapshot("300034.SZ",datetime(2026,5,15,tzinfo=timezone.utc))
    assert snap.net_profit==2.5

def test_snapshot_can_select_internal_vs_sell_side_vintage():
    s=ExpectationService()
    s.add(ConsensusVintage(company_id="X",as_of=datetime(2026,5,1,tzinfo=timezone.utc),forecast_period="2026FY",net_profit=2.5,expectation_type="sell_side"))
    s.add(ConsensusVintage(company_id="X",as_of=datetime(2026,5,1,tzinfo=timezone.utc),forecast_period="2026FY",net_profit=2.2,expectation_type="internal"))
    assert s.snapshot("X",datetime(2026,5,2,tzinfo=timezone.utc),expectation_type="internal").net_profit==2.2
