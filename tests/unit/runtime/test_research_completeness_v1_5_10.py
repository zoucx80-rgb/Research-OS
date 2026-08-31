from datetime import datetime, timezone

from research_os.completeness import (
    CashFlowQualityInput,
    ConsensusObservation,
    FinancialSeriesPoint,
    FinancialTimeSeries,
    MonitoringRule,
    OperatingObservation,
    PeerComparableObservation,
    PriorRunReviewInput,
    SensitivityCase,
    VerificationCalendarEvent,
)
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.research_completeness import ResearchCompletenessModule
from research_os.runtime.state import ResearchStateView


DECISION_TS = datetime(2026, 8, 31, tzinfo=timezone.utc)


class Context:
    decision_ts = DECISION_TS


def test_completeness_module_emits_only_explicit_research_artifacts_plus_methodology():
    inputs = ResearchInputs(
        operating_observations=(
            OperatingObservation(
                category="segment",
                metric_id="segment_revenue_growth",
                value=0.25,
                period="2026H1",
                segment_label="new_alloy",
                evidence_ids=("ev:segment",),
            ),
        ),
        financial_time_series=(
            FinancialTimeSeries(
                metric_id="revenue",
                unit="CNY",
                points=(
                    FinancialSeriesPoint(period="2026Q1", period_end=datetime(2026, 3, 31, tzinfo=timezone.utc), value=100.0, evidence_ids=("ev:q1",)),
                    FinancialSeriesPoint(period="2026Q2", period_end=datetime(2026, 6, 30, tzinfo=timezone.utc), value=120.0, evidence_ids=("ev:q2",)),
                ),
            ),
        ),
        cash_flow_quality_input=CashFlowQualityInput(
            net_profit=10.0,
            operating_cash_flow=15.0,
            capex_cash=4.0,
            evidence_ids=("ev:cash",),
        ),
        consensus_observations=(
            ConsensusObservation(source_id="broker-a", publish_ts=datetime(2026, 8, 20, tzinfo=timezone.utc), forecast_period="2027", metric="net_profit", value=20.0, evidence_ids=("ev:a",)),
            ConsensusObservation(source_id="broker-b", publish_ts=datetime(2026, 8, 21, tzinfo=timezone.utc), forecast_period="2027", metric="net_profit", value=24.0, evidence_ids=("ev:b",)),
        ),
        peer_comparables=(
            PeerComparableObservation(
                peer_id="peer-1",
                peer_role="direct_competitor",
                metric="segment_gross_margin",
                value=0.3,
                period="2026H1",
                period_type="H1",
                scope="segment",
                accounting_definition="reported_gross_margin",
                frequency="interim",
                share_count_convention="not_applicable",
                business_model_interpretation="manufacturing",
                product_or_segment="high_temperature_alloy",
                evidence_ids=("ev:peer",),
            ),
        ),
        sensitivities=(
            SensitivityCase(
                case_id="nickel-up",
                driver_id="nickel_price",
                base_value=100.0,
                shock_label="+10%",
                shock_value=0.1,
                affected_metric="gross_margin",
                result=0.24,
                formula_version="analyst-sensitivity@1",
                assumption_ids=("assumption:nickel",),
            ),
        ),
        monitoring_rules=(
            MonitoringRule(
                rule_id="margin-floor",
                metric="segment_gross_margin",
                operator="lt",
                threshold=0.22,
                frequency="quarterly",
                rationale="analyst monitoring threshold",
                source_type="analyst_assumption",
                assumption_ids=("assumption:margin-floor",),
            ),
        ),
        verification_calendar=(
            VerificationCalendarEvent(
                event_id="q3",
                label="Q3 report",
                event_type="financial_report",
                due_ts=datetime(2026, 10, 31, tzinfo=timezone.utc),
                status="scheduled",
                information_value="validate margin and cash conversion",
            ),
        ),
        prior_run_review_items=(
            PriorRunReviewInput(
                item_id="growth",
                prior_statement="revenue growth remains positive",
                metric="revenue_growth",
                period="2026H1",
                predicted_value=0.1,
                actual_value=0.13,
                tolerance=0.05,
                actual_evidence_ids=("ev:actual",),
            ),
        ),
    )
    result = ResearchCompletenessModule(inputs=inputs).run(Context(), ResearchStateView({}))

    assert result.status == "PASS"
    assert set(result.artifacts) == {
        "research.operating_evidence",
        "financial.time_series",
        "cash_flow.quality_bridge",
        "expectation.consensus_distribution",
        "peers.comparables",
        "scenario.sensitivities",
        "monitoring.rules",
        "monitoring.verification_calendar",
        "monitoring.prior_run_review",
        "methodology.disclosure",
    }
    assert result.artifacts["cash_flow.quality_bridge"].simplified_fcf == 11.0
    assert result.artifacts["expectation.consensus_distribution"][0].breadth == "multi_source"
    assert result.artifacts["monitoring.prior_run_review"].hit_count == 1
    assert "simplified FCF" in result.artifacts["methodology.disclosure"]["cash_flow_methodology"]
    assert "ev:segment" in result.evidence_ids
    assert "assumption:nickel" not in result.evidence_ids


def test_completeness_module_does_not_fabricate_optional_artifacts_for_empty_inputs():
    result = ResearchCompletenessModule(inputs=ResearchInputs()).run(Context(), ResearchStateView({}))

    assert result.status == "PASS"
    assert set(result.artifacts) == {"methodology.disclosure"}
    disclosure = result.artifacts["methodology.disclosure"]
    assert disclosure["pit_rule"] == "publish_ts <= decision_ts"
    assert disclosure["threshold_policy"] == "monitoring thresholds are explicit inputs, not universal constants"


def test_completeness_module_is_optional_for_completion_and_declares_all_capabilities():
    module = ResearchCompletenessModule(inputs=ResearchInputs())
    assert module.spec.module_id == "research_completeness"
    assert module.spec.module_version == "1.0.0"
    assert module.spec.required_for_completion is False
    assert "financial.time_series" in module.spec.provides
    assert "methodology.disclosure" in module.spec.provides
