from datetime import datetime, timezone

from research_os.domain.evidence import Evidence
from research_os.drivers.graph import DriverGraph
from research_os.thesis.semantic_service_v1_5_11 import SemanticThesisService
from research_os.thesis.semantic_signals import GrowthComparisonRule


def _metric(name, value, *, basis=None, kind=None):
    return Evidence(
        evidence_id=f"ev:generic:{name}",
        company_id="GENERIC-MFG",
        evidence_type="calculated_metric",
        source_table=name,
        value=value,
        publish_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
        comparison_basis=basis,
        metric_kind=kind,
    )


def test_generic_mixed_manufacturing_case_is_directionally_safe_and_unresolved():
    rule = GrowthComparisonRule(
        rule_id="receivables-vs-revenue",
        left_metric="ar_growth",
        right_metric="revenue_growth",
        spread_threshold=0.10,
        adverse_label="应收增速显著快于收入",
    )
    evidence = [
        _metric("revenue_growth", 0.12, basis="YOY_PERIOD", kind="FLOW_RATIO"),
        _metric("margin_change", -0.02, basis="YOY_PERIOD", kind="FLOW_RATIO"),
        _metric("ar_growth", 0.40, basis="END_VS_BEGIN", kind="STOCK_RATIO"),
        _metric("ocf", 220.0),
    ]
    service = SemanticThesisService(comparison_rules=(rule,))
    assessment = service.assess_signals(evidence)

    margin = next(item for item in assessment.signals if item.metric == "margin_change")
    assert margin.direction == "NEGATIVE"
    assert margin.semantic_label == "毛利率下降"
    assert "改善" not in margin.semantic_label
    assert assessment.comparisons[0].status == "NOT_COMPARABLE"
    assert "应收增速显著快于收入" not in assessment.negative_signals

    graph = DriverGraph.build("GENERIC-MFG", ["manufacturing"], evidence)
    thesis = service.evaluate("GENERIC-MFG", evidence, graph)[0]
    assert thesis.status == "unresolved"
    assert thesis.falsifiers == []
    assert thesis.resolution_conditions
    assert thesis.conviction_up_conditions
    assert thesis.deterioration_conditions


def test_generic_comparable_yoy_case_allows_only_explicit_rule_conclusion():
    rule = GrowthComparisonRule(
        rule_id="receivables-vs-revenue",
        left_metric="ar_growth",
        right_metric="revenue_growth",
        spread_threshold=0.10,
        adverse_label="应收增速显著快于收入",
    )
    assessment = SemanticThesisService(comparison_rules=(rule,)).assess_signals(
        [
            _metric("ar_growth", 0.35, basis="YOY_PERIOD", kind="FLOW_RATIO"),
            _metric("revenue_growth", 0.12, basis="YOY_PERIOD", kind="FLOW_RATIO"),
        ]
    )
    assert assessment.comparisons[0].status == "COMPARABLE"
    assert "应收增速显著快于收入" in assessment.negative_signals
