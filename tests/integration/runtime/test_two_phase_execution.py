from __future__ import annotations

from datetime import datetime, timezone
import subprocess

from research_os.application.bootstrap import BootstrapPlanCompiler, RepositoryAttestation
from research_os.application.command import ResearchRunCommand
from research_os.application.plan import ResearchPlanCompiler
from research_os.contracts.evidence import EvidenceRef, EvidenceSet
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.plugins.resolver import StrategyResolution
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.runtime.core_artifacts import (
    BUSINESS_MODEL_PROFILE,
    EVIDENCE_PIT,
    FINANCIAL_FACT_SNAPSHOT,
    KPI_METRICS,
    REPOSITORY_PREFLIGHT,
    STRATEGY_RESOLUTION,
    build_core_artifact_catalog,
)
from research_os.runtime.engine import ResearchEngine


def _command() -> ResearchRunCommand:
    decision_ts = datetime(2026, 9, 2, tzinfo=timezone.utc)
    company_id = "synthetic:two-phase"
    evidence = EvidenceView([], company_id=company_id, decision_ts=decision_ts)
    return ResearchRunCommand(
        context=ResearchContext(
            run_id="run:two-phase",
            company=CompanyRef(company_id=company_id),
            decision_ts=decision_ts,
            baseline=BaselineFingerprint(
                repository_full_name="zoucx80-rgb/Research-OS",
                repository_id=1350382205,
                branch="main",
                commit_sha=subprocess.check_output(
                    ("git", "rev-parse", "HEAD"), text=True
                ).strip(),
                research_os_version="1.6.0",
                core_api_version="2.0",
            ),
            evidence=evidence,
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


def test_two_phase_execution_retains_bootstrap_and_engine_writes_precomputed_strategy():
    catalog = build_core_artifact_catalog()
    command = _command()
    engine = ResearchEngine()

    bootstrap_execution = engine.execute(
        BootstrapPlanCompiler(catalog).compile(
            command,
            attestation=_attestation(command),
        ),
        command.context,
        catalog,
    )
    applicability_ref = EvidenceRef(
        evidence_id="ev:applicability",
        revision=1,
        content_fingerprint="a" * 64,
    )
    strategy = StrategyResolution(
        rationale=("resolved before phase B",),
        evidence_refs=(applicability_ref,),
    )
    phase_b = ResearchPlanCompiler(catalog).compile(
        command,
        bootstrap_execution.snapshot,
        strategy,
    )

    professional_execution = engine.execute(
        phase_b,
        command.context,
        catalog,
        initial_snapshot=bootstrap_execution.snapshot,
    )

    assert tuple(result.module_id for result in bootstrap_execution.module_results) == (
        "core:repository-preflight",
        "core:pit-lineage",
        "core:financial-fact-snapshot",
        "core:business-model",
    )
    assert tuple(result.module_id for result in professional_execution.module_results) == (
        "core:resolved-strategy",
        "core:kpi-provider",
        "core:thesis-portfolio",
        "core:portfolio-decision",
    )
    assert professional_execution.snapshot.require(REPOSITORY_PREFLIGHT) == command.context.baseline
    assert professional_execution.snapshot.require(EVIDENCE_PIT) == EvidenceSet()
    assert professional_execution.snapshot.require(FINANCIAL_FACT_SNAPSHOT).facts == ()
    assert professional_execution.snapshot.require(BUSINESS_MODEL_PROFILE).primary_model == "unknown"
    assert professional_execution.snapshot.require(STRATEGY_RESOLUTION) == strategy
    assert professional_execution.snapshot.envelope(STRATEGY_RESOLUTION).evidence_refs == (
        applicability_ref,
    )
    assert professional_execution.snapshot.require(KPI_METRICS).metrics == ()
