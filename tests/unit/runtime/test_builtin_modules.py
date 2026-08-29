from datetime import datetime, timezone

from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.plugins.builtins import BuiltinPluginProvider
from research_os.plugins.registry import PluginRegistry
from research_os.runtime.builtin_modules import (
    BusinessModelModule,
    CapitalEfficiencyModule,
    DecisionModule,
    DriverThesisModule,
    ExpectationModule,
    FinancialSanityModule,
    ForecastDisciplineModule,
    FundingLoopModule,
    IndustryKpiModule,
    PITLineageModule,
    RepositoryPreflightModule,
    StrategyResolutionModule,
    TemporalModule,
    ValuationModule,
    build_builtin_modules,
)
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.runtime.state import ResearchStateView


EXPECTED_IDS = {
    "core:repository-preflight",
    "core:pit-lineage",
    "core:financial-sanity",
    "core:business-model",
    "core:strategy-resolution",
    "core:industry-kpi",
    "core:capital-efficiency",
    "core:funding-loop",
    "core:driver-thesis",
    "core:expectation",
    "core:forecast-discipline",
    "core:valuation",
    "core:decision",
    "core:temporal",
}


def _evidence(source_table, value):
    ts = datetime(2026, 8, 1, tzinfo=timezone.utc)
    return Evidence(
        evidence_id=f"ev:{source_table}",
        company_id="synthetic:manufacturer",
        evidence_type=EvidenceType.FILING_FACT,
        publish_ts=ts,
        ingested_at=ts,
        value=value,
        source_table=source_table,
        confidence_grade=ConfidenceGrade.A,
        verification_status=VerificationStatus.PRIMARY_VERIFIED,
    )


def _context():
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
    evidence = [_evidence(k, v) for k, v in facts.items()]
    return ResearchContext(
        run_id="run:builtin-modules",
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
        facts=LegacyFactView(
            values=facts,
            evidence_by_fact={k: [f"ev:{k}"] for k in facts},
        ),
        options=ResearchOptions(),
    )


def _registry():
    registry = PluginRegistry(core_api_version="1.0", research_os_version="1.3.0")
    for plugin in BuiltinPluginProvider().plugins():
        registry.register(plugin)
    return registry


def test_builtin_module_contracts_are_stable_and_explicit():
    modules = build_builtin_modules(registry=_registry())
    assert {module.spec.module_id for module in modules} == EXPECTED_IDS
    for module in modules:
        assert module.spec.module_version
        assert module.spec.provides
        assert all(capability.strip() for capability in module.spec.provides)
        assert all(capability.strip() for capability in module.spec.requires)


def test_forecast_discipline_is_explicitly_not_applicable():
    result = ForecastDisciplineModule().run(_context(), ResearchStateView({}))
    assert result.status == "NOT_APPLICABLE"
    assert "forecast.discipline" in result.artifacts


def test_pit_business_model_strategy_and_kpi_modules_form_a_valid_chain():
    context = _context()
    pit = PITLineageModule().run(context, ResearchStateView({}))
    assert pit.status == "PASS"
    profile = BusinessModelModule().run(
        context,
        ResearchStateView({"evidence.pit": pit.artifacts["evidence.pit"]}),
    )
    assert profile.status == "PASS"
    assert profile.artifacts["business_model.profile"].primary_model == "manufacturing"

    strategy = StrategyResolutionModule(registry=_registry()).run(
        context,
        ResearchStateView({"business_model.profile": profile.artifacts["business_model.profile"]}),
    )
    assert strategy.status == "PASS"
    assert strategy.artifacts["strategy.resolution"].industry_plugins[0].plugin_id == "industry:manufacturing"

    kpi = IndustryKpiModule(registry=_registry()).run(
        context,
        ResearchStateView({
            "business_model.profile": profile.artifacts["business_model.profile"],
            "strategy.resolution": strategy.artifacts["strategy.resolution"],
        }),
    )
    assert kpi.status == "PASS"
    assert kpi.artifacts["kpi.pack_ids"] == ["manufacturing"]
    assert any(metric.evidence_ids for metric in kpi.artifacts["kpi.metrics"] if metric.status == "valid")


def test_module_classes_are_constructible_without_legacy_request():
    registry = _registry()
    modules = [
        RepositoryPreflightModule(),
        PITLineageModule(),
        FinancialSanityModule(),
        BusinessModelModule(),
        StrategyResolutionModule(registry=registry),
        IndustryKpiModule(registry=registry),
        CapitalEfficiencyModule(),
        FundingLoopModule(),
        DriverThesisModule(),
        ExpectationModule(),
        ForecastDisciplineModule(),
        ValuationModule(),
        DecisionModule(),
        TemporalModule(),
    ]
    assert {m.spec.module_id for m in modules} == EXPECTED_IDS
