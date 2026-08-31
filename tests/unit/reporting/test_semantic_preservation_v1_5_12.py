import pytest

from research_os.reporting.document import ResearchCompletenessBlock, ValuationRationaleBlock
from research_os.reporting.markdown_renderer_v1_5_12 import ResearchReportMarkdownRenderer


def test_sensitivity_result_renders_with_material_assumptions_and_model_boundary():
    block = ResearchCompletenessBlock(
        kind="sensitivity_scenarios",
        payload=[
            {
                "driver_id": "raw_material_price",
                "shock_label": "原材料 +5%",
                "affected_metric": "gross_margin",
                "result": -0.02,
                "probability": 0.30,
                "material_assumptions": [
                    {"label": "售价不变", "value": True, "unit": None},
                    {"label": "成本传导比例", "value": 0.60, "unit": "ratio"},
                ],
                "model_boundary": "机械敏感性，不是预测",
                "applicability": "销量与产品结构不变时适用",
                "caveats": ["库存计价时点不变"],
            }
        ],
    )

    text = "\n".join(ResearchReportMarkdownRenderer._render_completeness(block))

    assert "关键假设" in text
    assert "售价不变" in text
    assert "成本传导比例" in text
    assert "机械敏感性，不是预测" in text
    assert "销量与产品结构不变时适用" in text
    assert "库存计价时点不变" in text


def test_analyst_defined_threshold_is_labeled_as_research_warning_line():
    block = ResearchCompletenessBlock(
        kind="monitoring_calendar",
        payload={
            "rules": [
                {
                    "metric": "gross_margin",
                    "operator": "gte",
                    "threshold": 0.25,
                    "frequency": "quarterly",
                    "rationale": "监控修复持续性",
                    "threshold_type": "analyst_defined_monitoring",
                    "threshold_source": "分析师监控策略",
                    "comparison_basis": "单季度披露口径",
                    "applicability": "合并制造业务",
                }
            ],
            "events": [],
        },
    )

    text = "\n".join(ResearchReportMarkdownRenderer._render_completeness(block))

    assert "研究预警线" in text
    assert "分析师监控策略" in text
    assert "单季度披露口径" in text
    assert "合并制造业务" in text


@pytest.mark.parametrize(
    "threshold_type,label",
    (
        ("company_guidance", "公司指引阈值"),
        ("accounting_or_regulatory", "会计或监管阈值"),
        ("industry_benchmark", "行业基准阈值"),
        ("historical_company_benchmark", "公司历史基准阈值"),
        ("analyst_defined_monitoring", "研究预警线"),
        ("contractual", "合同阈值"),
        ("other", "其他来源阈值"),
    ),
)
def test_every_typed_threshold_has_an_investor_facing_label(threshold_type, label):
    block = ResearchCompletenessBlock(
        kind="monitoring_calendar",
        payload={
            "rules": [
                {
                    "metric": "gross_margin",
                    "operator": "gte",
                    "threshold": 0.25,
                    "frequency": "quarterly",
                    "rationale": "monitor recovery",
                    "threshold_type": threshold_type,
                    "threshold_source": "canonical source",
                    "comparison_basis": "quarterly reported basis",
                    "applicability": "manufacturing operations",
                }
            ],
            "events": [],
        },
    )

    text = "\n".join(ResearchReportMarkdownRenderer._render_completeness(block))

    assert label in text
    assert threshold_type not in text


def test_renderer_displays_model_disagreement_without_inventing_a_range():
    block = ValuationRationaleBlock(
        valuation_reconciliation={
            "status": "MODEL_DISAGREEMENT",
            "method": "none",
            "low": None,
            "high": None,
            "reason": "compatible model-implied ranges do not overlap",
        }
    )

    text = "\n".join(ResearchReportMarkdownRenderer._render_valuation_rationale(block))

    assert "模型分歧" in text
    assert "综合估值区间" not in text
    assert "None" not in text


def test_renderer_displays_only_canonical_intersection_values():
    block = ValuationRationaleBlock(
        valuation_reconciliation={
            "status": "INTERSECTION",
            "method": "mathematical_intersection",
            "low": 15.0,
            "high": 18.0,
            "basis": "equity_per_share",
            "currency": "CNY",
            "reason": "compatible model-implied ranges have a non-empty intersection",
        }
    )

    text = "\n".join(ResearchReportMarkdownRenderer._render_valuation_rationale(block))

    assert "15" in text
    assert "18" in text
    assert "数学交集" in text
