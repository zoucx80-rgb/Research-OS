from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from research_os.domain.evidence import Evidence
from research_os.storage.models import Base, EvidenceStore


def test_evidence_store_round_trips_raw_normalized_period_and_version_lineage():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    store = EvidenceStore(Session(engine))
    evidence = Evidence(
        evidence_id="lineage-1",
        company_id="001287.SZ",
        evidence_type="filing_fact",
        period_end="2026-06-30",
        period="2026H1",
        publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 25, 1, tzinfo=timezone.utc),
        value=21.24,
        raw_value="21.24 亿元",
        normalized_value=2_124_000_000.0,
        unit="亿元",
        scope="consolidated",
        version="reported",
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
    )
    store.append(evidence)
    restored = store.latest_as_of("001287.SZ", datetime(2026, 8, 29, tzinfo=timezone.utc))[0]
    assert restored.raw_value == "21.24 亿元"
    assert restored.normalized_value == 2_124_000_000.0
    assert restored.period == "2026H1"
    assert restored.version == "reported"
