from datetime import datetime, timezone

import pytest

from research_os.application.command import ResearchRunOptions
from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.plugins.models import (
    ApplicabilityResult,
    PluginManifest,
    SupportAssessment,
)
from research_os.plugins.protocols import PluginServices
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolutionError, StrategyResolver
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)


def _context():
    decision_ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    company_id = "synthetic:resolver"
    return ResearchContext(
        run_id="run:resolver",
        company=CompanyRef(company_id=company_id),
        decision_ts=decision_ts,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.6.0",
            core_api_version="2.0",
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


def _reference(evidence_id="ev:model"):
    return EvidenceRef(
        evidence_id=evidence_id,
        revision=1,
        content_fingerprint="a" * 64,
    )


def _profile(primary="manufacturing", secondary=None):
    return BusinessModelProfile(
        company_id="synthetic:resolver",
        primary_model=primary,
        secondary_models=secondary or [],
        confidence=0.9,
        evidence_refs=(_reference(),),
        router_version="router@test",
    )


def _manifest(
    plugin_id,
    *,
    plugin_type="industry",
    models=None,
    service_capabilities=frozenset({"kpi.metrics"}),
    priority=100,
):
    return PluginManifest(
        plugin_id=plugin_id,
        plugin_type=plugin_type,
        plugin_version="1.0.0",
        plugin_api_version="2.0",
        core_api_specifier="~=2.0",
        research_os_specifier=">=1.6,<2",
        supported_business_models=frozenset(models or []),
        service_capabilities=service_capabilities,
        priority=priority,
        maturity="stable",
    )


class _KpiProvider:
    provider_id = "synthetic:kpi"
    provider_version = "1.0.0"

    def metric_ids(self):
        return frozenset({"kpi.synthetic"})

    def calculate(self, facts, definitions, policy):
        return ()


class IndustryPlugin:
    def __init__(
        self,
        plugin_id,
        *,
        models,
        score=1.0,
        priority=100,
        evidence_refs=(),
    ):
        self.manifest = _manifest(plugin_id, models=models, priority=priority)
        self.score = score
        self.evidence_refs = evidence_refs
        self.seen_profile = None

    def applicability(self, context, business_model):
        self.seen_profile = business_model
        return ApplicabilityResult(
            applicable=self.score > 0,
            rule_score=self.score,
            rationale=(f"rule_score={self.score}",),
            evidence_refs=self.evidence_refs,
        )

    def services(self):
        return PluginServices(kpi_provider=_KpiProvider())


class MethodologyPlugin:
    def __init__(self, plugin_id, *, supported=True, evidence_refs=()):
        self.manifest = _manifest(
            plugin_id,
            plugin_type="methodology",
            service_capabilities=frozenset(),
        )
        self.supported = supported
        self.evidence_refs = evidence_refs
        self.seen_capabilities = None

    def supports(self, context, available_capabilities):
        self.seen_capabilities = available_capabilities
        return SupportAssessment(
            supported=self.supported,
            evidence_refs=self.evidence_refs,
        )

    def services(self):
        return PluginServices()


def _registry(*plugins):
    registry = PluginRegistry(core_api_version="2.0", research_os_version="1.6.0")
    for plugin in plugins:
        registry.register(plugin)
    return registry


def _resolve(profile, context, registry, options=None):
    return StrategyResolver().resolve(
        profile,
        context,
        registry,
        options or ResearchRunOptions(),
    )


def test_resolver_selects_matching_industry_plugin_using_profile_argument():
    plugin = IndustryPlugin("industry:manufacturing", models={"manufacturing"})

    result = _resolve(_profile(), _context(), _registry(plugin))

    assert [p.plugin_id for p in result.industry_plugins] == ["industry:manufacturing"]
    assert plugin.seen_profile is not None
    assert plugin.seen_profile.primary_model == "manufacturing"


def test_resolver_rejects_invalid_applicability_result_as_public_error():
    plugin = IndustryPlugin("industry:invalid", models={"manufacturing"})
    plugin.applicability = lambda context, profile: {"applicable": True}

    with pytest.raises(StrategyResolutionError) as captured:
        _resolve(_profile(), _context(), _registry(plugin))

    assert captured.value.context["operation"] == "applicability"
    assert captured.value.context["run_id"] == "run:resolver"


def test_resolver_emits_coverage_gap_without_a_compatible_industry_service():
    result = _resolve(
        _profile(primary="consumer"),
        _context(),
        _registry(),
    )

    assert result.industry_plugins == ()
    assert result.coverage_gaps[0].gap_type == "industry_strategy"
    assert result.coverage_gaps[0].business_model == "consumer"


def test_resolver_prefers_higher_rule_score():
    lower = IndustryPlugin("industry:lower", models={"manufacturing"}, score=0.6)
    higher = IndustryPlugin("industry:higher", models={"manufacturing"}, score=0.9)

    result = _resolve(_profile(), _context(), _registry(lower, higher))

    assert [p.plugin_id for p in result.industry_plugins] == ["industry:higher"]


def test_resolver_retains_only_selected_applicability_lineage():
    lower_ref = _reference("ev:lower")
    selected_ref = _reference("ev:selected")
    lower = IndustryPlugin(
        "industry:lower",
        models={"manufacturing"},
        score=0.6,
        evidence_refs=(lower_ref,),
    )
    selected = IndustryPlugin(
        "industry:selected",
        models={"manufacturing"},
        score=0.9,
        evidence_refs=(selected_ref,),
    )

    result = _resolve(_profile(), _context(), _registry(lower, selected))

    assert result.evidence_refs == (_reference(), selected_ref)


def test_resolver_passes_service_capabilities_to_methodology_plugin():
    industry = IndustryPlugin("industry:manufacturing", models={"manufacturing"})
    methodology = MethodologyPlugin("methodology:uses-kpi")

    result = _resolve(
        _profile(), _context(), _registry(industry, methodology)
    )

    assert [p.plugin_id for p in result.methodology_plugins] == ["methodology:uses-kpi"]
    assert methodology.seen_capabilities == frozenset(
        {"business_model.profile", "kpi.metrics"}
    )


def test_resolver_retains_selected_methodology_support_lineage():
    industry = IndustryPlugin("industry:manufacturing", models={"manufacturing"})
    support_ref = _reference("ev:method-support")
    methodology = MethodologyPlugin(
        "methodology:valuation-forecast",
        evidence_refs=(support_ref,),
    )

    result = _resolve(
        _profile(),
        _context(),
        _registry(industry, methodology),
    )

    assert result.methodology_plugins[0].evidence_refs == (support_ref,)
    assert result.evidence_refs == (support_ref, _reference())


def test_explicit_industry_override_records_rationale():
    automatic = IndustryPlugin("industry:auto", models={"manufacturing"}, score=0.9)
    override = IndustryPlugin("industry:override", models={"manufacturing"}, score=0.1)
    context = _context()
    options = ResearchRunOptions(
        industry_plugin_override="industry:override",
        override_rationale="analyst selected alternate strategy",
    )

    result = _resolve(
        _profile(), context, _registry(automatic, override), options
    )

    assert [p.plugin_id for p in result.industry_plugins] == ["industry:override"]
    assert any("analyst selected alternate strategy" in item for item in result.rationale)


def test_missing_industry_override_reports_plugin_and_run_context():
    options = ResearchRunOptions(
        industry_plugin_override="industry:missing",
        override_rationale="analyst override",
    )

    with pytest.raises(StrategyResolutionError) as captured:
        _resolve(_profile(), _context(), _registry(), options)

    assert captured.value.context == {
        "plugin_id": "industry:missing",
        "run_id": "run:resolver",
    }


def test_resolver_wraps_industry_applicability_exception() -> None:
    plugin = IndustryPlugin("industry:broken", models={"manufacturing"})

    def explode(context, business_model):
        raise RuntimeError("applicability exploded")

    plugin.applicability = explode

    with pytest.raises(StrategyResolutionError) as captured:
        _resolve(_profile(), _context(), _registry(plugin))

    assert isinstance(captured.value.__cause__, RuntimeError)
    assert captured.value.context == {
        "plugin_id": "industry:broken",
        "run_id": "run:resolver",
        "operation": "applicability",
    }


def test_resolver_wraps_methodology_support_exception() -> None:
    industry = IndustryPlugin("industry:ok", models={"manufacturing"})
    methodology = MethodologyPlugin("methodology:broken")

    def explode(context, available_capabilities):
        raise RuntimeError("support exploded")

    methodology.supports = explode

    with pytest.raises(StrategyResolutionError) as captured:
        _resolve(_profile(), _context(), _registry(industry, methodology))

    assert isinstance(captured.value.__cause__, RuntimeError)
    assert captured.value.context == {
        "plugin_id": "methodology:broken",
        "run_id": "run:resolver",
        "operation": "supports",
    }
