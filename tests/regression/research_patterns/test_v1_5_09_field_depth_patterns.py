from __future__ import annotations

import json
from pathlib import Path

from research_os.presentation import HtmlPresentationArtifact, PdfPresentationArtifact


class _DeterministicPdfAdapter:
    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact:
        return PdfPresentationArtifact.from_html(
            html=html,
            renderer_version="professional-pdf-adapter@1.0.0",
            backend_version="v1.5.09-depth-regression@1.0",
            content=b"%PDF-1.7\nv1.5.09-depth-regression",
        )


def _render(case_path: Path, tmp_path: Path, repository_root: Path):
    from scripts.render_field_acceptance_v1_5_09 import render_case

    return render_case(
        case_path=case_path,
        output_root=tmp_path,
        repository_root=repository_root,
        pdf_adapter=_DeterministicPdfAdapter(),
    )


def test_v1_5_09_three_company_depth_fixtures_are_permanent_and_all_pass(tmp_path: Path):
    repository_root = Path(__file__).resolve().parents[3]
    fixture_dir = repository_root / "tests/fixtures/field_acceptance/v1_5_09"
    cases = sorted(fixture_dir.glob("*.json"))

    assert [path.stem for path in cases] == ["001287.SZ", "300034.SZ", "301073.SZ"]

    outputs = {
        path.stem: _render(path, tmp_path / path.stem, repository_root)
        for path in cases
    }
    for output in outputs.values():
        acceptance = output.manifest["acceptance"]
        assert acceptance["presentation"]["status"] == "PASS"
        assert acceptance["research_depth"]["status"] == "PASS"
        assert acceptance["overall_status"] == "PASS"
        assert output.view.presentation_version == "professional-research-view@1.4.0"
        assert output.document.composition_version == "research-report-composer@1.2.0"
        assert output.bundle.markdown.renderer_version == "professional-markdown-renderer@1.1.0"


def test_manufacturing_depth_exposes_scale_margin_pressure_and_working_capital_tension(tmp_path: Path):
    repository_root = Path(__file__).resolve().parents[3]
    output = _render(
        repository_root / "tests/fixtures/field_acceptance/v1_5_09/300034.SZ.json",
        tmp_path,
        repository_root,
    )
    body = output.bundle.markdown.content.split("## 审计附录", 1)[0]

    for term in (
        "20.53亿元",
        "1.03亿元",
        "4.39亿元",
        "19.57亿元",
        "60.28%",
        "16.18亿元",
        "-11.60%",
        "3.19亿元",
        "4837.29万元",
        "毛利率同比下降",
        "-2.66个百分点",
    ):
        assert term in body
    for invented in ("订单饱满", "产能利用率改善", "资格认证完成"):
        assert invented not in body


def test_distributor_depth_keeps_cash_debt_and_receivable_transfer_semantics_distinct(tmp_path: Path):
    repository_root = Path(__file__).resolve().parents[3]
    output = _render(
        repository_root / "tests/fixtures/field_acceptance/v1_5_09/001287.SZ.json",
        tmp_path,
        repository_root,
    )
    body = output.bundle.markdown.content.split("## 审计附录", 1)[0]

    for term in (
        "735.56亿元",
        "164.19%",
        "20.93亿元",
        "2.85%",
        "-175.00亿元",
        "163.92亿元",
        "61.04亿元",
        "经营现金流为负",
        "债务融资驱动",
        "终止确认应收款",
        "融资成本",
    ):
        assert term in body
    assert "保理余额（债务）" not in body
    assert "终止确认应收款（债务）" not in body


def test_lease_heavy_hospitality_depth_is_explicit_about_capability_and_lease_limits(tmp_path: Path):
    repository_root = Path(__file__).resolve().parents[3]
    output = _render(
        repository_root / "tests/fixtures/field_acceptance/v1_5_09/301073.SZ.json",
        tmp_path,
        repository_root,
    )
    body = output.bundle.markdown.content.split("## 审计附录", 1)[0]

    for term in (
        "3.31亿元",
        "1.41%",
        "950.37万元",
        "1.23亿元",
        "酒店与住宿服务",
        "租赁项目具有重要性",
        "当前版本没有兼容的行业策略插件",
        "研究缺口分类",
    ):
        assert term in body
    for invented in (
        "RevPAR",
        "ADR",
        "OCC",
        "同店增长",
        "成熟店曲线",
        "轻资产",
        "低资本占用",
        "现金转化极佳",
    ):
        assert invented not in body


def test_v1_5_09_fixture_contracts_remain_pit_and_lineage_explicit():
    repository_root = Path(__file__).resolve().parents[3]
    fixture_dir = repository_root / "tests/fixtures/field_acceptance/v1_5_09"

    for path in sorted(fixture_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["decision_ts"] == "2026-08-30T00:00:00Z"
        assert payload["research_depth_acceptance"]["required_financial_fact_keys"]
        for item in payload["evidence"]:
            publish_ts = item.get("publish_ts") or payload["evidence_defaults"]["publish_ts"]
            assert publish_ts <= payload["decision_ts"]
            assert item["evidence_id"].startswith("ev:")
