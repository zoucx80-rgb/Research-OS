from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from research_os.acceptance import (
    FieldAcceptanceError,
    FieldAcceptanceOutput,
    render_active_case,
)
from research_os.presentation import PlaywrightPdfAdapter


def _semantic_acceptance(output: FieldAcceptanceOutput) -> dict:
    result = output.result
    assessment = result.artifacts.get("thesis.semantic_signal_assessment")
    decision = result.artifacts.get("decision.record")
    provenance = result.artifacts.get("decision.state_provenance") or {}
    errors: list[str] = []

    if assessment is None:
        errors.append("canonical typed thesis signal assessment missing")
    else:
        margin = next(
            (item for item in assessment.signals if item.metric == "margin_change"),
            None,
        )
        if margin is None or margin.direction != "NEGATIVE" or margin.semantic_label != "毛利率下降":
            errors.append("negative margin change did not retain downward semantics")
        if margin is not None and "改善" in margin.semantic_label:
            errors.append("negative margin change used improvement wording")

        comparison = next(
            (
                item
                for item in assessment.comparisons
                if item.rule_id == "receivables-vs-revenue"
            ),
            None,
        )
        if comparison is None or comparison.status != "NOT_COMPARABLE":
            errors.append("incompatible receivables/revenue bases were not fail-closed")
        if "应收增速显著快于收入" in assessment.negative_signals:
            errors.append("incompatible comparison emitted an adverse growth signal")

    theses = list(result.artifacts.get("thesis.items") or [])
    if not theses or theses[0].status != "unresolved":
        errors.append("mixed current evidence without prior thesis is not unresolved")
    elif theses[0].falsifiers:
        errors.append("unresolved thesis fabricated falsifiers")

    if decision is None or decision.expectation_state != "UNKNOWN":
        errors.append("missing PIT expectation evidence did not resolve to UNKNOWN")
    expectation_provenance = provenance.get("expectation") if isinstance(provenance, dict) else None
    provenance_value = (
        expectation_provenance.get("value")
        if isinstance(expectation_provenance, dict)
        else getattr(expectation_provenance, "value", None)
    )
    if provenance_value != "UNKNOWN":
        errors.append("UNKNOWN expectation provenance missing")

    aliases = [
        item.fact_key
        for item in output.view.core_financial_facts
        if item.fact_key in {"ocf", "operating_cash_flow"}
    ]
    if len(aliases) != 1:
        errors.append("equivalent OCF aliases were not deduplicated")

    body = output.bundle.markdown.content.split("## 审计附录", 1)[0]
    if "None" in body:
        errors.append("literal None leaked into investor-facing Markdown")
    if "应收增速显著快于收入" in body:
        errors.append("non-comparable growth conclusion leaked into report body")
    if "市场预期证据不足" not in body:
        errors.append("expectation missingness label absent from report body")
    if "已采纳证据质量" not in body:
        errors.append("evidence quality is not labeled narrowly in report body")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "checks": {
            "typed_signal_artifact": assessment is not None,
            "expectation_state": getattr(decision, "expectation_state", None),
            "thesis_state": theses[0].status if theses else None,
            "ocf_alias_count": len(aliases),
        },
    }


def render_case(
    *,
    case_path: Path,
    output_root: Path,
    repository_root: Path,
    pdf_adapter=None,
    commit_sha: str | None = None,
) -> FieldAcceptanceOutput:
    output = render_active_case(
        case_path=case_path,
        output_root=output_root,
        repository_root=repository_root,
        pdf_adapter=pdf_adapter,
        commit_sha=commit_sha,
    )
    semantic = _semantic_acceptance(output)
    acceptance = {
        "presentation": output.manifest["acceptance"],
        "semantic_correctness": semantic,
        "overall_status": "PASS"
        if output.manifest["acceptance"]["status"] == "PASS"
        and semantic["status"] == "PASS"
        else "FAIL",
    }
    manifest = dict(output.manifest)
    manifest["schema_version"] = "field-acceptance-result@1.5.11"
    manifest["acceptance"] = acceptance
    (output.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return replace(output, manifest=manifest)


def render_directory(
    *,
    input_root: Path,
    output_root: Path,
    repository_root: Path,
    commit_sha: str | None = None,
) -> list[FieldAcceptanceOutput]:
    cases = sorted(input_root.glob("*.json"))
    if not cases:
        raise FieldAcceptanceError(f"no field acceptance cases in {input_root}")
    adapter = PlaywrightPdfAdapter()
    outputs = [
        render_case(
            case_path=case,
            output_root=output_root,
            repository_root=repository_root,
            pdf_adapter=adapter,
            commit_sha=commit_sha,
        )
        for case in cases
    ]
    failed = [item.case_id for item in outputs if item.manifest["acceptance"]["overall_status"] != "PASS"]
    if failed:
        raise FieldAcceptanceError(f"v1.5.11 semantic field acceptance failed: {failed}")
    return outputs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render v1.5.11 semantic-correctness field acceptance")
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
    args.output_dir.resolve().mkdir(parents=True, exist_ok=True)
    (args.output_dir.resolve() / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
