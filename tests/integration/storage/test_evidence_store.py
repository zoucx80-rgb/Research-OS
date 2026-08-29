from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from research_os.domain.evidence import Evidence
from research_os.storage.models import Base, EvidenceStore


def make_evidence(**kw):
    data = dict(
        evidence_id="e1", company_id="001287.SZ", evidence_type="filing_fact",
        period_end="2026-06-30", publish_ts=datetime(2026,8,25,tzinfo=timezone.utc),
        ingested_at=datetime(2026,8,25,1,tzinfo=timezone.utc), value=10,
        confidence_grade="A", verification_status="PRIMARY_VERIFIED", revision_no=1,
    )
    data.update(kw)
    return Evidence(**data)


def store():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return EvidenceStore(Session(engine))


def test_as_of_excludes_future_publication():
    s=store(); s.append(make_evidence())
    rows=s.as_of("001287.SZ", datetime(2026,8,24,23,59,59,tzinfo=timezone.utc))
    assert rows == []


def test_correction_creates_new_revision():
    s=store()
    s.append(make_evidence(evidence_id="rev", revision_no=1, value=10))
    s.append(make_evidence(evidence_id="rev", revision_no=2, value=12))
    rows=s.as_of("001287.SZ", datetime(2026,12,31,tzinfo=timezone.utc))
    assert [r.value for r in rows if r.evidence_id=="rev"] == [10,12]

def test_latest_as_of_returns_only_latest_known_revision_per_evidence_id():
    s=store()
    s.append(make_evidence(evidence_id="rev", revision_no=1, value=10, publish_ts=datetime(2026,8,1,tzinfo=timezone.utc)))
    s.append(make_evidence(evidence_id="rev", revision_no=2, value=12, publish_ts=datetime(2026,8,20,tzinfo=timezone.utc)))
    latest=s.latest_as_of("001287.SZ",datetime(2026,8,25,tzinfo=timezone.utc))
    assert [(x.evidence_id,x.revision_no,x.value) for x in latest]==[("rev",2,12)]
