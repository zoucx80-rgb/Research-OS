#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_os.application import ResearchApplication, ResearchRunCommand  # noqa: E402
from research_os.application.bootstrap import RepositoryAttestation  # noqa: E402
from research_os.application.command import (  # noqa: E402
    FinancialResearchInput,
    MonitoringResearchInput,
    ResearchRunOptions,
    ThesisResearchInput,
    ValuationModelInput,
    ValuationResearchInput,
)
from research_os.contracts.artifact_values import (  # noqa: E402
    AssumptionRef,
    CashFlowQualityInput,
    FinancialSeriesPoint,
    FinancialTimeSeries,
    ModelFitnessInputs,
    MonitoringRule,
    OperatingObservation,
    ResearchAssertion,
    Thesis,
    ValuationRange,
    ValuationRationale,
    VerificationEvent,
)
from research_os.contracts.values import AccountingScope  # noqa: E402
from research_os.domain.evidence import Evidence  # noqa: E402
from research_os.period.models import ReportingPeriod  # noqa: E402
from research_os.presentation import ProfessionalPresentationPipeline  # noqa: E402
from research_os.reporting import ResearchReportComposer, ResearchViewPresenter  # noqa: E402
from research_os.runtime import (  # noqa: E402
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.runtime.core_artifacts import (  # noqa: E402
    BUSINESS_MODEL_PROFILE,
    CASH_FLOW_QUALITY_BRIDGE,
    DECISION_RECORD,
    FINANCIAL_TIME_SERIES,
    MONITORING_PLAN,
    RESEARCH_READINESS,
    THESIS_PORTFOLIO,
    VALUATION_RECONCILIATION,
    VALUATION_ROUTING,
)
from research_os.semantics.preservation import SemanticPreservationValidator  # noqa: E402
from research_os.snapshots.service import SnapshotService  # noqa: E402
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION  # noqa: E402


class FieldAcceptanceError(RuntimeError):
    pass


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


def _git(repository_root: Path, *args: str) -> str:
    return subprocess.check_output(("git", "-C", str(repository_root), *args), text=True).strip()


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise FieldAcceptanceError(f"timestamp must be timezone-aware: {value}")
    return parsed.astimezone(timezone.utc)


def _fixture(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise FieldAcceptanceError(f"fixture must be an object: {path}")
    return value


def _merge_case(repository_root: Path, spec: dict[str, Any]) -> dict[str, Any]:
    base = _fixture(repository_root / str(spec["source_fixture"]))
    supplement_path = spec.get("supplement_fixture")
    if not supplement_path:
        return base
    supplement = _fixture(repository_root / str(supplement_path))
    evidence_by_id = {item["evidence_id"]: item for item in base.get("evidence", [])}
    for item in supplement.get("evidence", []):
        evidence_by_id[item["evidence_id"]] = item
    merged = dict(base)
    merged["evidence"] = list(evidence_by_id.values())
    merged["inputs"] = {**base.get("inputs", {}), **supplement.get("inputs", {})}
    return merged


def _evidence(case: dict[str, Any], decision_ts: datetime) -> tuple[Evidence, ...]:
    defaults = dict(case.get("evidence_defaults", {}))
    company_id = str(case["company"]["company_id"])
    items: list[Evidence] = []
    for raw in case.get("evidence", []):
        values = {**defaults, **raw}
        period_end = values.get("period_end")
        items.append(
            Evidence(
                evidence_id=str(values["evidence_id"]),
                company_id=company_id,
                evidence_type=str(values.get("evidence_type", "filing_fact")),
                period_end=date.fromisoformat(period_end) if period_end else None,
                period=values.get("period"),
                publish_ts=_dt(str(values["publish_ts"])),
                ingested_at=decision_ts,
                value=values.get("value"),
                unit=values.get("unit"),
                scope=values.get("scope"),
                version=values.get("version"),
                source_document_id=values.get("source_document_id"),
                source_table=values.get("source_table"),
                source_url=values.get("source_url"),
                confidence_grade=str(values.get("confidence_grade", "A")),
                verification_status=str(values.get("verification_status", "PRIMARY_VERIFIED")),
                dataset_version=values.get("dataset_version"),
                parser_version=values.get("parser_version"),
                formula_version=values.get("formula_version"),
                comparison_basis=values.get("comparison_basis"),
            )
        )
    return tuple(items)


def _facts(
    case: dict[str, Any],
    evidence_view: EvidenceView,
) -> tuple[dict[str, Any], dict[str, tuple[Any, ...]]]:
    refs_by_id = {item.evidence_id: item for item in evidence_view.refs()}
    values: dict[str, Any] = {}
    refs_by_fact: dict[str, tuple[Any, ...]] = {}
    for raw in case.get("evidence", []):
        fact_id = raw.get("source_table")
        if not fact_id:
            continue
        values[str(fact_id)] = raw.get("value")
        refs_by_fact[str(fact_id)] = (refs_by_id[str(raw["evidence_id"])],)
    return values, refs_by_fact


def _financial_input(
    case: dict[str, Any],
    values: dict[str, Any],
    refs_by_fact: dict[str, tuple[Any, ...]],
) -> FinancialResearchInput:
    defaults = case.get("evidence_defaults", {})
    period = str(defaults.get("period", "current"))
    period_end = _dt(f"{defaults.get('period_end', '2026-06-30')}T00:00:00Z")
    units = {
        "revenue": "CNY",
        "net_profit_parent": "CNY",
        "net_profit": "CNY",
        "gross_margin": "ratio",
        "operating_cash_flow": "CNY",
        "capex_cash": "CNY",
    }
    series = []
    for metric_id, unit in units.items():
        if values.get(metric_id) is None:
            continue
        series.append(
            FinancialTimeSeries(
                metric_id=metric_id,
                unit=unit,
                points=(
                    FinancialSeriesPoint(
                        period=period,
                        period_end=period_end,
                        value=values[metric_id],
                        evidence_refs=refs_by_fact.get(metric_id, ()),
                    ),
                ),
            )
        )

    observation_ids = (
        "derecognized_receivables",
        "financing_cost",
        "short_debt",
        "right_of_use_assets_to_assets",
        "lease_liabilities_to_assets",
        "fixed_asset_to_assets",
    )
    observations = tuple(
        OperatingObservation(
            category="reported_or_derived",
            metric_id=metric_id,
            value=values[metric_id],
            unit=("ratio" if metric_id.endswith("_to_assets") else "CNY"),
            period=period,
            evidence_refs=refs_by_fact.get(metric_id, ()),
        )
        for metric_id in observation_ids
        if values.get(metric_id) is not None
    )

    net_profit_key = (
        "net_profit_parent" if values.get("net_profit_parent") is not None else "net_profit"
    )
    cash_refs = tuple(
        ref
        for key in (net_profit_key, "operating_cash_flow", "capex_cash")
        for ref in refs_by_fact.get(key, ())
    )
    cash_flow = None
    if values.get(net_profit_key) is not None or values.get("operating_cash_flow") is not None:
        cash_flow = CashFlowQualityInput(
            net_profit=values.get(net_profit_key),
            operating_cash_flow=values.get("operating_cash_flow"),
            capex_cash=values.get("capex_cash"),
            unit="CNY",
            evidence_refs=cash_refs,
        )
    return FinancialResearchInput(
        time_series=tuple(series),
        operating_observations=observations,
        cash_flow_quality=cash_flow,
    )


def _thesis_input(
    case: dict[str, Any], refs_by_fact: dict[str, tuple[Any, ...]]
) -> ThesisResearchInput:
    inputs = case.get("inputs", {})
    refs_by_id = {ref.evidence_id: ref for fact_refs in refs_by_fact.values() for ref in fact_refs}
    prior_theses = []
    for item in inputs.get("prior_theses", []):
        evidence_ids = tuple(str(value) for value in item.get("evidence_ids", []))
        missing_ids = tuple(value for value in evidence_ids if value not in refs_by_id)
        if missing_ids:
            raise FieldAcceptanceError(
                f"prior thesis {item['thesis_key']} has unknown evidence: {', '.join(missing_ids)}"
            )
        next_check_date = item.get("next_check_date")
        prior_theses.append(
            Thesis(
                thesis_key=str(item["thesis_key"]),
                company_id=str(case["company"]["company_id"]),
                title=str(item["title"]),
                statement=str(item["statement"]),
                mechanism=str(item["mechanism"]),
                anti_thesis=str(item["anti_thesis"]),
                status=str(item["status"]),
                falsifier_statements=tuple(
                    str(value) for value in item.get("falsifier_statements", [])
                ),
                next_check_date=(
                    date.fromisoformat(str(next_check_date)) if next_check_date else None
                ),
                confidence=item.get("confidence"),
                claim_strength=str(item.get("claim_strength", "OBSERVED")),
                evidence_refs=tuple(refs_by_id[value] for value in evidence_ids),
            )
        )
    cycle_support = None
    if inputs.get("cycle_turning_point_support") is not None:
        cycle_support = ResearchAssertion(
            assertion_key="cycle-turning-point",
            statement="已观察到周期修复迹象，但周期底部尚未确认",
            status="SUPPORTED",
            evidence_refs=tuple(
                ref
                for key in ("gross_margin", "margin_change")
                for ref in refs_by_fact.get(key, ())
            ),
        )
    moat = []
    for index, item in enumerate(inputs.get("moat_evidence", []), start=1):
        refs = tuple(
            ref
            for evidence_id in item.get("evidence_ids", [])
            for fact_refs in refs_by_fact.values()
            for ref in fact_refs
            if ref.evidence_id == evidence_id
        )
        moat.append(
            ResearchAssertion(
                assertion_key=f"barrier-{index}",
                statement="存在技术或资格壁垒证据，但经济护城河尚未确认",
                status="SUPPORTED",
                evidence_refs=refs,
            )
        )
    return ThesisResearchInput(
        cycle_recovery_observed=inputs.get("cycle_recovery_observed"),
        cycle_turning_point_support=cycle_support,
        moat_evidence=tuple(moat),
        prior_theses=tuple(prior_theses),
    )


def _valuation_input(case: dict[str, Any]) -> ValuationResearchInput:
    inputs = case.get("inputs", {})
    models = tuple(
        ValuationModelInput(model_id=model_id, fitness=ModelFitnessInputs(**fitness))
        for model_id, fitness in inputs.get("valuation_models", {}).items()
    )
    ranges = tuple(
        ValuationRange(
            range_key=str(item.get("range_key") or item.get("range_id")),
            low=item["low"],
            high=item["high"],
            basis=str(item["basis"]),
            currency=str(item["currency"]),
            role=str(item["role"]),
        )
        for item in inputs.get("valuation_ranges", [])
    )
    rationales = tuple(
        ValuationRationale(
            model_key=str(item.get("model_key") or item.get("model_id")),
            rationale=str(item.get("rationale") or item.get("explanation") or ""),
        )
        for item in inputs.get("valuation_rationales", [])
    )
    return ValuationResearchInput(models=models, ranges=ranges, rationales=rationales)


def _monitoring_assumption(item: dict[str, Any]) -> AssumptionRef:
    rule_key = str(item.get("rule_key") or item.get("rule_id"))
    payload = {
        "rule_key": rule_key,
        "metric_id": str(item.get("metric_id") or item.get("metric")),
        "operator": str(item["operator"]),
        "threshold": item["threshold"],
        "frequency": str(item["frequency"]),
        "rationale": str(item["rationale"]),
        "source_type": str(item.get("source_type") or "analyst_assumption"),
        "threshold_source": str(item.get("threshold_source") or ""),
    }
    fingerprint = sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return AssumptionRef(
        assumption_key=f"field-monitoring:{rule_key}",
        assumption_version="1",
        content_fingerprint=fingerprint,
    )


def _monitoring_input(case: dict[str, Any]) -> MonitoringResearchInput:
    inputs = case.get("inputs", {})
    rules = []
    for item in inputs.get("monitoring_rules", []):
        assumption_refs = ()
        if item.get("source_type") == "analyst_assumption":
            assumption_refs = (_monitoring_assumption(item),)
        rules.append(
            MonitoringRule(
                rule_key=str(item.get("rule_key") or item.get("rule_id")),
                metric_id=str(item.get("metric_id") or item.get("metric")),
                operator=str(item["operator"]),
                threshold=item["threshold"],
                frequency=str(item["frequency"]),
                rationale=str(item["rationale"]),
                assumption_refs=assumption_refs,
            )
        )
    event = inputs.get("next_verification_event")
    next_event = None
    if event:
        next_event = VerificationEvent(
            event_key="next-verification-event",
            label=str(event["event_name"]),
            event_type="periodic_report",
            due_ts=_dt(str(event["event_time"])),
            status="scheduled",
        )
    return MonitoringResearchInput(
        monitoring_rules=tuple(rules), next_verification_event=next_event
    )


def _command(case: dict[str, Any], *, commit_sha: str) -> ResearchRunCommand:
    decision_ts = _dt(str(case["decision_ts"]))
    company_id = str(case["company"]["company_id"])
    evidence = _evidence(case, decision_ts)
    evidence_view = EvidenceView(evidence, company_id=company_id, decision_ts=decision_ts)
    values, refs_by_fact = _facts(case, evidence_view)
    return ResearchRunCommand(
        context=ResearchContext(
            run_id=f"field:v1.6.01:{case['case_id']}",
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
                evidence_refs_by_fact=refs_by_fact,
                reporting_period=ReportingPeriod.from_facts(values),
                accounting_scope=AccountingScope(),
            ),
        ),
        financial=_financial_input(case, values, refs_by_fact),
        thesis=_thesis_input(case, refs_by_fact),
        valuation=_valuation_input(case),
        monitoring=_monitoring_input(case),
        options=ResearchRunOptions(persist_snapshot=False),
    )


def _machine_semantics(command: ResearchRunCommand, result: Any, view: Any, document: Any) -> str:
    versions = result.versions
    semantic = SemanticPreservationValidator.validate_reporting_chain(
        result=result,
        view=view,
        document=document,
    )
    snapshot_service = SnapshotService()
    snapshot = snapshot_service.build(command=command, result=result)
    descriptor = snapshot_service.describe(snapshot)
    valid = snapshot_service.verify(snapshot, integrity_digest=descriptor.integrity_digest).valid
    portfolio = result.artifacts.require(THESIS_PORTFOLIO)
    readiness_matches = result.artifacts.require(RESEARCH_READINESS) == result.research_readiness
    checks = (
        versions.core_api_version == "2.0",
        versions.plugin_api_version == "2.0",
        versions.snapshot_schema_version == "2.0",
        semantic.status == "PASS",
        snapshot.schema_version == "2.0",
        valid,
        portfolio.schema_version == "2.0" if hasattr(portfolio, "schema_version") else True,
        readiness_matches,
    )
    return "PASS" if all(checks) else "FAIL"


def _research_depth(result: Any) -> str:
    profile = result.artifacts.require(BUSINESS_MODEL_PROFILE)
    if profile.classification_status != "CLASSIFIED":
        return "FAIL"
    base_keys = (
        FINANCIAL_TIME_SERIES,
        CASH_FLOW_QUALITY_BRIDGE,
        VALUATION_ROUTING,
        MONITORING_PLAN,
    )
    base_supported = all(
        getattr(result.artifacts.require(key), "domain_status", None) == "SUPPORTED"
        for key in base_keys
    )
    reconciliation = result.artifacts.require(VALUATION_RECONCILIATION)
    if base_supported and reconciliation.domain_status == "SUPPORTED":
        return "PASS"
    return "LIMITED"


def _presentation(
    bundle: Any, spec: dict[str, Any], body_max_lines: int
) -> tuple[str, tuple[str, ...]]:
    errors: list[str] = []
    markdown = bundle.markdown.content
    body = markdown.split("\n## 审计附录", maxsplit=1)[0]
    body_lines = body.splitlines()
    headings = [line for line in body_lines if line.startswith("## ")]
    if not headings or headings[0] != "## 投资决策快照":
        errors.append("decision snapshot is not the first body section")
    if len(body_lines) > body_max_lines:
        errors.append(f"investor body exceeds {body_max_lines} lines")
    if re.search(r"\b[0-9a-f]{64}\b", body):
        errors.append("lineage hash leaked into investor body")
    for term in spec.get("required_body_terms", []):
        if term not in body:
            errors.append(f"required body term missing: {term}")
    for term in spec.get("forbidden_body_terms", []):
        if term in body:
            errors.append(f"forbidden body term present: {term}")
    for term in spec.get("forbidden_anywhere_terms", []):
        if term in markdown:
            errors.append(f"forbidden report term present: {term}")
    html = bundle.html.content
    if 'id="decision"' not in html or "report-section-1" in html:
        errors.append("stable section-id presentation contract not satisfied")
    if not bundle.pdf.content.startswith(b"%PDF"):
        errors.append("invalid PDF header")
    if not all((bundle.markdown.content_hash, bundle.html.content_hash, bundle.pdf.content_hash)):
        errors.append("presentation hash missing")
    return ("PASS" if not errors else "FAIL"), tuple(errors)


def render_case(
    spec: dict[str, Any],
    *,
    repository_root: Path,
    output_dir: Path,
    commit_sha: str,
    body_max_lines: int,
) -> dict[str, Any]:
    case = _merge_case(repository_root, spec)
    command = _command(case, commit_sha=commit_sha)
    result = ResearchApplication.build(repository_attestor=_Attestor(commit_sha)).run(command)
    profile = result.artifacts.require(BUSINESS_MODEL_PROFILE)
    if profile.primary_model != spec["expected_primary_model"]:
        raise FieldAcceptanceError(f"{spec['case_id']} primary model mismatch")

    view = ResearchViewPresenter().present(result)
    document = ResearchReportComposer().compose(view)
    bundle = ProfessionalPresentationPipeline().render(document)
    machine_semantics = _machine_semantics(command, result, view, document)
    research_depth = _research_depth(result)
    presentation, presentation_errors = _presentation(bundle, spec, body_max_lines)
    decision = result.artifacts.require(DECISION_RECORD)

    if machine_semantics != "PASS":
        raise FieldAcceptanceError(f"{spec['case_id']} machine semantics failed")
    if research_depth != spec["expected_research_depth"]:
        raise FieldAcceptanceError(f"{spec['case_id']} research depth mismatch: {research_depth}")
    expected_decision = spec.get("expected_decision_state")
    if expected_decision and decision.state != expected_decision:
        raise FieldAcceptanceError(f"{spec['case_id']} decision mismatch: {decision.state}")
    if presentation != "PASS":
        raise FieldAcceptanceError(f"{spec['case_id']} presentation failed: {presentation_errors}")

    case_dir = output_dir / str(spec["case_id"])
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "report.md").write_text(bundle.markdown.content, encoding="utf-8")
    (case_dir / "report.html").write_text(bundle.html.content, encoding="utf-8")
    (case_dir / "report.pdf").write_bytes(bundle.pdf.content)
    manifest = {
        "case_id": spec["case_id"],
        "commit_sha": commit_sha,
        "research_os_version": RESEARCH_OS_VERSION,
        "primary_model": profile.primary_model,
        "execution_completion": result.execution_completion.final_status,
        "research_readiness": result.research_readiness.final_status,
        "machine_semantics": machine_semantics,
        "research_depth": research_depth,
        "presentation": presentation,
        "decision_state": decision.state,
        "artifact_ids": [item.key.artifact_id for item in result.artifacts.envelopes()],
        "semantic_fingerprint": view.semantic_fingerprint,
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
    parser.add_argument(
        "--case-manifest",
        type=Path,
        default=Path("tests/fixtures/field_acceptance/v1_6_01/cases.json"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    parser.add_argument("--commit-sha")
    args = parser.parse_args()

    repository_root = args.repository_root.resolve()
    actual_sha = _git(repository_root, "rev-parse", "HEAD")
    commit_sha = args.commit_sha or actual_sha
    if actual_sha != commit_sha:
        raise FieldAcceptanceError("current field acceptance commit does not match HEAD")
    manifest = _fixture(repository_root / args.case_manifest)
    specs = manifest.get("cases", [])
    if {item["case_id"] for item in specs} != {"300034.SZ", "001287.SZ", "301073.SZ"}:
        raise FieldAcceptanceError("v1.6.01 field acceptance requires exactly three real companies")
    output = [
        render_case(
            spec,
            repository_root=repository_root,
            output_dir=args.output_dir,
            commit_sha=commit_sha,
            body_max_lines=int(manifest.get("body_max_lines", 350)),
        )
        for spec in specs
    ]
    (args.output_dir / "manifest.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("FIELD ACCEPTANCE VERIFIED: v1.6.01")


if __name__ == "__main__":
    main()
