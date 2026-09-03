from __future__ import annotations

from datetime import datetime, timezone

from research_os.application import ResearchRunOptions
from research_os.contracts.values import AccountingScope, Ratio
from research_os.period.models import ReportingPeriod
from research_os.plugins.builtins import BuiltinPluginProvider
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolver
from research_os.router.models import BusinessModelProfile
from research_os.router.segments import SegmentProfile
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)


def _context() -> ResearchContext:
    decision_ts = datetime(2026, 9, 1, tzinfo=timezone.utc)
    return ResearchContext(
        run_id="run:segment-routing",
        company=CompanyRef(company_id="synthetic:segments"),
        decision_ts=decision_ts,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.6.0",
            core_api_version="2.0",
        ),
        evidence=EvidenceView(
            (), company_id="synthetic:segments", decision_ts=decision_ts
        ),
        facts=FactView(
            company_id="synthetic:segments",
            decision_ts=decision_ts,
            values={},
            evidence_refs_by_fact={},
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        ),
    )


def test_secondary_segment_plugin_cannot_override_primary_exclusive_artifacts() -> None:
    profile = BusinessModelProfile(
        company_id="synthetic:segments",
        primary_model="manufacturing",
        secondary_models=("distributor",),
        rule_match_score=0.8,
        usable_evidence_coverage=0.8,
        confidence_band="HIGH",
        ambiguity=0.2,
        segment_profiles=(
            SegmentProfile(
                segment_id="manufacturing",
                business_model="manufacturing",
                revenue_share=Ratio(value="70", representation="percent"),
            ),
            SegmentProfile(
                segment_id="distribution",
                business_model="distributor",
                revenue_share=Ratio(value="30", representation="percent"),
            ),
        ),
        classification_status="CLASSIFIED",
    )
    registry = PluginRegistry(core_api_version="2.0", research_os_version="1.6.0")
    for plugin in BuiltinPluginProvider().plugins():
        registry.register(plugin)

    resolution = StrategyResolver().resolve(
        profile, _context(), registry, ResearchRunOptions()
    )

    assert tuple(item.plugin_id for item in resolution.industry_plugins) == (
        "industry:manufacturing",
    )
    assert any("secondary" in item for item in resolution.rationale)
