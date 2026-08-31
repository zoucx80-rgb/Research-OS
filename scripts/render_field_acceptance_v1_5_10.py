from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research_os.presentation import (
    MarkdownArtifactRenderer,
    PlaywrightPdfAdapter,
    ProfessionalPresentationPipeline,
)
from research_os.reporting.composer_v1_5_10 import (
    ResearchReportComposer as V1_5_10ResearchReportComposer,
)
from research_os.reporting.markdown_renderer_v1_5_10 import (
    ResearchReportMarkdownRenderer as V1_5_10ResearchReportMarkdownRenderer,
)
from research_os.reporting.research_view_v1_5_10 import (
    ResearchViewPresenter as V1_5_10ResearchViewPresenter,
)
from research_os.runtime import (
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
    ResearchRuntimeFactory,
)
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION
from scripts.render_field_acceptance_v1_5_08 import (
    FieldAcceptanceError,
    FieldAcceptanceOutput,
    _FIXED_DECISION_TS,
    _acceptance_result,
    _case_evidence,
    _load_case,
    _repository_identity,
    _research_inputs,
)
from scripts.render_field_acceptance_v1_5_09 import _evaluate_research_depth


_DIMENSIONS = (
    "time_series",
    "operating_evidence",
    "cash_flow",
    "consensus",
    "peers",
    "sensitivity",
    "monitoring_events",
    "prior_run_validation",
    "methodology",
)

_DIMENSION_PRESENTATION = {
    "time_series": ("financial-trends", "财务趋势"),
    "operating_evidence": ("operating-evidence", "经营证据"),
    "cash_flow": ("cash-flow-quality", "现金流质量"),
    "consensus": ("consensus-dispersion", "一致预期分布"),
    "peers": ("peer-comparison", "同行与产品线比较"),
    "sensitivity": ("sensitivity-scenarios", "敏感性与情景"),
    "monitoring_events": ("monitoring-calendar", "监控规则与验证日历"),
    "prior_run_validation": ("prior-run-review", "上期判断回顾"),
    "methodology": ("methodology-disclosure", "方法说明"),
}


def _present(value: Any) -> bool:
    return value not in (None, [], (), {})


def _dimension_statuses(output: FieldAcceptanceOutput) -> dict[str, str]:
    artifacts = output.result.artifacts

    series = artifacts.get("financial.time_series") or ()
    time_series_ok = any(
        sum(1 for point in item.points if point.value is not None) >= 2
        for item in series
    )

    cash = artifacts.get("cash_flow.quality_bridge")
    cash_ok = bool(
        cash is not None
        and cash.operating_cash_flow is not None
        and cash.capex_cash is not None
        and cash.working_capital_contribution is not None
        and cash.simplified_fcf is not None
    )

    distributions = artifacts.get("expectation.consensus_distribution") or ()
    consensus_ok = any(
        item.breadth == "multi_source" and item.source_count >= 2
        for item in distributions
    )

    rules = artifacts.get("monitoring.rules")
    events = artifacts.get("monitoring.verification_calendar")
    review = artifacts.get("monitoring.prior_run_review")

    return {
        "time_series": "PASS" if time_series_ok else "INCOMPLETE",
        "operating_evidence": "PASS" if _present(artifacts.get("research.operating_evidence")) else "INCOMPLETE",
        "cash_flow": "PASS" if cash_ok else "INCOMPLETE",
        "consensus": "PASS" if consensus_ok else "INCOMPLETE",
        "peers": "PASS" if _present(artifacts.get("peers.comparables")) else "INCOMPLETE",
        "sensitivity": "PASS" if _present(artifacts.get("scenario.sensitivities")) else "INCOMPLETE",
        "monitoring_events": "PASS" if _present(rules) and _present(events) else "INCOMPLETE",
        "prior_run_validation": "PASS" if review is not None and review.scored_count > 0 else "INCOMPLETE",
        "methodology": "PASS" if _present(artifacts.get("methodology.disclosure")) else "INCOMPLETE",
    }


def _evaluate_research_completeness(
    *,
    output: FieldAcceptanceOutput,
    case: dict[str, Any],
) -> dict[str, Any]:
    contract = dict(case.get("research_completeness_acceptance") or {})
    required = list(contract.get("required_dimensions") or _DIMENSIONS)
    not_applicable = list(contract.get("not_applicable_dimensions") or [])

    unknown = sorted((set(required) | set(not_applicable)) - set(_DIMENSIONS))
    if unknown:
        raise FieldAcceptanceError(
            "unknown research completeness dimension(s): " + ", ".join(unknown)
        )

    statuses = _dimension_statuses(output)
    for dimension in not_applicable:
        statuses[dimension] = "NOT_APPLICABLE"

    errors = [
        f"required research completeness dimension is incomplete: {dimension}"
        for dimension in required
        if statuses[dimension] not in {"PASS", "NOT_APPLICABLE"}
    ]
    return {
        "status": "PASS" if not errors else "FAIL",
        "dimensions": statuses,
        "required_dimensions": required,
        "not_applicable_dimensions": not_applicable,
        "errors": errors,
    }


