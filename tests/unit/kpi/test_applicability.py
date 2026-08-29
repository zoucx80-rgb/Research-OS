from datetime import datetime, timezone

from research_os.plugins.builtins import BuiltinPluginProvider
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolver
from research_os.router.models import BusinessModelProfile
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)


def _profile(primary, secondary=None):
    return BusinessModelProfile(
        company_id="synthetic:applicability",
        primary_model=primary,
        secondary_models=secondary or [],
        confidence=.9,
        evidence_ids=["synthetic:e1"],
        router_version="router@test",
    )


def _context():
    return ResearchContext(
        run_id="run:kpi-applicability",
        company=CompanyRef(company_id="synthetic:applicability"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version="1.4.0",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView([]),
        facts=LegacyFactView(values={}, evidence_by_fact={}),
        options=ResearchOptions(),
    )


def _registry():
    registry = PluginRegistry(core_api_version="1.0", research_os_version="1.4.0")
    for plugin in BuiltinPluginProvider().plugins():
        registry.register(plugin)
    return registry


def _resolve(primary, secondary=None):
    return StrategyResolver().resolve(
        _profile(primary, secondary),
        _context(),
        _registry(),
    )


def test_distributor_has_specialized_kpi_support():
    resolution = _resolve("distributor")
    assert [p.plugin_id for p in resolution.industry_plugins] == ["industry:distributor"]
    assert not resolution.coverage_gaps


def test_manufacturing_has_specialized_kpi_support():
    resolution = _resolve("manufacturing")
    assert [p.plugin_id for p in resolution.industry_plugins] == ["industry:manufacturing"]
    assert not resolution.coverage_gaps


def test_generic_infrastructure_never_counts_as_specialized_support():
    resolution = _resolve("consumer")
    assert resolution.industry_plugins == []
    assert any(
        gap.gap_type == "industry_strategy" and gap.business_model == "consumer"
        for gap in resolution.coverage_gaps
    )


def test_unsupported_secondary_is_recorded_without_losing_supported_primary():
    resolution = _resolve("distributor", ["software"])
    assert [p.plugin_id for p in resolution.industry_plugins] == ["industry:distributor"]
    assert any(gap.business_model == "software" for gap in resolution.coverage_gaps)
