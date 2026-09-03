import pytest

from research_os.plugins.models import (
    ApplicabilityResult,
    PluginManifest,
    SupportAssessment,
)
from research_os.plugins.protocols import PluginServices
from research_os.plugins.registry import (
    DuplicatePluginError,
    PluginContractError,
    PluginRegistry,
    PluginVersionUnsupportedError,
)


def _manifest(
    *,
    plugin_id="industry:synthetic",
    plugin_type="industry",
    core_api_specifier="~=2.0",
    research_os_specifier=">=1.6,<2",
    service_capabilities=frozenset({"kpi.metrics"}),
):
    return PluginManifest(
        plugin_id=plugin_id,
        plugin_type=plugin_type,
        plugin_version="1.0.0",
        plugin_api_version="2.0",
        core_api_specifier=core_api_specifier,
        research_os_specifier=research_os_specifier,
        supported_business_models=frozenset({"synthetic"}),
        service_capabilities=service_capabilities,
        maturity="stable",
    )


class _KpiProvider:
    provider_id = "synthetic:kpi"
    provider_version = "1.0.0"

    def metric_ids(self):
        return frozenset({"kpi.synthetic"})

    def calculate(self, facts, definitions, policy):
        return ()


class FakeIndustryPlugin:
    def __init__(self, manifest=None, services=None):
        self.manifest = manifest or _manifest()
        self._services = services or PluginServices(kpi_provider=_KpiProvider())

    def applicability(self, context, business_model):
        return ApplicabilityResult(applicable=True, rule_score=1.0)

    def services(self):
        return self._services


class FakeMethodologyPlugin:
    def __init__(self, manifest=None):
        self.manifest = manifest or _manifest(
            plugin_id="methodology:synthetic",
            plugin_type="methodology",
            service_capabilities=frozenset(),
        )

    def supports(self, context, available_capabilities):
        return SupportAssessment(supported=True)

    def services(self):
        return PluginServices()


def _registry(version="1.6.0"):
    return PluginRegistry(core_api_version="2.0", research_os_version=version)


def test_registry_uses_pep440_specifiers_for_core_and_product_compatibility():
    registry = _registry("1.10.0")
    plugin = FakeIndustryPlugin(_manifest(research_os_specifier=">=1.9,<1.11"))

    registry.register(plugin)

    assert registry.get("industry:synthetic") is plugin


def test_registry_rejects_version_outside_declared_specifier():
    plugin = FakeIndustryPlugin(_manifest(core_api_specifier="<2.0"))

    with pytest.raises(PluginVersionUnsupportedError, match="core API") as captured:
        _registry().register(plugin)

    assert captured.value.context == {
        "plugin_id": "industry:synthetic",
        "core_api_version": "2.0",
        "required_specifier": "<2.0",
    }


def test_registry_applies_pep440_prerelease_rules():
    registry = _registry("1.6.0rc1")
    plugin = FakeIndustryPlugin(_manifest(research_os_specifier=">=1.6.0rc1,<2"))

    registry.register(plugin)

    assert registry.get("industry:synthetic") is plugin


def test_registry_rejects_duplicate_plugin_id():
    registry = _registry()
    registry.register(FakeIndustryPlugin())

    with pytest.raises(DuplicatePluginError, match="industry:synthetic") as captured:
        registry.register(FakeIndustryPlugin())

    assert captured.value.context == {"plugin_id": "industry:synthetic"}


def test_registry_rejects_plugins_that_expose_old_module_contracts_only():
    class LegacyShape:
        manifest = _manifest()

        def applicability(self, context):
            return ApplicabilityResult(applicable=True)

        def modules(self):
            return []

    with pytest.raises(PluginContractError, match="services"):
        _registry().register(LegacyShape())


def test_registry_rejects_services_that_do_not_match_declared_capabilities():
    plugin = FakeIndustryPlugin(
        _manifest(service_capabilities=frozenset({"kpi.metrics"})),
        services=PluginServices(),
    )

    with pytest.raises(PluginContractError, match="service_capabilities"):
        _registry().register(plugin)


def test_registry_requires_exact_service_capability_declarations():
    plugin = FakeIndustryPlugin(
        _manifest(service_capabilities=frozenset({"valuation.methods"})),
        services=PluginServices(kpi_provider=_KpiProvider()),
    )

    with pytest.raises(
        PluginContractError, match="declared.*valuation.methods.*actual.*kpi.metrics"
    ):
        _registry().register(plugin)


def test_registry_rejects_non_plugin_services_return_value():
    plugin = FakeIndustryPlugin()
    plugin._services = object()

    with pytest.raises(PluginContractError, match="PluginServices"):
        _registry().register(plugin)


def test_registry_wraps_plugin_services_exception_with_plugin_context():
    plugin = FakeIndustryPlugin()

    def explode():
        raise RuntimeError("services exploded")

    plugin.services = explode

    with pytest.raises(PluginContractError) as captured:
        _registry().register(plugin)

    assert isinstance(captured.value.__cause__, RuntimeError)
    assert captured.value.context == {"plugin_id": "industry:synthetic"}


def test_registry_lists_manifests_deterministically_and_filters_type():
    registry = _registry()
    industry = FakeIndustryPlugin(_manifest(plugin_id="industry:zeta"))
    methodology = FakeMethodologyPlugin(
        _manifest(
            plugin_id="methodology:alpha",
            plugin_type="methodology",
            service_capabilities=frozenset(),
        )
    )
    registry.register(industry)
    registry.register(methodology)

    assert [m.plugin_id for m in registry.manifests()] == [
        "industry:zeta",
        "methodology:alpha",
    ]
    assert [m.plugin_id for m in registry.manifests("methodology")] == ["methodology:alpha"]
