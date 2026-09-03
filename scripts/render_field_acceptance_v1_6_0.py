from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from research_os.application import ResearchApplication, ResearchRunCommand
from research_os.application.bootstrap import RepositoryAttestation
from research_os.application.command import ResearchRunOptions
from research_os.contracts.artifact_values import ThesisPortfolio
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
from research_os.period.models import ReportingPeriod
from research_os.presentation import ProfessionalPresentationPipeline
from research_os.reporting import ResearchReportComposer, ResearchViewPresenter
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.runtime.core_artifacts import (
    BUSINESS_MODEL_PROFILE,
    RESEARCH_READINESS,
    THESIS_PORTFOLIO,
)
from research_os.semantics.preservation import SemanticPreservationValidator
from research_os.snapshots.service import SnapshotService
from research_os.valuation.reconciliation import (
    ValuationRange as ReconciliationRange,
    ValuationReconciler,
)
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


class FieldAcceptanceError(RuntimeError):
    pass


_ALLOWED_ACCEPTANCE_STATES = {
    "machine_semantics": frozenset(("PASS", "FAIL")),
    "research_depth": frozenset(("PASS", "LIMITED", "FAIL")),
    "presentation": frozenset(("PASS", "FAIL")),
}


def _acceptance_statuses(case: dict[str, Any]) -> dict[str, str]:
    statuses = {
        "machine_semantics": str(case.get("expected_machine_semantics", "")),
        "research_depth": str(case.get("expected_research_depth", "")),
        "presentation": str(case.get("expected_presentation", "")),
    }
    for dimension, status in statuses.items():
        if status not in _ALLOWED_ACCEPTANCE_STATES[dimension]:
            raise FieldAcceptanceError(
                f"{case.get('case_id', '<unknown>')} invalid {dimension}: {status!r}"
            )
    return statuses


def _git(repository_root: Path, *args: str) -> str:
    return subprocess.check_output(
        ("git", "-C", str(repository_root), *args), text=True
    ).strip()


class _Attestor:
    def __init__(self, commit_sha: str) -> None:
        self._commit_sha = commit_sha

    def attest(self) -> RepositoryAttestation:
        return RepositoryAttestation(
            repository_host="github.com",
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            head_sha=self._commit_sha,
        )


def _command(case: dict[str, Any], *, commit_sha: str) -> ResearchRunCommand:
    decision_ts = datetime.fromisoformat(str(case["decision_ts"]))
    company_id = str(case["company_id"])
    values = dict(case.get("values", {}))
    evidence = tuple(
        Evidence(
            evidence_id=f"{case['case_id']}:{fact_id}",
            revision_no=1,
            company_id=company_id,
            evidence_type="filing_fact",
            publish_ts=decision_ts,
            ingested_at=decision_ts,
            period="2025",
            source_table=fact_id,
            value=value,
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        )
        for fact_id, value in values.items()
    )
    evidence_view = EvidenceView(
        evidence,
        company_id=company_id,
        decision_ts=decision_ts,
    )
    refs = {
        reference.evidence_id.split(":", maxsplit=1)[1]: reference
        for reference in evidence_view.refs()
    }
    return ResearchRunCommand(
        context=ResearchContext(
            run_id=f"field:v1.6.0:{case['case_id']}",
            company=CompanyRef(company_id=company_id),
            decision_ts=decision_ts,
            baseline=BaselineFingerprint(
                repository_full_name="zoucx80-rgb/Research-OS",
                repository_id=1350382205,
                branch="main",
                commit_sha=commit_sha,
                research_os_version=RESEARCH_OS_VERSION,
                core_api_version=CORE_API_VERSION,
            ),
            evidence=evidence_view,
            facts=FactView(
                company_id=company_id,
                decision_ts=decision_ts,
                values=values,
                evidence_refs_by_fact={
                    fact_id: (refs[fact_id],) for fact_id in values
                },
                reporting_period=ReportingPeriod(period_type="FY"),
                accounting_scope=AccountingScope(),
            ),
        ),
        options=ResearchRunOptions(persist_snapshot=False),
    )


def _valuation_reconciliation(case: dict[str, Any]):
    ranges = tuple(
        ReconciliationRange.model_validate(item)
        for item in case.get("valuation_ranges", ())
    )
    return ValuationReconciler.reconcile(ranges)


def _machine_semantics_status(
    *,
    command: ResearchRunCommand,
    result: Any,
    view: Any,
    document: Any,
) -> tuple[str, str]:
    versions = result.versions
    plugin_versions_are_v2 = all(
        item.plugin_api_version == "2.0"
        for item in (
            *result.strategy_resolution.industry_plugins,
            *result.strategy_resolution.methodology_plugins,
        )
    )
    artifacts_are_v2 = all(
        envelope.key.schema_version == "2.0"
        for envelope in result.artifacts.envelopes()
    )
    readiness_artifact_matches = (
        result.artifacts.require(RESEARCH_READINESS) == result.research_readiness
    )
    portfolio = result.artifacts.require(THESIS_PORTFOLIO)
    typed_portfolio = isinstance(portfolio, ThesisPortfolio)
    semantic = SemanticPreservationValidator.validate_reporting_chain(
        result=result,
        view=view,
        document=document,
    )
    snapshot_service = SnapshotService()
    snapshot = snapshot_service.build(command=command, result=result)
    descriptor = snapshot_service.describe(snapshot)
    snapshot_valid = snapshot_service.verify(
        snapshot,
        integrity_digest=descriptor.integrity_digest,
    ).valid
    valid = all(
        (
            versions.core_api_version == "2.0",
            versions.plugin_api_version == "2.0",
            versions.snapshot_schema_version == "2.0",
            plugin_versions_are_v2,
            artifacts_are_v2,
            readiness_artifact_matches,
            typed_portfolio,
            semantic.status == "PASS",
            snapshot.schema_version == "2.0",
            snapshot_valid,
        )
    )
    return ("PASS" if valid else "FAIL"), semantic.status


