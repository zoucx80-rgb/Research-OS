from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
from typing import Any

from research_os.presentation import PlaywrightPdfAdapter
from scripts.render_field_acceptance_v1_5_08 import (
    FieldAcceptanceError,
    FieldAcceptanceOutput,
    render_case as render_presentation_case,
)


_DEFAULT_FORBIDDEN_DEPTH_TERMS = (
    "专业研究问题的中文展示尚未配置",
    "存在尚未配置中文说明的研究状态",
)
_HOSPITALITY_FORBIDDEN_TERMS = (
    "RevPAR",
    "ADR",
    "OCC",
    "同店增长",
    "成熟店曲线",
    "轻资产",
    "低资本占用",
    "现金转化极佳",
)


def _dedup(items: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in items if item))


def _body_markdown(output: FieldAcceptanceOutput) -> str:
    return output.bundle.markdown.content.split("## 审计附录", 1)[0]


def _evaluate_research_depth(
    *,
    output: FieldAcceptanceOutput,
    case: dict[str, Any],
) -> dict[str, Any]:
    contract = case.get("research_depth_acceptance") or {}
    errors: list[str] = []
    body = _body_markdown(output)

    facts = {
        item.fact_key: item
        for item in list(getattr(output.view, "core_financial_facts", []) or [])
    }
    section_ids = [section.section_id for section in output.document.sections]

    required_fact_keys = list(contract.get("required_financial_fact_keys", []))
    for key in required_fact_keys:
        if key not in facts:
            errors.append(f"missing required canonical financial fact: {key}")

    required_sections = list(contract.get("required_document_section_ids", []))
    for section_id in required_sections:
        if section_id not in section_ids:
            errors.append(f"missing required research document section: {section_id}")

    required_terms = list(contract.get("required_body_terms", []))
    for term in required_terms:
        if term not in body:
            errors.append(f"missing required research-depth body term: {term}")

    forbidden_terms = [
        *_DEFAULT_FORBIDDEN_DEPTH_TERMS,
        *list(contract.get("forbidden_body_terms", [])),
    ]
    if output.view.business_model.code == "hospitality":
        forbidden_terms.extend(_HOSPITALITY_FORBIDDEN_TERMS)
    for term in _dedup(forbidden_terms):
        if term in body:
            errors.append(f"forbidden research-depth body term present: {term}")

    for assessment in output.view.question_assessments:
        question = assessment.question.strip()
        if "?" in question or question.startswith(("What ", "How ", "Is ", "Are ", "Which ")):
            errors.append(f"non-localized professional research question: {question}")

    for risk in output.document.decision_snapshot.material_risks:
        if "尚未配置中文说明" in risk.label:
            errors.append(f"unmapped machine state surfaced as material risk: {risk.code}")

    business_model = output.view.business_model.code
    if business_model == "manufacturing":
        margin_change = facts.get("margin_change")
        if margin_change is not None and isinstance(margin_change.value, (int, float)):
            if margin_change.value < 0 and "毛利率同比下降" not in body:
                errors.append("negative canonical margin_change is not explained as 毛利率同比下降")
            if margin_change.value > 0 and "毛利率同比提升" not in body:
                errors.append("positive canonical margin_change is not explained as 毛利率同比提升")

    if business_model == "distributor":
        if output.view.funding_loop is not None and "capital-funding" not in section_ids:
            errors.append("distributor funding loop exists but capital-funding section is missing")
        if output.view.driver_graph is not None and output.view.driver_graph.edges and "causal-bridge" not in section_ids:
            errors.append("distributor driver graph exists but causal-bridge section is missing")

    if business_model == "hospitality":
        lease_limitations = [
            item for item in output.view.presentation_limitations if "租赁" in item
        ]
        if not lease_limitations:
            errors.append("lease-heavy hospitality presentation limitation is missing")
        if not output.view.industry_plugins:
            capability_gap = any(
                gap.gap_type.code != "business_model_evidence"
                for gap in output.view.coverage_gaps
            )
            if not capability_gap:
                errors.append("hospitality without industry plugin does not expose capability gap")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": _dedup(errors),
        "required_financial_fact_keys": required_fact_keys,
        "observed_financial_fact_keys": list(facts),
        "required_document_section_ids": required_sections,
        "observed_document_section_ids": section_ids,
        "required_body_terms": required_terms,
        "forbidden_body_terms": _dedup(forbidden_terms),
    }


def render_case(
    *,
    case_path: Path,
    output_root: Path,
    repository_root: Path,
    commit_sha: str | None = None,
    pdf_adapter=None,
) -> FieldAcceptanceOutput:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    output = render_presentation_case(
        case_path=case_path,
        output_root=output_root,
        repository_root=repository_root,
        commit_sha=commit_sha,
        pdf_adapter=pdf_adapter,
    )

    presentation = dict(output.manifest.get("acceptance") or {})
    presentation.setdefault("status", "PASS")
    research_depth = _evaluate_research_depth(output=output, case=case)
    overall_status = (
        "PASS"
        if presentation.get("status") == "PASS" and research_depth["status"] == "PASS"
        else "FAIL"
    )

    manifest = dict(output.manifest)
    versions = dict(manifest.get("versions") or {})
    versions.update(
        {
            "presenter": output.view.presentation_version,
            "composer": output.document.composition_version,
            "markdown_renderer": output.bundle.markdown.renderer_version,
            "html_renderer": output.bundle.html.renderer_version,
            "pdf_adapter": output.bundle.pdf.renderer_version,
        }
    )
    manifest["versions"] = versions
    manifest["acceptance"] = {
        "presentation": presentation,
        "research_depth": research_depth,
        "overall_status": overall_status,
    }

    manifest_path = output.output_dir / "manifest.json"
    manifest_path.write_text(
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
        "schema_version": "field-acceptance-summary@1.1.0",
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
            "research-depth field acceptance failed: " + ", ".join(failed)
        )
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Render v1.5.09 dual-status field acceptance")
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
