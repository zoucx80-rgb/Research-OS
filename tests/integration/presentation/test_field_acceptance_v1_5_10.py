from __future__ import annotations

import json
from pathlib import Path

from research_os.presentation import HtmlPresentationArtifact, PdfPresentationArtifact


class _DeterministicPdfAdapter:
    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact:
        return PdfPresentationArtifact.from_html(
            html=html,
            renderer_version="professional-pdf-adapter@1.0.0",
            backend_version="v1.5.10-completeness-test@1.0",
            content=b"%PDF-1.7\nv1.5.10-completeness-test",
        )


def _fixture(repository_root: Path) -> Path:
    return repository_root / "tests/fixtures/field_acceptance/v1_5_10/manufacturing_completeness.json"


def _render(case_path: Path, output_root: Path, repository_root: Path, monkeypatch):
    monkeypatch.syspath_prepend(str(repository_root))
    from scripts.render_field_acceptance_v1_5_10 import render_case

    return render_case(
        case_path=case_path,
        output_root=output_root,
        repository_root=repository_root,
        pdf_adapter=_DeterministicPdfAdapter(),
    )


def test_complete_manufacturing_fixture_passes_all_declared_dimensions(tmp_path: Path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    output = _render(_fixture(repository_root), tmp_path, repository_root, monkeypatch)

    acceptance = output.manifest["acceptance"]
    completeness = acceptance["research_completeness"]
    assert acceptance["overall_status"] == "PASS", acceptance
    assert completeness["status"] == "PASS"
    assert completeness["dimensions"] == {
        "time_series": "PASS",
        "operating_evidence": "PASS",
        "cash_flow": "PASS",
        "consensus": "PASS",
        "peers": "PASS",
        "sensitivity": "PASS",
        "monitoring_events": "PASS",
        "prior_run_validation": "PASS",
        "methodology": "PASS",
    }


def test_required_missing_dimension_fails_closed_without_fabrication(tmp_path: Path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    payload = json.loads(_fixture(repository_root).read_text(encoding="utf-8"))
    payload["inputs"].pop("financial_time_series")
    case_path = tmp_path / "missing-time-series.json"
    case_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    output = _render(case_path, tmp_path / "out", repository_root, monkeypatch)
    completeness = output.manifest["acceptance"]["research_completeness"]

    assert completeness["dimensions"]["time_series"] == "INCOMPLETE"
    assert completeness["status"] == "FAIL"
    assert output.manifest["acceptance"]["overall_status"] == "FAIL"
    assert "financial-trends" not in [section.section_id for section in output.document.sections]


def test_explicit_not_applicable_dimension_does_not_fail_or_invent_data(tmp_path: Path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    payload = json.loads(_fixture(repository_root).read_text(encoding="utf-8"))
    payload["inputs"].pop("prior_run_review_items")
    payload["research_completeness_acceptance"]["not_applicable_dimensions"] = [
        "prior_run_validation"
    ]
    case_path = tmp_path / "prior-run-na.json"
    case_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    output = _render(case_path, tmp_path / "out", repository_root, monkeypatch)
    acceptance = output.manifest["acceptance"]
    completeness = acceptance["research_completeness"]

    assert completeness["dimensions"]["prior_run_validation"] == "NOT_APPLICABLE"
    assert completeness["status"] == "PASS"
    assert acceptance["overall_status"] == "PASS", acceptance
    assert "monitoring.prior_run_review" not in output.result.artifacts
    assert "prior-run-review" not in [section.section_id for section in output.document.sections]
