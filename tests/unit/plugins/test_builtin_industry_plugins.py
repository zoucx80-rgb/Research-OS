from datetime import datetime, timezone

from research_os.plugins.builtins import (
    BuiltinPluginProvider,
    DistributorIndustryPlugin,
    ManufacturingIndustryPlugin,
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


def _context(facts):
    return ResearchContext(
        run_id="run:builtin-plugin",
        company=CompanyRef(company_id="synthetic:builtin"),
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
        facts=LegacyFactView(values=facts, evidence_by_fact={}),
        options=ResearchOptions(),
    )


def test_builtin_provider_exposes_stable_manufacturing_and_distributor_plugins():
    plugins = BuiltinPluginProvider().plugins()
    assert [p.manifest.plugin_id for p in plugins] == [
        "industry:distributor",
        "industry:manufacturing",
    ]
    assert all(p.manifest.api_version == "1.0" for p in plugins)
    assert all(p.manifest.maturity == "stable" for p in plugins)


def test_builtin_plugins_delegate_to_one_kpi_module():
    facts = {
        "revenue": 1000.0,
        "net_profit_parent": 50.0,
        "assets_begin": 800.0,
        "assets_end": 900.0,
        "equity_begin": 400.0,
        "equity_end": 450.0,
        "period_type": "H1",
        "period_days": 181,
    }
    plugin = ManufacturingIndustryPlugin()
    modules = plugin.modules()
    assert len(modules) == 1
    result = modules[0].run(_context(facts), ResearchStateView({}))
    assert result.status == "PASS"
    assert "kpi.metrics" in result.artifacts


def test_distributor_manifest_supports_only_distributor_model():
    assert DistributorIndustryPlugin().manifest.supported_business_models == {"distributor"}


def test_manufacturing_manifest_supports_both_manufacturing_aliases():
    assert ManufacturingIndustryPlugin().manifest.supported_business_models == {
        "manufacturing",
        "manufacturer",
    }
