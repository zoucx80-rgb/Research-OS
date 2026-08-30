from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, datetime
import json
import os
from pathlib import Path
import subprocess
from typing import Any

from research_os.domain.evidence import Evidence
from research_os.preflight.models import RepositoryPreflightEvidence
from research_os.presentation import (
    PlaywrightPdfAdapter,
    PresentationBundle,
    ProfessionalPresentationPipeline,
)
from research_os.reporting import (
    HumanReadableResearchView,
    ResearchReportComposer,
    ResearchReportDocument,
    ResearchViewPresenter,
)
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchInputs,
    ResearchOptions,
    ResearchRunResult,
    ResearchRuntimeFactory,
)
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


class FieldAcceptanceError(RuntimeError):
    """A field case violates PIT, provenance, or presentation acceptance."""


_FIXED_DECISION_TS = datetime.fromisoformat("2026-08-30T00:00:00+00:00")


@dataclass(frozen=True)
class FieldAcceptanceOutput:
    case_id: str
    result: ResearchRunResult
    view: HumanReadableResearchView
    document: ResearchReportDocument
    bundle: PresentationBundle
    manifest: dict[str, Any]
    output_dir: Path


def _git(repository_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _repository_identity(
    repository_root: Path,
    *,
    commit_sha: str | None,
    decision_ts: datetime,
) -> tuple[BaselineFingerprint, RepositoryPreflightEvidence]:
    frozen_sha = commit_sha or os.environ.get("GITHUB_SHA") or _git(
        repository_root, "rev-parse", "HEAD"
    )
    if _git(repository_root, "rev-parse", f"{frozen_sha}^{{commit}}") != frozen_sha:
        raise FieldAcceptanceError("frozen repository commit is unavailable")
    message = _git(repository_root, "show", "-s", "--format=%s", frozen_sha)
    agents_blob = _git(repository_root, "rev-parse", f"{frozen_sha}:AGENTS.md")
    prompt_blob = _git(
        repository_root,
        "rev-parse",
        f"{frozen_sha}:docs/prompts/stock_research.md",
    )
    baseline = BaselineFingerprint(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        commit_sha=frozen_sha,
        research_os_version=RESEARCH_OS_VERSION,
        core_api_version=CORE_API_VERSION,
    )
    preflight = RepositoryPreflightEvidence(
        repository_full_name=baseline.repository_full_name,
        repository_id=baseline.repository_id,
        branch=baseline.branch,
        head_sha=frozen_sha,
        head_commit_message=message,
        agents_blob_sha=agents_blob,
        research_prompt_blob_sha=prompt_blob,
        verified_at=decision_ts,
        agents_ref=frozen_sha,
        research_prompt_ref=frozen_sha,
    )
    return baseline, preflight


def _coerce_fact_value(key: str, value: Any) -> Any:
    if key in {"period_start", "period_end"} and isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _load_case(case_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(case_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FieldAcceptanceError(f"cannot load field case {case_path}") from exc
    if payload.get("schema_version") != "field-acceptance-case@1.0.0":
        raise FieldAcceptanceError("unsupported field acceptance schema")
    return payload


def _case_evidence(
    payload: dict[str, Any],
    *,
    decision_ts: datetime,
) -> tuple[list[Evidence], dict[str, Any], dict[str, list[str]]]:
    company_id = str(payload["company"]["company_id"])
    evidence: list[Evidence] = []
    facts: dict[str, Any] = {}
    evidence_by_fact: dict[str, list[str]] = {}
    defaults = dict(payload.get("evidence_defaults") or {})
    for raw in payload.get("evidence", []):
        record = {**defaults, **dict(raw)}
        publish_ts = datetime.fromisoformat(
            str(record["publish_ts"]).replace("Z", "+00:00")
        )
        if publish_ts > decision_ts:
            raise FieldAcceptanceError(
                f"evidence {record.get('evidence_id')} publish_ts exceeds decision_ts"
            )
        key = str(record.get("source_table") or "")
        if not key:
            raise FieldAcceptanceError("every evidence record needs source_table fact identity")
        if key in facts:
            raise FieldAcceptanceError(f"duplicate field fact: {key}")
        value = _coerce_fact_value(key, record.get("value"))
        record.update(
            company_id=company_id,
            ingested_at=decision_ts,
            value=value,
            normalized_value=_coerce_fact_value(key, record.get("normalized_value")),
        )
        item = Evidence.model_validate(record)
        evidence.append(item)
        facts[key] = value
        evidence_by_fact[key] = [item.evidence_id]
    if not evidence:
        raise FieldAcceptanceError("field acceptance requires PIT evidence")
    return evidence, facts, evidence_by_fact


def _research_inputs(
    payload: dict[str, Any],
    *,
    preflight: RepositoryPreflightEvidence,
) -> ResearchInputs:
    raw = dict(payload.get("inputs") or {})
    versions = {
        "dataset_version": "field-acceptance-v1.5.08@1",
        "parser_version": "manual-primary-source@1",
        "formula_version": "field-derived@1",
        "report_version": "professional-research-view@1.3.0",
        **dict(raw.get("versions") or {}),
    }
    raw.update(preflight=preflight, versions=versions)
    return ResearchInputs.model_validate(raw)


_DEFAULT_BODY_FORBIDDEN = (
    "evidence_ids",
    "assumption_ids",
    "plugin_id",
    "reason_codes",
    "ResearchRunResult(",
    "HumanReadableResearchView(",
    "ResearchReportDocument(",
)


def _acceptance_result(
    payload: dict[str, Any],
    *,
    result: ResearchRunResult,
    bundle: PresentationBundle,
) -> dict[str, Any]:
    contract = dict(payload.get("acceptance") or {})
    html = bundle.html.content
    marker = '<section id="audit-appendix"'
    if marker not in html:
        raise FieldAcceptanceError("rendered HTML has no Audit Appendix boundary")
    body, audit = html.split(marker, maxsplit=1)
    errors: list[str] = []

    expected_model = contract.get("expected_business_model")
    if expected_model and result.business_model.primary_model != expected_model:
        errors.append(
            f"business model {result.business_model.primary_model!r} != {expected_model!r}"
        )
    for term in contract.get("required_body_terms", []):
        if term not in body:
            errors.append(f"required body term missing: {term}")
    for term in [*_DEFAULT_BODY_FORBIDDEN, *contract.get("forbidden_body_terms", [])]:
        if term and term in body:
            errors.append(f"forbidden body term present: {term}")
    for term in contract.get("forbidden_anywhere_terms", []):
        if term and term in html:
            errors.append(f"forbidden presentation term present: {term}")
    for term in contract.get("audit_only_terms", []):
        if term in body:
            errors.append(f"audit-only term leaked into body: {term}")
        if term not in audit:
            errors.append(f"audit-only term missing from appendix: {term}")
    for section_id in contract.get("required_section_ids", []):
        if f'id="{section_id}"' not in html:
            errors.append(f"required section missing: {section_id}")

    if errors:
        raise FieldAcceptanceError("; ".join(errors))
    return {
        "status": "PASS",
        "expected_business_model": expected_model,
        "required_body_terms": list(contract.get("required_body_terms", [])),
        "forbidden_body_terms": list(contract.get("forbidden_body_terms", [])),
        "forbidden_anywhere_terms": list(contract.get("forbidden_anywhere_terms", [])),
        "audit_only_terms": list(contract.get("audit_only_terms", [])),
        "required_section_ids": list(contract.get("required_section_ids", [])),
    }


def render_case(
    *,
    case_path: Path,
    output_root: Path,
    repository_root: Path,
    pdf_adapter=None,
    commit_sha: str | None = None,
) -> FieldAcceptanceOutput:
    payload = _load_case(case_path)
    decision_ts = datetime.fromisoformat(
        str(payload["decision_ts"]).replace("Z", "+00:00")
    )
    if decision_ts != _FIXED_DECISION_TS:
        raise FieldAcceptanceError(
            "v1.5.08 field acceptance requires decision_ts "
            "2026-08-30T00:00:00Z"
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
        run_id=str(payload.get("run_id") or f"field:v1.5.08:{payload['case_id']}"),
        company=company,
        decision_ts=decision_ts,
        baseline=baseline,
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(values=facts, evidence_by_fact=evidence_by_fact),
        options=ResearchOptions(),
    )
    inputs = _research_inputs(payload, preflight=preflight)
    result = ResearchRuntimeFactory.default().run_context(context, inputs)
    view = ResearchViewPresenter().build(result)
    document = ResearchReportComposer().compose(view)
    bundle = ProfessionalPresentationPipeline(pdf_adapter=pdf_adapter).render(document)
    acceptance = _acceptance_result(payload, result=result, bundle=bundle)

    case_id = str(payload["case_id"])
    output_dir = output_root / case_id
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "report.md").write_text(bundle.markdown.content, encoding="utf-8")
    (output_dir / "report.html").write_text(bundle.html.content, encoding="utf-8")
    (output_dir / "report.pdf").write_bytes(bundle.pdf.content)

    manifest = {
        "schema_version": "field-acceptance-result@1.0.0",
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
        },
        "acceptance": acceptance,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return FieldAcceptanceOutput(
        case_id=case_id,
        result=result,
        view=view,
        document=document,
        bundle=bundle,
        manifest=manifest,
        output_dir=output_dir,
    )


def render_directory(
    *,
    input_root: Path,
    output_root: Path,
    repository_root: Path,
    commit_sha: str | None = None,
) -> list[FieldAcceptanceOutput]:
    case_paths = sorted(input_root.glob("*.json"))
    if not case_paths:
        raise FieldAcceptanceError(f"no field acceptance cases in {input_root}")
    adapter = PlaywrightPdfAdapter()
    return [
        render_case(
            case_path=case_path,
            output_root=output_root,
            repository_root=repository_root,
            pdf_adapter=adapter,
            commit_sha=commit_sha,
        )
        for case_path in case_paths
    ]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render Research OS v1.5.08 field cases")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--commit-sha")
    return parser


def main() -> int:
    args = _parser().parse_args()
    outputs = render_directory(
        input_root=args.input_dir.resolve(),
        output_root=args.output_dir.resolve(),
        repository_root=args.repository_root.resolve(),
        commit_sha=args.commit_sha,
    )
    summary = {
        "status": "PASS",
        "cases": [item.manifest for item in outputs],
    }
    summary_path = args.output_dir.resolve() / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
