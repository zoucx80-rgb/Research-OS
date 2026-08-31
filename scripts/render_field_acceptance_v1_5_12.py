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
from research_os.semantics.preservation import SemanticPreservationValidator


def _finding(
    finding_id: str,
    passed: bool,
    layer: str,
    detail: str,
    *,
    failure_status: str = "FAIL",
) -> dict:
    return {
        "finding_id": finding_id,
        "status": "PASS" if passed else failure_status,
        "layer": layer,
        "detail": detail,
    }


def _semantic_acceptance(output: FieldAcceptanceOutput) -> dict:
    result = output.result
    validation = result.artifacts.get("validation.semantic_preservation")
    cycle = result.artifacts.get("semantic.cycle_assessment")
    moat = result.artifacts.get("semantic.moat_assessment")
    reconciliation = result.artifacts.get("valuation.reconciliation")
    rationales = list(result.artifacts.get("valuation.rationales") or [])
    body = output.bundle.markdown.content.split("## 审计附录", 1)[0]

    sensitivity = output.view.research_completeness.get("scenario.sensitivities")
    sensitivity_section = next(
        (
            item
            for item in output.document.sections
            if item.section_id == "sensitivity-scenarios"
        ),
        None,
    )
    sensitivity_document_fingerprint = (
        getattr(sensitivity_section.blocks[0], "semantic_fingerprint", None)
        if sensitivity_section is not None and sensitivity_section.blocks
        else None
    )
    sensitivity_canonical_fingerprint = getattr(
        validation, "sensitivity_fingerprint", None
    )
    sensitivity_view_fingerprint = (
        SemanticPreservationValidator.sensitivity_fingerprint(sensitivity)
        if sensitivity is not None
        else None
    )
    monitoring = output.view.research_completeness.get("monitoring.rules")
    monitoring_section = next(
        (
            item
            for item in output.document.sections
            if item.section_id == "monitoring-calendar"
        ),
        None,
    )
    monitoring_document_fingerprint = (
        getattr(monitoring_section.blocks[0], "semantic_fingerprint", None)
        if monitoring_section is not None and monitoring_section.blocks
        else None
    )
    monitoring_canonical_fingerprint = getattr(
        validation, "monitoring_fingerprint", None
    )
    monitoring_view_fingerprint = (
        SemanticPreservationValidator.monitoring_fingerprint(monitoring)
        if monitoring is not None
        else None
    )

    sensitivity_items = list(sensitivity or [])
    result_bearing_sensitivities = [
        item
        for item in sensitivity_items
        if any(item.get(key) is not None for key in ("result", "result_low", "result_high"))
    ]

    rationale_is_economic = bool(rationales) and all(
        not any(
            token in item.explanation.lower()
            for token in ("research os", "renderer", "software version", "release version")
        )
        for item in rationales
    )
    findings = [
        _finding(
            "moat-wording",
            (
                getattr(moat, "state", None) == "ECONOMIC_MOAT_REALIZED"
                and "经济护城河已实现" in body
            )
            or (
                getattr(moat, "state", None) == "INSUFFICIENT_MOAT_EVIDENCE"
                and "护城河证据不足" in body
            )
            or (
                getattr(moat, "state", None) == "ECONOMIC_MOAT_UNREALIZED"
                and "经济护城河尚未实现" in body
            )
            or (
                getattr(moat, "state", None)
                in {
                    "OTHER_BARRIER_EVIDENCED",
                    "TECHNICAL_BARRIER_EVIDENCED",
                }
                and "不等同于已实现经济护城河" in body
            ),
            "semantics/claims -> Markdown",
            "barrier evidence remains distinct from realized economic moat",
        ),
        _finding(
            "sensitivity-qualifiers",
            getattr(validation, "status", None) == "PASS"
            and all(
                term in body
                for term in ("关键假设", "模型边界", "适用范围")
            ),
            "completeness -> preservation -> Markdown",
            "numerical result travels with assumptions, boundary and applicability",
        ),
        _finding(
            "typed-threshold",
            "研究预警线" in body and "比较口径" in body and "适用范围" in body,
            "completeness -> Markdown",
            "analyst-defined threshold is explicitly labeled and scoped",
        ),
        _finding(
            "cycle-claim-strength",
            (
                getattr(cycle, "state", None) == "RECOVERY_NOT_OBSERVED"
                and "尚未观察到修复迹象" in body
            )
            or (
                getattr(cycle, "state", None)
                in {"RECOVERY_OBSERVED", "TROUGH_UNCONFIRMED"}
                and "周期底部未确认" in body
            )
            or (
                getattr(cycle, "state", None) == "TROUGH_CONFIRMED"
                and "周期底部已确认" in body
            ),
            "semantics/claims -> Markdown",
            "observed recovery does not become a confirmed trough",
        ),
        _finding(
            "valuation-economic-rationale",
            rationale_is_economic and "经济适用性理由" in body,
            "valuation -> Markdown",
            "model downgrade is supported by economic factors only",
        ),
        _finding(
            "valuation-reconciliation",
            getattr(reconciliation, "status", None)
            in {"INTERSECTION", "CROSS_CHECK_BAND", "MODEL_DISAGREEMENT", "NOT_COMPARABLE"}
            and "跨模型估值协调" in body,
            "valuation/reconciliation -> Markdown",
            "canonical reconciliation status is rendered without presentation calculation",
        ),
        _finding(
            "result-view-document-fingerprint",
            sensitivity_canonical_fingerprint is not None
            and sensitivity_canonical_fingerprint
            == sensitivity_view_fingerprint
            == sensitivity_document_fingerprint
            and monitoring_canonical_fingerprint is not None
            and monitoring_canonical_fingerprint
            == monitoring_view_fingerprint
            == monitoring_document_fingerprint,
            "Result -> View -> Document",
            "sensitivity and monitoring fingerprints attest actual projected payloads",
        ),
        _finding(
            "sensitivity-caveats",
            not result_bearing_sensitivities
            or all(item.get("caveats") for item in result_bearing_sensitivities),
            "completeness -> Markdown",
            "optional sensitivity caveats are explicit when available",
            failure_status="WARN",
        ),
    ]
    errors = [item for item in findings if item["status"] == "FAIL"]
    warnings = [item for item in findings if item["status"] == "WARN"]
    return {
        "status": "FAIL" if errors else "WARN" if warnings else "PASS",
        "findings": findings,
        "errors": errors,
        "warnings": warnings,
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
    statuses = [output.manifest["acceptance"]["status"], semantic["status"]]
    overall_status = (
        "FAIL" if "FAIL" in statuses else "WARN" if "WARN" in statuses else "PASS"
    )
    acceptance = {
        "presentation": output.manifest["acceptance"],
        "semantic_preservation": semantic,
        "overall_status": overall_status,
    }
    manifest = dict(output.manifest)
    manifest["schema_version"] = "field-acceptance-result@1.5.12"
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
    failed = [
        item.case_id
        for item in outputs
        if item.manifest["acceptance"]["overall_status"] == "FAIL"
    ]
    if failed:
        raise FieldAcceptanceError(
            f"v1.5.12 semantic-preservation field acceptance failed: {failed}"
        )
    return outputs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render v1.5.12 semantic-preservation field acceptance"
    )
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
    statuses = [item.manifest["acceptance"]["overall_status"] for item in outputs]
    summary = {
        "status": "WARN" if "WARN" in statuses else "PASS",
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
