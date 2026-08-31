from datetime import datetime, timezone

import pytest

from research_os.completeness import (
    CashFlowQualityInput,
    ConsensusObservation,
    FinancialSeriesPoint,
    FinancialTimeSeries,
    MonitoringRule,
    OperatingObservation,
    PriorRunReviewInput,
    build_cash_flow_quality_bridge,
    build_consensus_distribution,
    build_prior_run_review,
)


def ts(day: int) -> datetime:
    return datetime(2026, 8, day, tzinfo=timezone.utc)


def test_completeness_models_are_immutable_and_preserve_missing_values():
    observation = OperatingObservation(
        category="capacity",
        metric_id="capacity_utilization",
        value=None,
        period="2026H1",
        evidence_ids=("ev:capacity",),
    )
    assert observation.value is None
    assert observation.evidence_ids == ("ev:capacity",)
    with pytest.raises(Exception):
        observation.value = 0.8

    series = FinancialTimeSeries(
        metric_id="revenue",
        unit="CNY",
        points=(
            FinancialSeriesPoint(
                period="2025Q4",
                period_end=ts(1),
                value=100.0,
                evidence_ids=("ev:q4",),
            ),
            FinancialSeriesPoint(
                period="2026Q1",
                period_end=ts(2),
                value=None,
                evidence_ids=(),
            ),
        ),
    )
    assert [point.value for point in series.points] == [100.0, None]


def test_cash_flow_bridge_only_calculates_simplified_fcf_when_inputs_exist():
    complete = build_cash_flow_quality_bridge(
        CashFlowQualityInput(
            net_profit=100.0,
            operating_cash_flow=140.0,
            working_capital_contribution=30.0,
            other_adjustments=10.0,
            capex_cash=50.0,
            unit="CNY",
            evidence_ids=("ev:np", "ev:ocf", "ev:capex"),
        )
    )
    assert complete.simplified_fcf == 90.0
    assert complete.working_capital_contribution == 30.0
    assert complete.methodology == "simplified_fcf_not_fcff"

    incomplete = build_cash_flow_quality_bridge(
        CashFlowQualityInput(
            net_profit=100.0,
            operating_cash_flow=140.0,
            capex_cash=None,
            unit="CNY",
        )
    )
    assert incomplete.simplified_fcf is None
    assert incomplete.working_capital_contribution is None


def test_consensus_distribution_is_pit_safe_and_single_source_is_not_broad_consensus():
    decision_ts = ts(20)
    single = build_consensus_distribution(
        observations=(
            ConsensusObservation(
                source_id="broker-a",
                publish_ts=ts(10),
                forecast_period="2027",
                metric="net_profit",
                value=3.0,
            ),
        ),
        decision_ts=decision_ts,
        metric="net_profit",
        forecast_period="2027",
    )
    assert single.source_count == 1
    assert single.breadth == "single_source"
    assert single.low == single.median == single.high == 3.0

    broad = build_consensus_distribution(
        observations=(
            ConsensusObservation(source_id="a", publish_ts=ts(10), forecast_period="2027", metric="net_profit", value=3.0),
            ConsensusObservation(source_id="b", publish_ts=ts(11), forecast_period="2027", metric="net_profit", value=5.0),
            ConsensusObservation(source_id="c", publish_ts=ts(12), forecast_period="2027", metric="net_profit", value=4.0),
        ),
        decision_ts=decision_ts,
        metric="net_profit",
        forecast_period="2027",
    )
    assert broad.source_count == 3
    assert broad.breadth == "multi_source"
    assert (broad.low, broad.median, broad.high) == (3.0, 4.0, 5.0)
    assert broad.dispersion == 2.0

    with pytest.raises(ValueError, match="post-decision"):
        build_consensus_distribution(
            observations=(
                ConsensusObservation(
                    source_id="future",
                    publish_ts=ts(25),
                    forecast_period="2027",
                    metric="net_profit",
                    value=6.0,
                ),
            ),
            decision_ts=decision_ts,
            metric="net_profit",
            forecast_period="2027",
        )


def test_prior_run_review_does_not_score_unknown_predictions_or_actuals():
    review = build_prior_run_review(
        items=(
            PriorRunReviewInput(
                item_id="growth",
                prior_statement="growth should accelerate",
                metric="revenue_growth",
                period="2026H1",
                predicted_value=0.2,
                actual_value=0.25,
                tolerance=0.1,
            ),
            PriorRunReviewInput(
                item_id="margin",
                prior_statement="margin should recover",
                metric="gross_margin",
                period="2026H1",
                predicted_value=0.3,
                actual_value=None,
                tolerance=0.02,
            ),
        )
    )
    assert review.items[0].status == "HIT"
    assert review.items[0].error == pytest.approx(0.05)
    assert review.items[1].status == "UNKNOWN"
    assert review.items[1].error is None
    assert review.scored_count == 1


def test_monitoring_threshold_is_explicit_input_not_methodology_constant():
    rule = MonitoringRule(
        rule_id="margin-floor",
        metric="segment_gross_margin",
        operator="lt",
        threshold=0.22,
        frequency="quarterly",
        rationale="analyst-defined monitoring threshold",
        source_type="analyst_assumption",
        assumption_ids=("assumption:margin-floor",),
    )
    assert rule.threshold == 0.22
    assert rule.source_type == "analyst_assumption"
    assert rule.assumption_ids == ("assumption:margin-floor",)
