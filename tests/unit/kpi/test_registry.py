from research_os.kpi.distributor import DistributorPack
from research_os.kpi.manufacturing import ManufacturingPack
from research_os.plugins.builtins import BuiltinPluginProvider
from research_os.plugins.registry import PluginRegistry


def test_builtin_industry_plugins_are_registered_through_plugin_registry():
    registry = PluginRegistry(core_api_version="1.0", research_os_version="1.4.0")
    for plugin in BuiltinPluginProvider().plugins():
        registry.register(plugin)

    assert [m.plugin_id for m in registry.manifests("industry")] == [
        "industry:distributor",
        "industry:manufacturing",
    ]


def test_kpi_packs_expose_versioned_calculation_contract_metadata():
    distributor = DistributorPack()
    manufacturing = ManufacturingPack()

    assert {"revenue", "cogs"} <= set(distributor.required_facts)
    assert distributor.missing_policy == "preserve_missing"
    assert "distributor" in distributor.eligible_business_models
    assert "manufacturing" in manufacturing.eligible_business_models
    assert manufacturing.required_facts
