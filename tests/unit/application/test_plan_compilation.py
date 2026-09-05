from __future__ import annotations

from datetime import datetime, timezone

import pytest

from research_os.application.bootstrap import BootstrapPlanCompiler, RepositoryAttestation
from research_os.application.command import ResearchRunCommand
from research_os.application.plan import ResearchPlanCompiler
from research_os.contracts.artifacts import ArtifactStore, ArtifactWrite
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.plugins.models import ResolvedPlugin
from research_os.plugins.resolver import StrategyResolution
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.runtime.core_artifacts import (
    BUSINESS_MODEL_PROFILE,
    KPI_METRICS,
    STRATEGY_RESOLUTION,
    build_core_artifact_catalog,
)
from research_os.runtime.module_plan import ModulePlanCompilationError


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
                commit_sha="84eeb98d30ca5d887019c5fe24f0c61d7b3a8571",
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


def test_bootstrap_compiler_creates_only_the_four_bootstrap_modules():
    command = _command()
    plan = BootstrapPlanCompiler(build_core_artifact_catalog()).compile(
        command,
        attestation=_attestation(command),
    )

    assert plan.module_ids == (
        "core:repository-preflight",
        "core:pit-lineage",
        "core:financial-fact-snapshot",
        "core:business-model",
    )


def test_research_plan_uses_bootstrap_snapshot_and_adds_only_resolved_strategy_module():
    catalog = build_core_artifact_catalog()
    command = _command()
    bootstrap = BootstrapPlanCompiler(catalog).compile(
        command,
        attestation=_attestation(command),
    )
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            key=BUSINESS_MODEL_PROFILE,
            value=BusinessModelProfile(
                company_id=command.context.company.company_id,
                primary_model="unknown",
                confidence_band="UNKNOWN",
                classification_status="INSUFFICIENT_EVIDENCE",
            ),
            producer_id="core:business-model",
        )
    )
    snapshot = store.freeze()
    strategy = StrategyResolution(rationale=("resolved before phase B",))

    plan = ResearchPlanCompiler(catalog).compile(command, snapshot, strategy)

    assert set(plan.module_ids) == {
        "core:resolved-strategy",
        "core:kpi-provider",
        "core:professional-financial",
        "core:professional-capital",
        "core:thesis-portfolio",
        "core:professional-thesis-semantics",
        "core:professional-expectation",
        "core:professional-forecast",
        "core:professional-peers",
        "core:professional-valuation",
        "core:professional-sensitivity",
        "core:professional-monitoring",
        "core:professional-methodology",
        "core:research-sufficiency",
        "core:portfolio-decision",
    }
    assert plan.module_ids.index("core:professional-capital") < plan.module_ids.index(
        "core:professional-valuation"
    )
    assert plan.module_ids.index("core:thesis-portfolio") < plan.module_ids.index(
        "core:professional-thesis-semantics"
    )
    assert plan.module_ids.index("core:professional-valuation") < plan.module_ids.index(
        "core:portfolio-decision"
    )
    assert plan.module_ids.index("core:professional-methodology") < plan.module_ids.index(
        "core:research-sufficiency"
    )
    assert plan.module_ids.index("core:research-sufficiency") < plan.module_ids.index(
        "core:portfolio-decision"
    )
    assert plan.initial_snapshot is snapshot
    modules_by_id = {module.spec.module_id: module for module in plan.modules}
    assert modules_by_id["core:resolved-strategy"].spec.requires == frozenset(
        (BUSINESS_MODEL_PROFILE,)
    )
    assert modules_by_id["core:resolved-strategy"].spec.provides == frozenset(
        (STRATEGY_RESOLUTION,)
    )
    assert modules_by_id["core:kpi-provider"].spec.provides == frozenset((KPI_METRICS,))
    assert bootstrap.module_ids != plan.module_ids


def test_research_plan_rejects_a_resolved_plugin_missing_from_the_registry():
    catalog = build_core_artifact_catalog()
    command = _command()
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            key=BUSINESS_MODEL_PROFILE,
            value=BusinessModelProfile(
                company_id=command.context.company.company_id,
                primary_model="manufacturing",
                rule_match_score=1.0,
                usable_evidence_coverage=1.0,
                confidence_band="HIGH",
                classification_status="CLASSIFIED",
            ),
            producer_id="core:business-model",
        )
    )
    strategy = StrategyResolution(
        industry_plugins=(
            ResolvedPlugin(
                plugin_id="industry:ghost",
                plugin_type="industry",
                plugin_version="2.0.0",
                plugin_api_version="2.0",
                priority=100,
                maturity="stable",
                applicability_score=1.0,
            ),
        )
    )

    with pytest.raises(ModulePlanCompilationError, match="not registered"):
        ResearchPlanCompiler(catalog).compile(command, store.freeze(), strategy)