def _effective_case_for_not_applicable(case: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(case))
    contract = result.get("research_completeness_acceptance") or {}
    not_applicable = set(contract.get("not_applicable_dimensions") or [])
    if not not_applicable:
        return result

    section_ids = {
        _DIMENSION_PRESENTATION[item][0]
        for item in not_applicable
        if item in _DIMENSION_PRESENTATION
    }
    terms = {
        _DIMENSION_PRESENTATION[item][1]
        for item in not_applicable
        if item in _DIMENSION_PRESENTATION
    }

    presentation = dict(result.get("acceptance") or {})
    presentation["required_section_ids"] = [
        item
        for item in presentation.get("required_section_ids", [])
        if item not in section_ids
    ]
    presentation["required_body_terms"] = [
        item
        for item in presentation.get("required_body_terms", [])
        if item not in terms
    ]
    result["acceptance"] = presentation

    depth = dict(result.get("research_depth_acceptance") or {})
    depth["required_document_section_ids"] = [
        item
        for item in depth.get("required_document_section_ids", [])
        if item not in section_ids
    ]
    depth["required_body_terms"] = [
        item
        for item in depth.get("required_body_terms", [])
        if item not in terms
    ]
    result["research_depth_acceptance"] = depth
    return result


def _presentation_acceptance(
    *,
    case: dict[str, Any],
    result,
    bundle,
) -> dict[str, Any]:
    try:
        return _acceptance_result(case, result=result, bundle=bundle)
    except FieldAcceptanceError as exc:
        return {
            "status": "FAIL",
            "errors": [str(exc)],
        }


def _render_current_case(
    *,
    case_path: Path,
    output_root: Path,
    repository_root: Path,
    commit_sha: str | None,
    pdf_adapter,
) -> FieldAcceptanceOutput:
    payload = _load_case(case_path)
    decision_ts = datetime.fromisoformat(
        str(payload["decision_ts"]).replace("Z", "+00:00")
    )
    if decision_ts != _FIXED_DECISION_TS:
        raise FieldAcceptanceError(
            "v1.5.10 field acceptance requires decision_ts 2026-08-30T00:00:00Z"
        )

    baseline, preflight = _repository_identity(
        repository_root,
        commit_sha=commit_sha,
        decision_ts=decision_ts,
    )
    evidence, facts, evidence_by_fact = _case_evidence(
        payload,
        decision_ts=decision_ts,
    )
    company = CompanyRef.model_validate(payload["company"])
    context = ResearchContext(
        run_id=str(payload.get("run_id") or f"field:v1.5.10:{payload['case_id']}"),
        company=company,
        decision_ts=decision_ts,
        baseline=baseline,
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(values=facts, evidence_by_fact=evidence_by_fact),
        options=ResearchOptions(),
    )
    inputs = _research_inputs(payload, preflight=preflight)
    result = ResearchRuntimeFactory.historical_v1_5_10().run_context(context, inputs)
    view = V1_5_10ResearchViewPresenter().build(result)
    document = V1_5_10ResearchReportComposer().compose(view)
    markdown_renderer = MarkdownArtifactRenderer(
        renderer=V1_5_10ResearchReportMarkdownRenderer()
    )
    bundle = ProfessionalPresentationPipeline(
        markdown_renderer=markdown_renderer,
        pdf_adapter=pdf_adapter,
    ).render(document)

    effective_case = _effective_case_for_not_applicable(payload)
    presentation = _presentation_acceptance(
        case=effective_case,
        result=result,
        bundle=bundle,
    )

    case_id = str(payload["case_id"])
    output_dir = output_root / case_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.md").write_text(bundle.markdown.content, encoding="utf-8")
    (output_dir / "report.html").write_text(bundle.html.content, encoding="utf-8")
    (output_dir / "report.pdf").write_bytes(bundle.pdf.content)

    manifest = {
        "schema_version": "field-acceptance-result@1.2.0",
        "case_id": case_id,
        "company": company.model_dump(mode="json"),
        "decision_ts": decision_ts.isoformat().replace("+00:00", "Z"),
        "repository": baseline.model_dump(mode="json"),
        "business_model": result.business_model.model_dump(mode="json"),
        "completion": result.completion.model_dump(mode="json"),
        "evidence_provenance": [
            {
                "evidence_id": item.evidence_id,
                "fact": item.source_table,
                "publish_ts": item.publish_ts.isoformat().replace("+00:00", "Z"),
                "source_document_id": item.source_document_id,
                "source_url": item.source_url,
                "confidence_grade": item.confidence_grade.value,
                "verification_status": item.verification_status.value,
            }
            for item in evidence
        ],
        "hash_chain": {
            "document": bundle.markdown.source_hash,
            "markdown": bundle.markdown.content_hash,
            "html": bundle.html.content_hash,
            "pdf": bundle.pdf.content_hash,
        },
        "versions": {
            "research_os": RESEARCH_OS_VERSION,
            "core_api": CORE_API_VERSION,
            "presenter": view.presentation_version,
            "composer": document.composition_version,
            "markdown_renderer": bundle.markdown.renderer_version,
            "html_renderer": bundle.html.renderer_version,
            "pdf_adapter": bundle.pdf.renderer_version,
            "pdf_backend": bundle.pdf.backend_version,
            "research_completeness": "1.0.0",
        },
        "acceptance": {
            "presentation": presentation,
        },
    }
    return FieldAcceptanceOutput(
        case_id=case_id,
        result=result,
        view=view,
        document=document,
        bundle=bundle,
        manifest=manifest,
        output_dir=output_dir,
    )


