from datetime import datetime, timezone

from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.plugins.builtins import BuiltinPluginProvider
from research_os.plugins.registry import PluginRegistry
from research_os.runtime.builtin_modules import (
    BusinessModelModule,
    IndustryKpiModule,
    PITLineageModule,
    StrategyResolutionModule,
)
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.runtime.engine import ResearchEngine


def test_dependency_engine_runs_core_router_strategy_kpi_pipeline_deterministically():
    ts = datetime(2026, 8, 1, tzinfo=timezone.utc)
    facts = {
        "business_description": "precision manufacturing",
        "revenue": 1000.0,
        "net_profit_parent": 50.0,
        "assets_begin": 800.0,
        "assets_end": 900.0,
        "equity_begin": 400.0,
        "equity_end": 450.0,
        "period_type": "FY",
    }
    evidence = [
        Evidence(
            evidence_id=f"ev:{key}",
            company_id="synthetic:manufacturer",
            evidence_type=EvidenceType.FILING_FACT,
            publish_ts=ts,
            ingested_at=ts,
            value=value,
            source_table=key,
            confidence_grade=ConfidenceGrade.A,
            verification_status=VerificationStatus.PRIMARY_VERIFIED,
        )
        for key, value in facts.items()
    ]
    context = ResearchContext(
        run_id="run:pipeline-statuses",
        company=CompanyRef(company_id="synthetic:manufacturer"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version="1.3.0",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(values=facts, evidence_by_fact={key: [f"ev:{key}"] for key in facts}),
        options=ResearchOptions(),
    )
    registry = PluginRegistry(core_api_version="1.0", research_os_version="1.3.0")
    for plugin in BuiltinPluginProvider().plugins():
        registry.register(plugin)

    state = ResearchEngine([
        PITLineageModule(),
        BusinessModelModule(),
        StrategyResolutionModule(registry=registry),
        IndustryKpiModule(registry=registry),
    ]).run(context)

    assert state.module_results["core:pit-lineage"].status == "PASS"
    assert state.module_results["core:business-model"].status == "PASS"
    assert state.module_results["core:strategy-resolution"].status == "PASS"
    assert state.module_results["core:industry-kpi"].status == "PASS"
    assert state.artifacts["kpi.pack_ids"] == ["manufacturing"]
