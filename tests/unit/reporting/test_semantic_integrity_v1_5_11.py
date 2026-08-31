from datetime import datetime, timezone

from research_os.reporting.document import ValuationRationaleBlock
from research_os.reporting.semantics import DecisionSummaryPresenter
from research_os.reporting.research_view_v1_5_11 import ResearchViewPresenter
from research_os.reporting.markdown_renderer_v1_5_11 import ResearchReportMarkdownRenderer


def test_new_missingness_states_have_explicit_human_semantics():
    presenter = DecisionSummaryPresenter()
    thesis = presenter.semantic("UNRESOLVED", category="thesis_state")
    expectation = presenter.semantic("UNKNOWN", category="expectation_state")

    assert "尚未配置" not in thesis.label
    assert "确认" in thesis.label or "未决" in thesis.label
    assert expectation.label == "市场预期证据不足"


def test_equivalent_ocf_aliases_are_deduplicated_for_display():
    rows = [
        {
            "fact_key": "ocf",
            "label": "经营现金流",
            "value": 100.0,
            "unit": "元",
            "period": "2026H1",
            "period_end": "2026-06-30",
            "evidence_ids": ["ev:ocf"],
        },
        {
            "fact_key": "operating_cash_flow",
            "label": "经营现金流",
            "value": 100.0,
            "unit": "元",
            "period": "2026H1",
            "period_end": "2026-06-30",
            "evidence_ids": ["ev:operating-cash-flow"],
        },
    ]

    deduped = ResearchViewPresenter._deduplicate_financial_facts(rows)

    assert len(deduped) == 1
    assert deduped[0]["fact_key"] in {"ocf", "operating_cash_flow"}
    assert deduped[0]["evidence_ids"] == ["ev:ocf", "ev:operating-cash-flow"]


def test_body_dates_are_human_readable_without_losing_audit_precision():
    value = datetime(2026, 8, 31, 5, 9, 25, tzinfo=timezone.utc)

    assert ResearchReportMarkdownRenderer._body_date(value) == "2026-08-31"
    assert ResearchReportMarkdownRenderer._display_scalar(value) == "2026-08-31T05:09:25+00:00"


def test_null_display_values_never_render_literal_none():
    assert ResearchReportMarkdownRenderer._shown(None) == "—"
    assert "None" not in ResearchReportMarkdownRenderer._shown(None)


def test_valuation_fitness_body_is_categorical_not_fake_precision():
    block = ValuationRationaleBlock(
        valuation_models=[
            {
                "model_id": "dcf",
                "label": "DCF",
                "status": {"label": "适用性中等", "explanation": "预测稳定性有限", "code": "MEDIUM"},
                "score": 0.87654321,
                "explanation": "预测稳定性有限",
            }
        ]
    )

    text = "\n".join(ResearchReportMarkdownRenderer._render_valuation_rationale(block))

    assert "适用性中等" in text
    assert "0.87654321" not in text
    assert "评分" not in text