def render_case(
    *,
    case_path: Path,
    output_root: Path,
    repository_root: Path,
    commit_sha: str | None = None,
    pdf_adapter=None,
) -> FieldAcceptanceOutput:
    case = _load_case(case_path)
    output = _render_current_case(
        case_path=case_path,
        output_root=output_root,
        repository_root=repository_root,
        commit_sha=commit_sha,
        pdf_adapter=pdf_adapter,
    )
    effective_case = _effective_case_for_not_applicable(case)
    presentation = dict(output.manifest["acceptance"]["presentation"])
    research_depth = _evaluate_research_depth(output=output, case=effective_case)
    research_completeness = _evaluate_research_completeness(output=output, case=case)
    overall_status = (
        "PASS"
        if presentation.get("status") == "PASS"
        and research_depth["status"] == "PASS"
        and research_completeness["status"] == "PASS"
        else "FAIL"
    )

    manifest = dict(output.manifest)
    manifest["acceptance"] = {
        "presentation": presentation,
        "research_depth": research_depth,
        "research_completeness": research_completeness,
        "overall_status": overall_status,
    }
    (output.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return replace(output, manifest=manifest)


def render_directory(
    *,
    input_dir: Path,
    output_root: Path,
    repository_root: Path,
    commit_sha: str | None = None,
) -> list[FieldAcceptanceOutput]:
    case_paths = sorted(input_dir.glob("*.json"))
    if not case_paths:
        raise FieldAcceptanceError(f"no field-acceptance cases found in {input_dir}")

    adapter = PlaywrightPdfAdapter()
    outputs = [
        render_case(
            case_path=path,
            output_root=output_root,
            repository_root=repository_root,
            commit_sha=commit_sha,
            pdf_adapter=adapter,
        )
        for path in case_paths
    ]
    summary = {
        "schema_version": "field-acceptance-summary@1.2.0",
        "overall_status": (
            "PASS"
            if all(item.manifest["acceptance"]["overall_status"] == "PASS" for item in outputs)
            else "FAIL"
        ),
        "cases": [
            {
                "case_id": item.manifest["case_id"],
                "presentation_status": item.manifest["acceptance"]["presentation"]["status"],
                "research_depth_status": item.manifest["acceptance"]["research_depth"]["status"],
                "research_completeness_status": item.manifest["acceptance"]["research_completeness"]["status"],
                "overall_status": item.manifest["acceptance"]["overall_status"],
                "output_dir": str(item.output_dir.relative_to(output_root)),
            }
            for item in outputs
        ],
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if summary["overall_status"] != "PASS":
        failed = [
            item["case_id"]
            for item in summary["cases"]
            if item["overall_status"] != "PASS"
        ]
        raise FieldAcceptanceError(
            "v1.5.10 field acceptance failed: " + ", ".join(failed)
        )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render v1.5.10 research-completeness field acceptance"
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--commit-sha", default=None)
    args = parser.parse_args()

    render_directory(
        input_dir=args.input_dir,
        output_root=args.output_dir,
        repository_root=args.repository_root.resolve(),
        commit_sha=args.commit_sha,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
