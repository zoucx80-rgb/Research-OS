import json
from pathlib import Path

import pytest

from research_os.presentation import HtmlPresentationArtifact, PdfPresentationArtifact
from research_os.acceptance import FieldAcceptanceError


class _DeterministicPdfAdapter:
    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact:
        return PdfPresentationArtifact.from_html(
            html=html,
            renderer_version="professional-pdf-adapter@1.0.0",
            backend_version="semantic-preservation-test-backend@1.0",
            content=b"%PDF-1.7\nsemantic-preservation-field-test",
        )


def _render(case_name: str, tmp_path: Path):
    repository_root = Path(__file__).resolve().parents[3]
    from scripts.render_field_acceptance_v1_5_12 import render_case

    return render_case(
        case_path=(
            repository_root
            / f"tests/fixtures/field_acceptance/v1_5_12/{case_name}.json"
        ),
        output_root=tmp_path,
        repository_root=repository_root,
        pdf_adapter=_DeterministicPdfAdapter(),
    )


def _render_payload(payload: dict, tmp_path: Path):
    from scripts.render_field_acceptance_v1_5_12 import render_case

    case_path = tmp_path / "case.json"
    case_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return render_case(
        case_path=case_path,
        output_root=tmp_path / "output",
        repository_root=Path(__file__).resolve().parents[3],
        pdf_adapter=_DeterministicPdfAdapter(),
    )


def test_v1_5_12_synthetic_case_preserves_all_seven_semantic_boundaries(tmp_path: Path):
    output = _render("manufacturing_semantic_preservation", tmp_path)

    acceptance = output.manifest["acceptance"]
    assert acceptance["presentation"]["status"] == "PASS"
    assert acceptance["semantic_preservation"]["status"] == "PASS", acceptance
    assert acceptance["overall_status"] == "PASS"
    assert output.manifest["versions"]["presenter"] == "professional-research-view@1.7.0"
    assert output.manifest["versions"]["composer"] == "research-report-composer@1.4.0"
    assert output.manifest["versions"]["markdown_renderer"] == "professional-markdown-renderer@1.4.0"

    body = output.bundle.markdown.content.split("## 审计附录", 1)[0]
    for phrase in (
        "技术壁垒有证据",
        "不等同于已实现经济护城河",
        "周期底部未确认",
        "关键假设",
        "模型边界",
        "研究预警线",
        "模型分歧",
        "现金流可见性与预测期不足",
    ):
        assert phrase in body
    assert "综合估值区间" not in body


def test_v1_5_12_steel_superalloy_case_is_pit_safe_and_passes(tmp_path: Path):
    output = _render("300034.SZ", tmp_path)

    acceptance = output.manifest["acceptance"]
    assert acceptance["overall_status"] == "PASS", acceptance
    assert output.manifest["decision_ts"] == "2026-08-30T00:00:00Z"
    assert all(
        item["publish_ts"] <= output.manifest["decision_ts"]
        for item in output.manifest["evidence_provenance"]
    )

    case_path = (
        Path(__file__).resolve().parents[3]
        / "tests/fixtures/field_acceptance/v1_5_12/300034.SZ.json"
    )
    case = json.loads(case_path.read_text(encoding="utf-8"))
    assert case["company"]["security_id"] == "300034.SZ"


def test_optional_missing_caveat_is_recorded_as_warn_without_failing_case(tmp_path: Path):
    source = (
        Path(__file__).resolve().parents[3]
        / "tests/fixtures/field_acceptance/v1_5_12/manufacturing_semantic_preservation.json"
    )
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["case_id"] = "semantic-warning"
    payload["inputs"]["sensitivities"][0]["caveats"] = []

    output = _render_payload(payload, tmp_path)
    acceptance = output.manifest["acceptance"]

    assert acceptance["semantic_preservation"]["status"] == "WARN"
    assert acceptance["overall_status"] == "WARN"
    assert acceptance["semantic_preservation"]["warnings"][0]["layer"]
    assert output.output_dir.joinpath("report.pdf").exists()


def test_presentation_failure_keeps_first_pass_artifacts_and_diagnostic_manifest(
    tmp_path: Path,
):
    source = (
        Path(__file__).resolve().parents[3]
        / "tests/fixtures/field_acceptance/v1_5_12/manufacturing_semantic_preservation.json"
    )
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["case_id"] = "presentation-first-pass-failure"
    payload["acceptance"]["required_body_terms"].append("impossible-required-term")
    case_path = tmp_path / "failed-case.json"
    case_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    output_root = tmp_path / "failed-output"

    from scripts.render_field_acceptance_v1_5_12 import render_case

    with pytest.raises(FieldAcceptanceError, match="required body term missing"):
        render_case(
            case_path=case_path,
            output_root=output_root,
            repository_root=Path(__file__).resolve().parents[3],
            pdf_adapter=_DeterministicPdfAdapter(),
        )

    first_pass = output_root / payload["case_id"]
    assert first_pass.joinpath("report.md").exists()
    assert first_pass.joinpath("report.html").exists()
    assert first_pass.joinpath("report.pdf").exists()
    manifest = json.loads(first_pass.joinpath("manifest.json").read_text(encoding="utf-8"))
    assert manifest["acceptance"]["status"] == "FAIL"
    assert manifest["acceptance"]["layer"] == "presentation"
    assert "required body term missing" in manifest["acceptance"]["errors"][0]
