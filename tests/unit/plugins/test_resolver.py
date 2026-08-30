from datetime import datetime, timezone

from research_os.plugins.models import ApplicabilityResult, PluginManifest
from research_os.plugins.registry import PluginRegistry
from research_os.plugins.resolver import StrategyResolver
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)


def _context(options=None):
    return ResearchContext(
        run_id="run:resolver",
        company=CompanyRef(company_id="synthetic:resolver"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.3.0",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView([]),
        facts=LegacyFactView(values={}, evidence_by_fact={}),
        options=options or ResearchOptions(),
    )


def _profile(primary="manufacturing", secondary=None):
    return BusinessModelProfile(
        company_id="synthetic:resolver",
        primary_model=primary,
        secondary_models=secondary or [],
        confidence=0.9,
        evidence_ids=["ev:model"],
        router_version="router@test",
    )


def _manifest(
    plugin_id,
    *,
    plugin_type="industry",
    models=None,
    provides=None,
    requires=None,
    priority=100,
):
    return PluginManifest(
        plugin_id=plugin_id,
        plugin_type=plugin_type,
        plugin_version="1.0.0",
        api_version="1.0",
        min_research_os_version="1.3.0",
        provides=set(provides or {"kpi.synthetic"}),
        requires=set(requires or {"business_model.profile"}),
        supported_business_models=set(models or []),
        priority=priority,
        maturity="stable",
    )


class IndustryPlugin:
    def __init__(self, plugin_id, *, models, score=1.0, priority=100):
        self.manifest = _manifest(plugin_id, models=models, priority=priority)
        self.score = score

    def applicability(self, context):
        return ApplicabilityResult(
            applicable=self.score > 0,
            score=self.score,
            rationale=[f"score={self.score}"],
        )

    def modules(self):
        return []

    def report_contributions(self):
        return []


class MethodologyPlugin:
    def __init__(self, plugin_id, *, requires, supported=True):
        self.manifest = _manifest(
            plugin_id,
            plugin_type="methodology",
            provides={f"methodology.{plugin_id}"},
            requires=requires,
        )
        self.supported = supported

    def supports(self, context, state):
        return self.supported

    def modules(self):
        return []


def _registry(*plugins):
    registry = PluginRegistry(core_api_version="1.0", research_os_version="1.3.0")
    for plugin in plugins:
        registry.register(plugin)
    return registry


def test_resolver_automatically_selects_matching_industry_plugin():
    plugin = IndustryPlugin("industry:manufacturing", models={"manufacturing"})
    result = StrategyResolver().resolve(_profile(), _context(), _registry(plugin))

    assert [p.plugin_id for p in result.industry_plugins] == ["industry:manufacturing"]
    assert result.coverage_gaps == []


def test_resolver_emits_coverage_gap_without_silent_core_fallback():
    result = StrategyResolver().resolve(
        _profile(primary="consumer"),
        _context(),
        _registry(),
    )

    assert result.industry_plugins == []
    assert result.coverage_gaps[0].gap_type == "industry_strategy"
    assert result.coverage_gaps[0].business_model == "consumer"


def test_resolver_distinguishes_unsupported_taxonomy_from_missing_plugin():
    profile = _profile(primary="unknown").model_copy(
        update={
            "classification_status": "unsupported_taxonomy",
            "classification_reason": "no_supported_business_model_match",
        }
    )

    result = StrategyResolver().resolve(profile, _context(), _registry())

    assert result.industry_plugins == []
    assert len(result.coverage_gaps) == 1
    gap = result.coverage_gaps[0]
    assert gap.gap_type == "business_model_taxonomy"
    assert gap.business_model == "unknown"
    assert gap.reason_code == "UNSUPPORTED_BUSINESS_MODEL_TAXONOMY"
    assert gap.fallback_available is True
    assert "industry_strategy" in gap.affected_capabilities


def test_resolver_distinguishes_insufficient_model_evidence():
    profile = _profile(primary="unknown").model_copy(
        update={
            "classification_status": "insufficient_evidence",
            "classification_reason": "no_usable_business_model_evidence",
        }
    )

    result = StrategyResolver().resolve(profile, _context(), _registry())

    assert result.industry_plugins == []
    assert len(result.coverage_gaps) == 1
    gap = result.coverage_gaps[0]
    assert gap.gap_type == "business_model_evidence"
    assert gap.reason_code == "INSUFFICIENT_BUSINESS_MODEL_EVIDENCE"
    assert gap.fallback_available is True


def test_recognized_hospitality_gets_industry_strategy_gap():
    profile = _profile(primary="hospitality")

    result = StrategyResolver().resolve(profile, _context(), _registry())

    assert result.industry_plugins == []
    assert len(result.coverage_gaps) == 1
    gap = result.coverage_gaps[0]
    assert gap.gap_type == "industry_strategy"
    assert gap.business_model == "hospitality"
    assert gap.reason_code == "NO_COMPATIBLE_INDUSTRY_PLUGIN"
    assert gap.fallback_available is True


def test_resolver_prefers_higher_applicability_score():
    lower = IndustryPlugin("industry:lower", models={"manufacturing"}, score=0.6, priority=1)
    higher = IndustryPlugin("industry:higher", models={"manufacturing"}, score=0.9, priority=999)

    result = StrategyResolver().resolve(_profile(), _context(), _registry(lower, higher))

    assert [p.plugin_id for p in result.industry_plugins] == ["industry:higher"]


def test_resolver_breaks_equal_score_by_priority_then_plugin_id():
    zeta = IndustryPlugin("industry:zeta", models={"manufacturing"}, score=0.8, priority=20)
    beta = IndustryPlugin("industry:beta", models={"manufacturing"}, score=0.8, priority=10)
    alpha = IndustryPlugin("industry:alpha", models={"manufacturing"}, score=0.8, priority=10)

    result = StrategyResolver().resolve(_profile(), _context(), _registry(zeta, beta, alpha))

    assert [p.plugin_id for p in result.industry_plugins] == ["industry:alpha"]


def test_resolver_selects_only_supported_methodology_with_satisfied_requirements():
    industry = IndustryPlugin("industry:manufacturing", models={"manufacturing"})
    selected = MethodologyPlugin("methodology:selected", requires={"kpi.synthetic"}, supported=True)
    unsupported = MethodologyPlugin("methodology:unsupported", requires={"kpi.synthetic"}, supported=False)
    unsatisfied = MethodologyPlugin("methodology:unsatisfied", requires={"missing.capability"}, supported=True)

    result = StrategyResolver().resolve(
        _profile(),
        _context(),
        _registry(industry, selected, unsupported, unsatisfied),
    )

    assert [p.plugin_id for p in result.methodology_plugins] == ["methodology:selected"]


def test_explicit_industry_override_records_rationale():
    automatic = IndustryPlugin("industry:auto", models={"manufacturing"}, score=0.9)
    override = IndustryPlugin("industry:override", models={"manufacturing"}, score=0.1)
    context = _context(
        ResearchOptions(
            industry_plugin_override="industry:override",
            override_rationale="analyst selected alternate strategy",
        )
    )

    result = StrategyResolver().resolve(
        _profile(), context, _registry(automatic, override)
    )

    assert [p.plugin_id for p in result.industry_plugins] == ["industry:override"]
    assert any("analyst selected alternate strategy" in item for item in result.rationale)
