import importlib
import importlib.util
from datetime import datetime, timezone


def _load(name: str):
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    assert spec is not None, f"missing required module {name}"
    return importlib.import_module(name)


def test_used_interim_report_cannot_be_next_verification_event():
    m = _load("research_os.events.validation")
    decision_ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    event = m.NextVerificationEvent(
        event_name="2026H1 interim report",
        event_time=decision_ts,
        evidence_ids=["ev:2026H1"],
    )
    result = m.NextVerificationEventValidator().validate(
        event,
        reference_time=decision_ts,
        used_evidence_ids=["ev:2026H1"],
    )
    assert result.status == "FAIL"


def test_future_unused_event_passes_temporal_gate():
    m = _load("research_os.events.validation")
    decision_ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    event = m.NextVerificationEvent(
        event_name="2026Q3 report",
        event_time=datetime(2026, 10, 30, tzinfo=timezone.utc),
        evidence_ids=[],
    )
    result = m.NextVerificationEventValidator().validate(
        event, reference_time=decision_ts, used_evidence_ids=[]
    )
    assert result.status == "PASS"
