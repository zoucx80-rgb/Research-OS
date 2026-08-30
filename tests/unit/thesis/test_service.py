from datetime import date, datetime, timezone
from research_os.domain.evidence import Evidence
from research_os.thesis.models import Thesis, Falsifier
from research_os.thesis.service import ThesisService

def metric(name,value):
    return Evidence(evidence_id=name,company_id="X",evidence_type="calculated_metric",source_table=name,value=value,
       publish_ts=datetime(2026,8,29,tzinfo=timezone.utc),ingested_at=datetime(2026,8,29,tzinfo=timezone.utc),
       confidence_grade="B",verification_status="PRIMARY_VERIFIED")

def test_triggered_falsifier_moves_active_thesis_to_weakening():
    t=Thesis(thesis_id="t",company_id="X",title="Cash quality",statement="growth converts to cash",mechanism="m",anti_thesis="counter",status="active",
      falsifiers=[Falsifier(metric="cfo",operator="<",threshold=0)],next_check_date=date(2026,10,31))
    r=ThesisService().evaluate_existing(t,[metric("cfo",-100)])
    assert r.status=="weakening"
    assert r.triggered_falsifiers==["cfo < 0.0"]


def test_legacy_cfo_falsifier_resolves_canonical_ocf_evidence():
    t=Thesis(thesis_id="t:legacy",company_id="X",title="Cash quality",statement="growth converts to cash",mechanism="m",anti_thesis="counter",status="active",
      falsifiers=[Falsifier(metric="cfo",operator="<",threshold=0)],next_check_date=date(2026,10,31))
    r=ThesisService().evaluate_existing(t,[metric("ocf",-100)])
    assert r.status=="weakening"
    assert r.triggered_falsifiers==["cfo < 0.0"]


def test_canonical_ocf_wins_when_legacy_alias_conflicts():
    t=Thesis(thesis_id="t:alias-priority",company_id="X",title="Cash quality",statement="growth converts to cash",mechanism="m",anti_thesis="counter",status="active",
      falsifiers=[Falsifier(metric="cfo",operator="<",threshold=0)],next_check_date=date(2026,10,31))
    r=ThesisService().evaluate_existing(t,[metric("cfo",100),metric("ocf",-100)])
    assert r.status=="weakening"
