from __future__ import annotations

from datetime import datetime, timezone
import subprocess

from research_os.application.bootstrap import BootstrapPlanCompiler, RepositoryAttestation
from research_os.application.command import ResearchRunCommand
from research_os.application.plan import ResearchPlanCompiler
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.plugins.resolver import StrategyResolution
from research_os.readiness import ResearchReadinessEvaluator
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
    ResearchEngine,
)
from research_os.runtime.core_artifacts import RESEARCH_READINESS, build_core_artifact_catalog
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


def _command() -> ResearchRunCommand:
    decision_ts = datetime(2026, 9, 2, tzinfo=timezone.utc)
    company_id = "synthetic:no-evidence"
    return ResearchRunCommand(
        context=ResearchContext(
            run_id="run:no-evidence",
            company=CompanyRef(company_id=company_id),
            decision_ts=decision_ts,
            baseline=BaselineFingerprint(
                repository_full_name="zoucx80-rgb/Research-OS",
                repository_id=1350382205,
                branch="main",
                commit_sha=subprocess.check_output(("git", "rev-parse", "HEAD"), text=True).strip(),
                research_os_version=RESEARCH_OS_VERSION,
                core_api_version=CORE_API_VERSION,
            ),
            evidence=EvidenceView([], company_id=company_id, decision_ts=decision_ts),
            facts=FactView(
                company_id=company_id,
                decision_ts=decision_ts,
                values={},
                evidence_refs_by_fact={},
                reporting_period=ReportingPeriod(period_type="FY"),
                accounting_scope=AccountingScope(),
            ),
        )
    )


def _attestation(command: ResearchRunCommand) -> RepositoryAttestation:
    baseline = command.context.baseline
    return RepositoryAttestation(
        repository_host="github.com",
        repository_full_name=baseline.repository_full_name,
        repository_id=baseline.repository_id,
        branch=baseline.branch,
        head_sha=baseline.commit_sha,
    )


def test_missing_evidence_produces_incomplete_and_not_ready_without_a_cycle():
    command = _command()
    catalog = build_core_artifact_catalog()
    engine = ResearchEngine()
    bootstrap_plan = BootstrapPlanCompiler(catalog).compile(
        command,
        attestation=_attestation(command),
    )
    bootstrap = engine.execute(bootstrap_plan, command.context, catalog)
    professional_plan = ResearchPlanCompiler(catalog).compile(
        command,
        bootstrap.snapshot,
        StrategyResolution(rationale=("no plugin coverage",)),
    )
    professional = engine.execute(professional_plan, command.context, catalog)

    results = bootstrap.module_results + professional.module_results
    finalized = engine.finalize(
        plans=(bootstrap_plan, professional_plan),
        execution=type(professional)(
            snapshot=professional.snapshot,
            module_results=results,
        ),
        catalog=catalog,
        readiness_evaluator=ResearchReadinessEvaluator(),
    )
    completion = finalized.completion
    readiness = finalized.readiness

    assert completion.final_status == "INCOMPLETE"
    assert readiness.final_status == "NOT_READY"
    assert "core:pit-lineage" in completion.blocking_capabilities
    assert not set(completion.blocking_capabilities) & {"completion", "readiness"}
    assert finalized.execution.snapshot.require(RESEARCH_READINESS) == readiness