def _research_depth_status(case: dict[str, Any], profile: Any) -> tuple[str, str]:
    reconciliation = _valuation_reconciliation(case)
    full_valuation = reconciliation.status in {"INTERSECTION", "CROSS_CHECK_BAND"}
    classified = profile.classification_status == "CLASSIFIED"
    return (
        "PASS" if classified and full_valuation else "LIMITED",
        reconciliation.status,
    )


def _presentation_status(bundle: Any) -> str:
    valid = all(
        (
            bool(bundle.markdown.content.strip()),
            bool(bundle.html.content.strip()),
            bool(bundle.pdf.content),
            bundle.pdf.content.startswith(b"%PDF"),
            bool(bundle.markdown.content_hash),
            bool(bundle.html.content_hash),
            bool(bundle.pdf.content_hash),
        )
    )
    return "PASS" if valid else "FAIL"


def render_case(
    case_path: Path,
    *,
    output_dir: Path,
    commit_sha: str,
) -> dict[str, Any]:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    if not isinstance(case, dict):
        raise FieldAcceptanceError("field acceptance case must be an object")
    expected_statuses = _acceptance_statuses(case)
    command = _command(case, commit_sha=commit_sha)
    result = ResearchApplication.build(
        repository_attestor=_Attestor(commit_sha)
    ).run(command)
    profile = result.artifacts.require(BUSINESS_MODEL_PROFILE)
    if profile.primary_model != case["expected_primary_model"]:
        raise FieldAcceptanceError(
            f"{case['case_id']} primary model mismatch: {profile.primary_model}"
        )
    expected_completion = case.get("expected_completion")
    if expected_completion and result.execution_completion.final_status != expected_completion:
        raise FieldAcceptanceError(f"{case['case_id']} completion mismatch")
    expected_readiness = case.get("expected_readiness")
    if expected_readiness and result.research_readiness.final_status != expected_readiness:
        raise FieldAcceptanceError(f"{case['case_id']} readiness mismatch")

    view = ResearchViewPresenter().present(result)
    document = ResearchReportComposer().compose(view)
    semantic_status, preservation_status = _machine_semantics_status(
        command=command,
        result=result,
        view=view,
        document=document,
    )
    research_depth, reconciliation_status = _research_depth_status(case, profile)
    bundle = ProfessionalPresentationPipeline().render(document)
    presentation_status = _presentation_status(bundle)
    actual_statuses = {
        "machine_semantics": semantic_status,
        "research_depth": research_depth,
        "presentation": presentation_status,
    }
    if actual_statuses != expected_statuses:
        raise FieldAcceptanceError(
            f"{case['case_id']} acceptance status mismatch: "
            f"expected={expected_statuses}, actual={actual_statuses}"
        )

    case_dir = output_dir / str(case["case_id"])
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "report.md").write_text(bundle.markdown.content, encoding="utf-8")
    (case_dir / "report.html").write_text(bundle.html.content, encoding="utf-8")
    (case_dir / "report.pdf").write_bytes(bundle.pdf.content)
    manifest = {
        "case_id": case["case_id"],
        "company_id": case["company_id"],
        "commit_sha": commit_sha,
        "research_os_version": RESEARCH_OS_VERSION,
        "core_api_version": CORE_API_VERSION,
        "plugin_api_version": result.versions.plugin_api_version,
        "snapshot_schema_version": result.versions.snapshot_schema_version,
        "primary_model": profile.primary_model,
        "execution_completion": result.execution_completion.final_status,
        "research_readiness": result.research_readiness.final_status,
        "machine_semantics": actual_statuses["machine_semantics"],
        "research_depth": actual_statuses["research_depth"],
        "presentation": actual_statuses["presentation"],
        "semantic_preservation": preservation_status,
        "thesis_portfolio_schema": THESIS_PORTFOLIO.schema_version,
        "valuation_reconciliation": reconciliation_status,
        "semantic_fingerprint": view.semantic_fingerprint,
        "document_hash": bundle.markdown.source_hash,
        "markdown_hash": bundle.markdown.content_hash,
        "html_hash": bundle.html.content_hash,
        "pdf_hash": bundle.pdf.content_hash,
    }
    (case_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--commit-sha")
    args = parser.parse_args()
    repository_root = args.repository_root.resolve()
    actual_sha = _git(repository_root, "rev-parse", "HEAD")
    commit_sha = args.commit_sha or actual_sha
    if actual_sha != commit_sha:
        raise FieldAcceptanceError("current field acceptance commit does not match HEAD")
    manifests = [
        render_case(path, output_dir=args.output_dir, commit_sha=commit_sha)
        for path in sorted(args.input_dir.glob("*.json"))
    ]
    if {item["case_id"] for item in manifests} != {
        "manufacturing_typed_architecture",
        "distributor_funding_and_valuation",
        "coverage_limited_no_plugin",
    }:
        raise FieldAcceptanceError("v1.6.0 field acceptance requires exactly three cases")


if __name__ == "__main__":
    main()
