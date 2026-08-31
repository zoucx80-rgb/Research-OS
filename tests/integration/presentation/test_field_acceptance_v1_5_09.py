from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from research_os.presentation import HtmlPresentationArtifact, PdfPresentationArtifact


class _DeterministicPdfAdapter:
    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact:
        return PdfPresentationArtifact.from_html(
            html=html,
            renderer_version="professional-pdf-adapter@1.0.0",
            backend_version="field-depth-test-backend@1.0",
            content=b"%PDF-1.7\nfield-depth-acceptance-test",
        )


def _case(repository_root: Path) -> dict:
    path = repository_root / "tests/fixtures/field_acceptance/v1_5_08/300034.SZ.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["research_depth_acceptance"] = {
        "required_financial_fact_keys": [
            "revenue",
            "net_profit_parent",
            "margin_change",
            "ocf",
            "capex_cash",
            "ar_end",
        ],
        "required_document_section_ids": [
            "financial-operating-performance",
            "capital-funding",
            "causal-bridge",
            "valuation-rationale",
            "research-gaps",
        ],
        "required_body_terms": [
            "核心财务事实",
            "营业收入",
            "20.53亿元",
            "归母净利润",
            "1.03亿元",
            "毛利率同比下降",
            "-2.66个百分点",
            "资本开支现金支出",
            "4837.29万元",
        ],
        "forbidden_body_terms": [
            "专业研究问题的中文展示尚未配置",
            "存在尚未配置中文说明的研究状态",
        ],
    }
    return payload


def test_field_acceptance_separates_presentation_and_research_depth_status(tmp_path: Path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repository_root))
    from scripts.render_field_acceptance_v1_5_09 import render_case

    case_path = tmp_path / "300034.SZ.json"
    case_path.write_text(
        json.dumps(_case(repository_root), ensure_ascii=False),
        encoding="utf-8",
    )

    output = render_case(
        case_path=case_path,
        output_root=tmp_path / "output",
        repository_root=repository_root,
        pdf_adapter=_DeterministicPdfAdapter(),
    )

    acceptance = output.manifest["acceptance"]
    assert acceptance["presentation"]["status"] == "PASS"
    assert acceptance["research_depth"]["status"] == "PASS"
    assert acceptance["research_depth"]["errors"] == []
    assert acceptance["overall_status"] == "PASS"
    assert output.manifest["versions"]["presenter"] == "professional-research-view@1.4.0"
    assert output.manifest["versions"]["composer"] == "research-report-composer@1.2.0"
    assert output.manifest["versions"]["markdown_renderer"] == "professional-markdown-renderer@1.1.0"


def test_layout_pass_cannot_mask_missing_research_depth(tmp_path: Path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repository_root))
    from scripts.render_field_acceptance_v1_5_09 import render_case

    payload = _case(repository_root)
    payload["research_depth_acceptance"]["required_financial_fact_keys"].append("debt_end")
    case_path = tmp_path / "missing-depth.json"
    case_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    output = render_case(
        case_path=case_path,
        output_root=tmp_path / "output",
        repository_root=repository_root,
        pdf_adapter=_DeterministicPdfAdapter(),
    )

    acceptance = output.manifest["acceptance"]
    assert acceptance["presentation"]["status"] == "PASS"
    assert acceptance["research_depth"]["status"] == "FAIL"
    assert acceptance["overall_status"] == "FAIL"
    assert any("debt_end" in item for item in acceptance["research_depth"]["errors"])


def test_v1_5_09_acceptance_script_supports_direct_cli_execution():
    repository_root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, "scripts/render_field_acceptance_v1_5_09.py", "--help"],
        cwd=repository_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "Render v1.5.09 dual-status field acceptance" in result.stdout
