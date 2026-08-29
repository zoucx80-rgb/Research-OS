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


def test_beat_without_expectation_baseline_fails():
    m = _load("research_os.expectations.validation")
    result = m.ExpectationEvidenceValidator().assess(
        conclusion="beat expectations",
        evidence=None,
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
    )
    assert result.status == "FAIL"


def test_missing_baseline_without_claim_is_insufficient_evidence():
    m = _load("research_os.expectations.validation")
    result = m.ExpectationEvidenceValidator().assess(
        conclusion=None,
        evidence=None,
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
    )
    assert result.status == "INSUFFICIENT_EVIDENCE"


def test_future_expectation_vintage_fails_pit_validation():
    models = _load("research_os.expectations.models")
    validation = _load("research_os.expectations.validation")
    evidence = models.ExpectationEvidence(
        expectation_source="broker consensus",
        expectation_publish_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        expectation_period="2026H1",
        metric="net_profit",
        expected_value=10.0,
        actual_value=11.0,
        surprise=1.0,
        vintage="2026-08-30",
    )
    result = validation.ExpectationEvidenceValidator().assess(
        conclusion="beat expectations",
        evidence=evidence,
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
    )
    assert result.status == "FAIL"
