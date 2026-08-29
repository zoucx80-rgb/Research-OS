from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from research_os.domain.evidence import Evidence
from research_os.storage.models import Base, EvidenceStore


def test_future_evidence_never_enters_asof_snapshot_across_boundary_matrix():
    base=datetime(2026,1,1,tzinfo=timezone.utc)
    for days in (1,2,30,180,365):
        engine=create_engine("sqlite+pysqlite:///:memory:"); Base.metadata.create_all(engine)
        s=EvidenceStore(Session(engine))
        s.append(Evidence(evidence_id=f"e{days}",company_id="X",evidence_type="filing_fact",
            publish_ts=base+timedelta(days=days),ingested_at=base+timedelta(days=days),
            confidence_grade="A",verification_status="PRIMARY_VERIFIED"))
        assert s.as_of("X",base)==[]
