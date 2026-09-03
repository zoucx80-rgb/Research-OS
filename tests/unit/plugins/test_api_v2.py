from __future__ import annotations

from dataclasses import dataclass

import pytest

from research_os.plugins.discovery import PluginDiscoveryError, discover_plugins
from research_os.plugins.models import ApplicabilityResult, PluginManifest
from research_os.plugins.protocols import PluginServices
from research_os.plugins.registry import (
    DuplicatePluginError,
    PluginContractError,
    PluginRegistry,
)


class _Provider:
    provider_id = "synthetic:kpi"
    provider_version = "1.0.0"

    def metric_ids(self):
        return frozenset({"synthetic.metric"})

    def calculate(self, facts, definitions, policy):
        return ()


class _Plugin:
    def __init__(self, plugin_id: str):
        self.manifest = PluginManifest(
            plugin_id=plugin_id,
            plugin_type="industry",
            plugin_version="1.0.0",
            plugin_api_version="2.0",
            core_api_specifier="~=2.0",
            research_os_specifier=">=1.6,<2",
            supported_business_models=frozenset({"synthetic"}),
            service_capabilities=frozenset({"kpi.metrics"}),
        )

    def applicability(self, context, business_model):
        return ApplicabilityResult(applicable=True, rule_score=1.0)

    def services(self):
        return PluginServices(kpi_provider=_Provider())


@dataclass(frozen=True)
class _Distribution:
    name: str


@dataclass
class _EntryPoint:
    name: str
    value: str
    loaded: object
    group: str = "research_os.plugins"
    dist: _Distribution = _Distribution("synthetic-dist")

    def load(self):
        if isinstance(self.loaded, Exception):
            raise self.loaded
        return self.loaded


def _registry() -> PluginRegistry:
    return PluginRegistry(core_api_version="2.0", research_os_version="1.6.0")


def test_discovery_loads_and_registers_plugins_in_plugin_id_order():
    registry = _registry()
    entry_points = (
        _EntryPoint("industry:zeta", "pkg:zeta", lambda: _Plugin("industry:zeta")),
        _EntryPoint("industry:alpha", "pkg:alpha", _Plugin("industry:alpha")),
    )

    discovered = discover_plugins(registry, entry_points=entry_points)

    assert tuple(item.manifest.plugin_id for item in discovered) == (
        "industry:alpha",
        "industry:zeta",
    )
    assert [item.plugin_id for item in registry.manifests()] == [
        "industry:alpha",
        "industry:zeta",
    ]


def test_discovery_uses_manifest_plugin_id_not_entry_point_name_as_identity():
    entry_point = _EntryPoint(
        "industry:declared",
        "pkg:plugin",
        _Plugin("industry:actual"),
    )

    discovered = discover_plugins(_registry(), entry_points=(entry_point,))

    assert discovered[0].manifest.plugin_id == "industry:actual"


def test_discovery_instantiates_plugin_class_with_class_level_manifest():
    class ClassPlugin(_Plugin):
        manifest = _Plugin("industry:class").manifest

        def __init__(self):
            super().__init__("industry:class")

    discovered = discover_plugins(
        _registry(),
        entry_points=(_EntryPoint("industry:class", "pkg:ClassPlugin", ClassPlugin),),
    )

    assert isinstance(discovered[0], ClassPlugin)


def test_discovery_wraps_raw_register_failure_with_entry_point_context():
    class BrokenRegistry(PluginRegistry):
        def register(self, plugin):
            raise RuntimeError("registry hook exploded")

    entry_point = _EntryPoint(
        "industry:broken-register",
        "broken.package:plugin",
        _Plugin("industry:broken-register"),
        dist=_Distribution("broken-dist"),
    )

    with pytest.raises(PluginDiscoveryError) as captured:
        discover_plugins(
            BrokenRegistry(core_api_version="2.0", research_os_version="1.6.0"),
            entry_points=(entry_point,),
        )

    assert isinstance(captured.value.__cause__, RuntimeError)
    assert captured.value.context == {
        "distribution": "broken-dist",
        "entry_point": "industry:broken-register",
        "entry_point_value": "broken.package:plugin",
        "plugin_id": "industry:broken-register",
    }


def test_discovery_adds_entry_point_context_to_services_failure() -> None:
    plugin = _Plugin("industry:broken-services")

    def explode():
        raise RuntimeError("services exploded")

    plugin.services = explode
    entry_point = _EntryPoint(
        "industry:broken-services",
        "broken.package:plugin",
        plugin,
        dist=_Distribution("broken-dist"),
    )

    with pytest.raises(PluginDiscoveryError) as captured:
        discover_plugins(_registry(), entry_points=(entry_point,))

    assert captured.value.context == {
        "distribution": "broken-dist",
        "entry_point": "industry:broken-services",
        "entry_point_value": "broken.package:plugin",
        "plugin_id": "industry:broken-services",
    }
    assert isinstance(captured.value.__cause__, PluginContractError)
    assert isinstance(captured.value.__cause__.__cause__, RuntimeError)


def test_discovery_rejects_duplicate_plugin_ids():
    entry_points = (
        _EntryPoint("industry:same", "first:plugin", _Plugin("industry:same")),
        _EntryPoint("industry:same", "second:plugin", _Plugin("industry:same")),
    )

    with pytest.raises(PluginDiscoveryError, match="second:plugin") as captured:
        discover_plugins(_registry(), entry_points=entry_points)

    assert isinstance(captured.value.__cause__, DuplicatePluginError)
    assert captured.value.context["plugin_id"] == "industry:same"
    assert captured.value.context["entry_point_value"] == "second:plugin"


def test_discovery_wraps_load_failure_with_distribution_and_entry_point_context():
    entry_point = _EntryPoint(
        "industry:broken",
        "broken.package:plugin",
        RuntimeError("import exploded"),
        dist=_Distribution("broken-dist"),
    )

    with pytest.raises(
        PluginDiscoveryError,
        match="broken-dist.*industry:broken.*broken.package:plugin",
    ) as captured:
        discover_plugins(_registry(), entry_points=(entry_point,))

    assert isinstance(captured.value.__cause__, RuntimeError)


def test_discovery_uses_only_the_v2_entry_point_group():
    seen = []

    def query(*, group):
        seen.append(group)
        return ()

    assert discover_plugins(_registry(), entry_point_query=query) == ()
    assert seen == ["research_os.plugins"]


def test_discovery_wraps_entry_point_query_failure():
    def query(*, group):
        raise RuntimeError(f"cannot query {group}")

    with pytest.raises(PluginDiscoveryError) as captured:
        discover_plugins(_registry(), entry_point_query=query)

    assert isinstance(captured.value.__cause__, RuntimeError)


def test_plugin_package_exports_metric_definition_registry_contract():
    from research_os.plugins import MetricDefinitionRegistry

    assert MetricDefinitionRegistry.__name__ == "MetricDefinitionRegistry"
