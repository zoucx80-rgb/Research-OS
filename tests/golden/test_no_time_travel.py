from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from research_os.adapters.persistence.evidence_repository import SqlEvidenceRepository
from research_os.adapters.persistence.schema import PersistenceBase
from research_os.domain.evidence import Evidence


def test_future_evidence_never_enters_asof_snapshot_across_boundary_matrix():
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for days in (1, 2, 30, 180, 365):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        PersistenceBase.metadata.create_all(engine)
        s = SqlEvidenceRepository(Session(engine))
        s.append(
            Evidence(
                evidence_id=f"e{days}",
                company_id="X",
                evidence_type="filing_fact",
                publish_ts=base + timedelta(days=days),
                ingested_at=base + timedelta(days=days),
                confidence_grade="A",
                verification_status="PRIMARY_VERIFIED",
            )
        )
        assert s.latest_as_of("X", base).items == ()
