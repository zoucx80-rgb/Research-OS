from datetime import datetime, timezone

from research_os.domain.evidence import Evidence
from research_os.thesis.semantic_signals import GrowthComparisonRule
from research_os.thesis.semantic_service_v1_5_11 import SemanticThesisService


def metric(name, value, *, comparison_basis=None, metric_kind=None):
    return Evidence(
        evidence_id=f"ev:{name}",
        company_id="GENERIC",
        evidence_type="calculated_metric",
        source_table=name,
        value=value,
        publish_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
        comparison_basis=comparison_basis,
        metric_kind=metric_kind,
    )


def test_negative_margin_change_uses_downward_not_improvement_language():
    result = SemanticThesisService().assess_signals(
        [metric("margin_change", -0.025, comparison_basis="YOY_PERIOD", metric_kind="FLOW_RATIO")]
    )
    signal = next(item for item in result.signals if item.metric == "margin_change")
    assert signal.direction == "NEGATIVE"
    assert signal.semantic_label == "毛利率下降"
    assert "改善" not in signal.semantic_label
    assert "毛利率下降" in result.negative_signals


def test_positive_margin_change_uses_improvement_language():
    result = SemanticThesisService().assess_signals(
        [metric("margin_change", 0.015, comparison_basis="YOY_PERIOD", metric_kind="FLOW_RATIO")]
    )
    signal = next(item for item in result.signals if item.metric == "margin_change")
    assert signal.direction == "POSITIVE"
    assert signal.semantic_label == "毛利率改善"
    assert "毛利率改善" in result.positive_signals


def test_stock_change_receivables_vs_flow_yoy_revenue_is_not_comparable():
    rule = GrowthComparisonRule(
        rule_id="receivables-vs-revenue",
        left_metric="ar_growth",
        right_metric="revenue_growth",
        spread_threshold=0.10,
        adverse_label="应收增速显著快于收入",
    )
    result = SemanticThesisService(comparison_rules=(rule,)).assess_signals(
        [
            metric("ar_growth", 0.60, comparison_basis="END_VS_BEGIN", metric_kind="STOCK_RATIO"),
            metric("revenue_growth", 0.13, comparison_basis="YOY_PERIOD", metric_kind="FLOW_RATIO"),
        ]
    )
    comparison = result.comparisons[0]
    assert comparison.status == "NOT_COMPARABLE"
    assert "应收增速显著快于收入" not in result.negative_signals


def test_compatible_yoy_growth_comparison_can_emit_explicit_rule_signal():
    rule = GrowthComparisonRule(
        rule_id="receivables-vs-revenue",
        left_metric="ar_growth",
        right_metric="revenue_growth",
        spread_threshold=0.10,
        adverse_label="应收增速显著快于收入",
    )
    result = SemanticThesisService(comparison_rules=(rule,)).assess_signals(
        [
            metric("ar_growth", 0.35, comparison_basis="YOY_PERIOD", metric_kind="FLOW_RATIO"),
            metric("revenue_growth", 0.12, comparison_basis="YOY_PERIOD", metric_kind="FLOW_RATIO"),
        ]
    )
    comparison = result.comparisons[0]
    assert comparison.status == "COMPARABLE"
    assert "应收增速显著快于收入" in result.negative_signals
    emitted = next(item for item in result.signals if item.reason_code == "EXPLICIT_GROWTH_SPREAD_RULE")
    assert emitted.direction == "NEGATIVE"
    assert set(emitted.evidence_ids) == {"ev:ar_growth", "ev:revenue_growth"}
