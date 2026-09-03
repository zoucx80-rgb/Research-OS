from datetime import datetime, timezone
from research_os.domain.enums import ConfidenceGrade, VerificationStatus
from research_os.domain.evidence import Evidence


def test_evidence_keeps_period_and_publish_time_separate():
    e = Evidence(
        evidence_id="e1",
        company_id="001287.SZ",
        evidence_type="filing_fact",
        period_end="2026-06-30",
        publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 25, 1, tzinfo=timezone.utc),
        value=735.56,
        unit="CNY_100M",
        confidence_grade=ConfidenceGrade.A,
        verification_status=VerificationStatus.PRIMARY_VERIFIED,
    )
    assert e.period_end.isoformat() == "2026-06-30"
    assert e.publish_ts.date().isoformat() == "2026-08-25"


def test_evidence_is_immutable():
    e = Evidence(
        evidence_id="e1",
        company_id="X",
        evidence_type="filing_fact",
        publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
    )
    try:
        e.value = 3
    except Exception:
        pass
    else:
        raise AssertionError("Evidence must be frozen")
