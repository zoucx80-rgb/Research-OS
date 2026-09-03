from __future__ import annotations

from datetime import datetime, timezone

from research_os.application import ResearchRunOptions
from research_os.contracts.policies import PolicySnapshot
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
from research_os.metrics import builtin_metric_registry
from research_os.plugins.builtins import BuiltinPluginProvider
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolver
from research_os.period.models import ReportingPeriod
from research_os.router.models import BusinessModelProfile
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)


DECISION_TS = datetime(2026, 9, 2, tzinfo=timezone.utc)
COMPANY_ID = "synthetic:plugin-services"


def _context() -> ResearchContext:
    values = {
        "business_description": "precision manufacturing",
        "revenue": 1_000.0,
        "net_profit_parent": 50.0,
        "assets_begin": 800.0,
        "assets_end": 900.0,
        "equity_begin": 400.0,
        "equity_end": 450.0,
    }
    evidence = tuple(
        Evidence(
            evidence_id=f"ev:{fact_id}",
            revision_no=1,
            company_id=COMPANY_ID,
            evidence_type="filing_fact",
            publish_ts=DECISION_TS,
            ingested_at=DECISION_TS,
            value=value,
            source_table=fact_id,
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        )
        for fact_id, value in values.items()
    )
    evidence_view = EvidenceView(
        evidence,
        company_id=COMPANY_ID,
        decision_ts=DECISION_TS,
    )
    refs = {ref.evidence_id.removeprefix("ev:"): ref for ref in evidence_view.refs()}
    return ResearchContext(
        run_id="run:plugin-services",
        company=CompanyRef(company_id=COMPANY_ID),
        decision_ts=DECISION_TS,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="d37e360cea3cd32f18cacc634ab7e5dec967c4db",
            research_os_version="1.6.0",
            core_api_version="2.0",
        ),
        evidence=evidence_view,
        facts=FactView(
            company_id=COMPANY_ID,
            decision_ts=DECISION_TS,
            values=values,
            evidence_refs_by_fact={key: (ref,) for key, ref in refs.items()},
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        ),
    )


def test_resolved_plugin_exposes_domain_service_without_nested_module_execution() -> None:
    context = _context()
    registry = PluginRegistry(core_api_version="2.0", research_os_version="1.6.0")
    for plugin in BuiltinPluginProvider().plugins():
        registry.register(plugin)
    strategy = StrategyResolver().resolve(
        BusinessModelProfile(
            company_id=COMPANY_ID,
            primary_model="manufacturing",
            rule_match_score=1.0,
            usable_evidence_coverage=1.0,
            confidence_band="HIGH",
            classification_status="CLASSIFIED",
        ),
        context,
        registry,
        ResearchRunOptions(),
    )

    resolved = strategy.industry_plugins[0]
    provider = registry.services(resolved.plugin_id).kpi_provider  # type: ignore[union-attr]

    assert provider is not None
    assert not hasattr(provider, "run")
    metrics = provider.calculate(
        context.facts,
        builtin_metric_registry().select(provider.metric_ids()),
        PolicySnapshot(),
    )
    assert any(metric.status == "valid" for metric in metrics)
    assert all(metric.evidence_refs for metric in metrics if metric.status == "valid")
