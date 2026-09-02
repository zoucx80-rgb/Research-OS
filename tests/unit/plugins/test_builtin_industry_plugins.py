from datetime import datetime, timezone

from research_os.contracts.evidence import EvidenceRef
from research_os.plugins.builtins import (
    BuiltinPluginProvider,
    DistributorIndustryPlugin,
    ManufacturingIndustryPlugin,
)
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.plugins.registry import PluginRegistry
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
    company_id = "synthetic:builtin"
    return ResearchContext(
        run_id="run:builtin-plugin",
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


def _profile(primary):
    return BusinessModelProfile(
        company_id="synthetic:builtin",
        primary_model=primary,
        confidence=0.9,
        evidence_refs=(),
    )


def test_builtin_provider_exposes_precise_v2_industry_plugins():
    plugins = BuiltinPluginProvider().plugins()

    assert [p.manifest.plugin_id for p in plugins] == [
        "industry:distributor",
        "industry:manufacturing",
    ]
    assert all(p.manifest.plugin_api_version == "2.0" for p in plugins)
    assert all(p.manifest.core_api_specifier == "~=2.0" for p in plugins)
    assert all(p.manifest.research_os_specifier == ">=1.6,<2" for p in plugins)
    assert all(
        p.manifest.service_capabilities
        == frozenset({"kpi.metrics", "report.contributions"})
        for p in plugins
    )


def test_every_builtin_plugin_registers_under_api_v2():
    registry = PluginRegistry(core_api_version="2.0", research_os_version="1.6.0")

    for plugin in BuiltinPluginProvider().plugins():
        registry.register(plugin)

    assert [item.plugin_id for item in registry.manifests()] == [
        "industry:distributor",
        "industry:manufacturing",
    ]


def test_builtin_plugins_expose_domain_services_without_module_execution_api():
    plugin = ManufacturingIndustryPlugin()
    services = plugin.services()

    assert services.kpi_provider is not None
    assert services.kpi_provider.provider_id == "industry:manufacturing:kpi"
    assert services.report_contributions
    assert not hasattr(plugin, "modules")
    assert not hasattr(plugin, "report_contributions")
    assert not hasattr(plugin, "_pack")


def test_builtin_plugin_module_does_not_expose_compatibility_adapters():
    from research_os.plugins import builtins

    assert not any(name.endswith("Adapter") for name in vars(builtins))


def test_builtin_applicability_is_bound_to_its_business_model():
    plugin = DistributorIndustryPlugin()
    reference = EvidenceRef(
        evidence_id="ev:model",
        revision=1,
        content_fingerprint="a" * 64,
    )

    applicable = plugin.applicability(
        _context(),
        _profile("distributor").model_copy(update={"evidence_refs": (reference,)}),
    )
    inapplicable = plugin.applicability(_context(), _profile("manufacturing"))

    assert applicable.applicable is True
    assert applicable.rule_score == 1.0
    assert applicable.evidence_refs == (reference,)
    assert inapplicable.applicable is False
    assert inapplicable.rule_score == 0.0


def test_manufacturing_manifest_supports_both_manufacturing_aliases():
    assert ManufacturingIndustryPlugin().manifest.supported_business_models == frozenset(
        {"manufacturing", "manufacturer"}
    )
