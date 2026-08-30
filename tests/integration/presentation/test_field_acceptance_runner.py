from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from research_os.presentation import HtmlPresentationArtifact, PdfPresentationArtifact
from research_os.reporting import HumanReadableResearchView, ResearchReportDocument
from research_os.runtime import ResearchRunResult


class _DeterministicPdfAdapter:
    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact:
        return PdfPresentationArtifact.from_html(
            html=html,
            renderer_version="professional-pdf-adapter@1.0.0",
            backend_version="field-test-backend@1.0",
            content=b"%PDF-1.7\nfield-acceptance-test",
        )


def _record(key: str, value, *, evidence_type: str = "filing_fact") -> dict:
    return {
        "evidence_id": f"ev:synthetic-field:{key}",
        "evidence_type": evidence_type,
        "period_end": "2026-06-30",
        "period": "2026H1",
        "publish_ts": "2026-08-21T00:00:00Z",
        "value": value,
        "raw_value": value,
        "normalized_value": value,
        "unit": "元" if isinstance(value, (int, float)) else None,
        "scope": "consolidated",
        "version": "2026H1",
        "source_document_id": "synthetic-field-2026H1",
        "source_page": 1,
        "source_table": key,
        "source_url": "https://example.invalid/synthetic-field.pdf",
        "confidence_grade": "A",
        "verification_status": "PRIMARY_VERIFIED",
        "dataset_version": "field-acceptance@1",
        "parser_version": "manual-primary-source@1",
        "formula_version": "field-derived@1" if evidence_type == "calculated_metric" else None,
    }


def _case() -> dict:
    values = {
        "business_description": "electronic component distribution",
        "revenue": 73_555.0,
        "cogs": 71_463.0,
        "gross_profit": 2_092.0,
        "avg_ar": 18_817.0,
        "avg_inventory": 15_301.0,
        "avg_ap": 9_574.0,
        "ar": 26_112.0,
        "inventory": 18_348.0,
        "ap": 11_180.0,
        "delta_nwc": 17_470.0,
        "delta_revenue": 45_714.0,
        "delta_debt": 16_392.0,
        "external_equity_financing": 0.0,
        "short_debt": 30_038.0,
        "equity": 5_815.0,
        "ocf": -17_500.0,
        "operating_cash_flow": -17_500.0,
        "net_profit": 513.0,
        "interest_expense": 415.0,
        "financing_cost": 616.0,
        "derecognized_receivables": 6_104.0,
        "period_type": "H1",
        "period_start": "2026-01-01",
        "period_end": "2026-06-30",
        "period_days": 181,
        "is_cumulative": True,
        "delta_nwc_comparison_basis": "2026H1_end_vs_2025YE",
        "delta_debt_comparison_basis": "2026H1_end_vs_2025YE",
        "external_equity_financing_comparison_basis": "2026H1_end_vs_2025YE",
        "delta_revenue_comparison_basis": "2026H1_vs_2025H1",
    }
    calculated = {
        "gross_profit",
        "avg_ar",
        "avg_inventory",
        "avg_ap",
        "delta_nwc",
        "delta_revenue",
        "delta_debt",
    }
    return {
        "schema_version": "field-acceptance-case@1.0.0",
        "case_id": "synthetic-distributor",
        "company": {
            "company_id": "synthetic:field-distributor",
            "security_id": "000000.SZ",
            "exchange": "SZSE",
            "display_name": "Synthetic Distributor",
        },
        "decision_ts": "2026-08-30T00:00:00Z",
        "evidence": [
            _record(key, value, evidence_type="calculated_metric" if key in calculated else "filing_fact")
            for key, value in values.items()
        ],
        "inputs": {
            "fundamental_state_input": {
                "value": "UNCERTAIN",
                "source": "analyst_assumption",
                "method": "field acceptance conservative state",
            },
            "valuation_state_input": {
                "value": "UNRELIABLE",
                "source": "analyst_assumption",
                "method": "no supported valuation execution",
            },
            "expectation_state_input": {
                "value": "MIXED",
                "source": "analyst_assumption",
                "method": "no auditable consensus supplied",
            },
            "valuation_models": {
                "pe": {
                    "data_quality": 0.8,
                    "earnings_stability": 0.6,
                    "cash_flow_visibility": 0.1,
                    "capital_structure_fit": 0.1,
                    "business_model_fit": 0.7,
                    "forecast_stability": 0.3,
                },
                "pb": {
                    "data_quality": 0.8,
                    "earnings_stability": 0.6,
                    "cash_flow_visibility": 0.3,
                    "capital_structure_fit": 0.7,
                    "business_model_fit": 0.8,
                    "forecast_stability": 0.4,
                },
            },
            "next_verification_event": {
                "event_name": "下一次营运资金、融资成本与现金流披露",
                "event_time": "2026-10-31T00:00:00Z",
            },
        },
        "acceptance": {
            "expected_business_model": "distributor",
            "required_body_terms": ["保理", "经营现金流为负", "估值"],
            "forbidden_body_terms": ["ev:synthetic-field", "industry:distributor"],
            "audit_only_terms": ["ev:synthetic-field"],
        },
    }


