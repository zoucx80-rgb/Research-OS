from __future__ import annotations

from pathlib import Path

from research_os.presentation import HtmlPresentationArtifact, PdfPresentationArtifact


class _DeterministicPdfAdapter:
    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact:
        return PdfPresentationArtifact.from_html(
            html=html,
            renderer_version="professional-pdf-adapter@1.0.0",
            backend_version="v1.5.10-completeness-regression@1.0",
            content=b"%PDF-1.7\nv1.5.10-completeness-regression",
        )


def test_manufacturing_completeness_pattern_is_generic_pit_safe_and_decision_useful(tmp_path: Path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repository_root))
    from scripts.render_field_acceptance_v1_5_10 import render_case

    case_path = repository_root / "tests/fixtures/field_acceptance/v1_5_10/manufacturing_completeness.json"
    output = render_case(
        case_path=case_path,
        output_root=tmp_path,
        repository_root=repository_root,
        pdf_adapter=_DeterministicPdfAdapter(),
    )

    body = output.bundle.markdown.content.split("## 审计附录", 1)[0]
    section_ids = [section.section_id for section in output.document.sections]

    for section_id in (
        "financial-trends",
        "operating-evidence",
        "cash-flow-quality",
        "peer-comparison",
        "consensus-dispersion",
        "sensitivity-scenarios",
        "monitoring-calendar",
        "prior-run-review",
        "methodology-disclosure",
    ):
        assert section_id in section_ids

    for term in (
        "财务趋势",
        "经营证据",
        "高端产品线",
        "在手订单",
        "产能利用率",
        "子公司A",
        "子公司B",
        "现金流质量",
        "simplified FCF",
        "不是 FCFF",
        "同行与产品线比较",
        "一致预期分布",
        "多来源",
        "敏感性与情景",
        "原材料价格 +10%",
        "监控规则与验证日历",
        "上期判断回顾",
        "方法说明",
    ):
        assert term in body

    assert "ev:synthetic:" not in body
    assert "assumption:synthetic:" not in body
    assert output.view.presentation_version == "professional-research-view@1.5.0"
    assert output.document.composition_version == "research-report-composer@1.3.0"
    assert output.bundle.markdown.renderer_version == "professional-markdown-renderer@1.2.0"

    assert output.result.artifacts["cash_flow.quality_bridge"].working_capital_contribution is not None
    consensus = output.result.artifacts["expectation.consensus_distribution"]
    assert consensus and consensus[0].breadth == "multi_source"
    assert output.result.artifacts["monitoring.prior_run_review"].scored_count >= 1


def test_v1_5_10_fixture_uses_no_real_validation_company_identity():
    repository_root = Path(__file__).resolve().parents[3]
    text = (
        repository_root
        / "tests/fixtures/field_acceptance/v1_5_10/manufacturing_completeness.json"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "300034",
        "001287",
        "301073",
        "钢研高纳",
        "中电港",
        "君亭酒店",
    ):
        assert forbidden not in text
