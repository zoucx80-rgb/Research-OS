from __future__ import annotations

from datetime import date
from decimal import Decimal

from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.reporting.projectors import project_artifact
from research_os.sufficiency.models import (
    DomainSufficiencyAssessment,
    MaterialResearchGap,
    ResearchSufficiencyAssessment,
)
from research_os.temporal.models import FinancialTemporalAnalysis, MetricTemporalAssessment


def test_temporal_projector_displays_canonical_yoy_without_recalculation() -> None:
    temporal = FinancialTemporalAnalysis(
        domain_status="SUPPORTED",
        assessments=(
            MetricTemporalAssessment(
                metric_id="revenue",
                unit="CNY",
                period_kind="FLOW",
                accounting_scope=AccountingScope(consolidation="consolidated"),
                comparison_basis="YOY_PERIOD",
                latest_period=ReportingPeriod(
                    period_type="FY",
                    period_start=date(2025, 1, 1),
                    period_end=date(2025, 12, 31),
                    period_days=365,
                    is_cumulative=True,
                ),
                point_count=2,
                comparable_point_count=2,
                temporal_span_days=365,
                yoy_change=Decimal("0.10"),
                trend_state="RISING",
                turning_point_state="NOT_OBSERVED",
                comparison_status="PASS",
            ),
        ),
        temporal_coverage="SUFFICIENT",
    )

    projected = project_artifact("financial.temporal_analysis", temporal)

    assert projected.section_id == "financial"
    assert projected.audit_only is False
    assert projected.payload["时序覆盖"] == "充分"
    assert projected.payload["指标趋势"][0] == {
        "指标": "营业收入",
        "报告期": "2025-12-31",
        "期间口径": "流量",
        "比较口径": "同比同口径",
        "可比数据点": 2,
        "同比变化": "10.00%",
        "环比变化": "—",
        "滚动十二个月": "—",
        "趋势": "上升",
        "拐点": "未观察到",
        "比较状态": "通过",
        "异常": [],
        "不足原因": [],
    }


def test_temporal_projector_preserves_missing_comparison_basis() -> None:
    temporal = FinancialTemporalAnalysis(
        assessments=(
            MetricTemporalAssessment(
                metric_id="revenue",
                unit="CNY",
                point_count=1,
                comparable_point_count=0,
                comparison_status="INSUFFICIENT_EVIDENCE",
                reason_codes=("COMPARISON_BASIS_REQUIRED",),
            ),
        ),
    )

    projected = project_artifact("financial.temporal_analysis", temporal)

    row = projected.payload["指标趋势"][0]
    assert row["比较口径"] == "—"
    assert row["报告期"] == "—"
    assert row["不足原因"] == ["缺少明确比较口径"]


def test_sufficiency_projector_exposes_known_unknown_and_upgrade_evidence() -> None:
    gap = MaterialResearchGap(
        gap_key="financial_temporal:gross_margin:INSUFFICIENT_COMPARABLE_POINTS",
        domain_id="financial_temporal",
        reason_code="INSUFFICIENT_COMPARABLE_POINTS",
        description="Comparable temporal evidence for gross_margin is unresolved.",
        required_evidence=(
            "comparable gross_margin period",
            "explicit comparison basis",
            "revision-bound lineage",
        ),
    )
    sufficiency = ResearchSufficiencyAssessment(
        overall_status="INSUFFICIENT_EVIDENCE",
        domains=(
            DomainSufficiencyAssessment(
                domain_id="financial_temporal",
                coverage="PARTIAL",
                evidence_quality="COMPLETE",
                temporal_coverage="MISSING",
                benchmark_coverage="NOT_APPLICABLE",
                peer_coverage="NOT_APPLICABLE",
                model_executability="NOT_APPLICABLE",
                known_items=("observation:revenue",),
                unknown_items=("comparable_trend:gross_margin",),
                why_unknown=("gross_margin:INSUFFICIENT_COMPARABLE_POINTS",),
                upgrade_evidence_requirements=(
                    "add a comparable gross_margin period with explicit basis and revision-bound lineage",
                ),
                material_gaps=(gap,),
            ),
        ),
        blocking_gap_keys=(gap.gap_key,),
    )

    projected = project_artifact("research.sufficiency", sufficiency)

    assert projected.section_id == "readiness"
    assert projected.audit_only is False
    domain = projected.payload["领域"][0]
    assert domain["领域"] == "财务跨期分析"
    assert domain["覆盖"] == "部分"
    assert domain["证据质量"] == "完整"
    assert domain["跨期覆盖"] == "缺失"
    assert domain["基准覆盖"] == "不适用"
    assert domain["已知"] == ["已观察：营业收入"]
    assert domain["未知"] == ["可比趋势：毛利率"]
    assert domain["未知原因"] == ["毛利率：可比数据点不足"]
    assert domain["升级所需证据"]
    assert domain["重大缺口"][0]["所需证据"]
    text = repr(projected.payload)
    assert "gross_margin" not in text
    assert "INSUFFICIENT_COMPARABLE_POINTS" not in text