def test_field_runner_executes_canonical_one_way_pipeline_and_writes_artifacts(
    tmp_path: Path,
    monkeypatch,
):
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repository_root))
    from scripts.render_field_acceptance_v1_5_08 import render_case

    case_path = tmp_path / "case.json"
    case_path.write_text(json.dumps(_case(), ensure_ascii=False), encoding="utf-8")

    output = render_case(
        case_path=case_path,
        output_root=tmp_path / "output",
        repository_root=repository_root,
        pdf_adapter=_DeterministicPdfAdapter(),
    )

    assert isinstance(output.result, ResearchRunResult)
    assert isinstance(output.view, HumanReadableResearchView)
    assert isinstance(output.document, ResearchReportDocument)
    assert output.result.business_model.primary_model == "distributor"
    assert output.bundle.html.source_hash == output.bundle.markdown.content_hash
    assert output.bundle.pdf.source_hash == output.bundle.html.content_hash

    body = output.bundle.html.content.split('<section id="audit-appendix"', maxsplit=1)[0]
    audit = output.bundle.html.content.split('<section id="audit-appendix"', maxsplit=1)[1]
    assert "终止确认应收款" in body
    assert "新增债务" in body
    assert "ev:synthetic-field" not in body
    assert "industry:distributor" not in body
    assert "ev:synthetic-field" in audit

    case_output = tmp_path / "output" / "synthetic-distributor"
    assert (case_output / "report.md").read_text(encoding="utf-8") == output.bundle.markdown.content
    assert (case_output / "report.html").read_text(encoding="utf-8") == output.bundle.html.content
    assert (case_output / "report.pdf").read_bytes() == output.bundle.pdf.content

    manifest = json.loads((case_output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["case_id"] == "synthetic-distributor"
    assert manifest["decision_ts"] == "2026-08-30T00:00:00Z"
    assert manifest["hash_chain"] == {
        "document": output.bundle.markdown.source_hash,
        "markdown": output.bundle.markdown.content_hash,
        "html": output.bundle.html.content_hash,
        "pdf": output.bundle.pdf.content_hash,
    }
    assert manifest["acceptance"]["status"] == "PASS"
    assert manifest["versions"]["html_renderer"] == "professional-html-renderer@1.0.0"
    assert manifest["versions"]["pdf_adapter"] == "professional-pdf-adapter@1.0.0"


def test_field_runner_rejects_future_evidence_before_rendering(tmp_path: Path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repository_root))
    from scripts.render_field_acceptance_v1_5_08 import FieldAcceptanceError, render_case

    payload = _case()
    payload["evidence"][0]["publish_ts"] = "2026-08-31T00:00:00Z"
    case_path = tmp_path / "future.json"
    case_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    try:
        render_case(
            case_path=case_path,
            output_root=tmp_path / "output",
            repository_root=repository_root,
            pdf_adapter=_DeterministicPdfAdapter(),
        )
    except FieldAcceptanceError as exc:
        assert "publish_ts exceeds decision_ts" in str(exc)
    else:
        raise AssertionError("future evidence must stop field acceptance")


def test_field_runner_applies_declared_evidence_defaults(tmp_path: Path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repository_root))
    from scripts.render_field_acceptance_v1_5_08 import render_case

    payload = _case()
    first = payload["evidence"][0]
    payload["evidence_defaults"] = {
        key: first[key]
        for key in (
            "evidence_type",
            "period_end",
            "period",
            "publish_ts",
            "source_document_id",
            "source_url",
            "confidence_grade",
            "verification_status",
            "dataset_version",
            "parser_version",
        )
    }
    for record in payload["evidence"]:
        for key in payload["evidence_defaults"]:
            record.pop(key, None)
    case_path = tmp_path / "defaults.json"
    case_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    output = render_case(
        case_path=case_path,
        output_root=tmp_path / "output",
        repository_root=repository_root,
        pdf_adapter=_DeterministicPdfAdapter(),
    )

    assert output.manifest["acceptance"]["status"] == "PASS"


def test_field_runner_requires_the_fixed_v1_5_08_decision_timestamp(
    tmp_path: Path, monkeypatch
):
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repository_root))
    from scripts.render_field_acceptance_v1_5_08 import FieldAcceptanceError, render_case

    payload = _case()
    payload["decision_ts"] = "2026-08-29T00:00:00Z"
    case_path = tmp_path / "wrong-decision-ts.json"
    case_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(FieldAcceptanceError, match="2026-08-30"):
        render_case(
            case_path=case_path,
            output_root=tmp_path / "output",
            repository_root=repository_root,
            pdf_adapter=_DeterministicPdfAdapter(),
        )


def test_three_real_company_cases_pass_with_pit_source_lineage(tmp_path: Path, monkeypatch):
    repository_root = Path(__file__).resolve().parents[3]
    monkeypatch.syspath_prepend(str(repository_root))
    from scripts.render_field_acceptance_v1_5_08 import render_case

    cases = repository_root / "tests/fixtures/field_acceptance/v1_5_08"
    expected_models = {
        "300034.SZ": "manufacturing",
        "001287.SZ": "distributor",
        "301073.SZ": "hospitality",
    }

    for case_id, expected_model in expected_models.items():
        output = render_case(
            case_path=cases / f"{case_id}.json",
            output_root=tmp_path / "output",
            repository_root=repository_root,
            pdf_adapter=_DeterministicPdfAdapter(),
        )

        assert output.result.business_model.primary_model == expected_model
        assert output.manifest["acceptance"]["status"] == "PASS"
        assert output.manifest["evidence_provenance"]
        assert all(
            item["publish_ts"] <= "2026-08-30T00:00:00Z"
            for item in output.manifest["evidence_provenance"]
        )
        assert all(
            item["source_url"].startswith("https://")
            for item in output.manifest["evidence_provenance"]
        )
