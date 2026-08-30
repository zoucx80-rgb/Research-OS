from research_os.expectations.models import ExpectationGapResult
from research_os.expectations.surprise import build_expectation_gap


def test_missing_consensus_does_not_fabricate_gap():
    assert build_expectation_gap(metric="revenue", market=None, os_view=120.0) is None


def test_numeric_gap_preserves_lineage_and_quality():
    result = build_expectation_gap(
        metric="revenue",
        market={
            "value": 100.0,
            "source_count": 3,
            "source_quality": 0.8,
            "age_days": 12,
            "post_event_consensus": True,
            "evidence_ids": ["consensus-1"],
        },
        os_view=120.0,
        os_evidence_ids=["forecast-1"],
    )
    assert isinstance(result, ExpectationGapResult)
    assert result.direction == "ABOVE"
    assert result.magnitude == 20.0
    assert result.source_count == 3
    assert result.source_quality == 0.8
    assert result.post_event_consensus is True
    assert result.evidence_ids == ["consensus-1", "forecast-1"]


def test_thin_or_pre_event_consensus_is_qualified():
    result = build_expectation_gap(
        metric="net_profit",
        market={
            "value": 10.0,
            "source_count": 1,
            "source_quality": 0.6,
            "age_days": 30,
            "post_event_consensus": False,
            "evidence_ids": ["thin-1"],
        },
        os_view=11.0,
    )
    assert result is not None
    assert result.direction == "ABOVE"
    assert result.limitation


def test_directional_gap_does_not_invent_numeric_magnitude():
    result = build_expectation_gap(
        metric="gross_margin",
        market={
            "direction": "UP",
            "source_count": 2,
            "source_quality": 0.7,
            "post_event_consensus": True,
            "evidence_ids": ["directional-1"],
        },
        os_view_direction="DOWN",
    )
    assert result is not None
    assert result.direction == "BELOW"
    assert result.magnitude is None
