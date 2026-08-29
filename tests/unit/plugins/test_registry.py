import pytest

from research_os.plugins.models import ApplicabilityResult, PluginManifest
from research_os.plugins.registry import (
    DuplicatePluginError,
    PluginCompatibilityError,
    PluginRegistry,
)


def _manifest(
    *,
    plugin_id="industry:synthetic",
    plugin_type="industry",
    api_version="1.0",
    min_version="1.3.0",
    max_version=None,
):
    return PluginManifest(
        plugin_id=plugin_id,
        plugin_type=plugin_type,
        plugin_version="1.0.0",
        api_version=api_version,
        min_research_os_version=min_version,
        max_research_os_version=max_version,
        provides={"kpi.synthetic"},
        requires={"business_model.profile"},
        supported_business_models={"synthetic"},
        maturity="stable",
    )


class FakeIndustryPlugin:
    def __init__(self, manifest=None):
        self.manifest = manifest or _manifest()

    def applicability(self, context):
        return ApplicabilityResult(applicable=True, score=1.0, rationale=["synthetic"])

    def modules(self):
        return []

    def report_contributions(self):
        return []


class FakeMethodologyPlugin:
    def __init__(self, manifest=None):
        self.manifest = manifest or _manifest(
            plugin_id="methodology:synthetic",
            plugin_type="methodology",
        )

    def supports(self, context, state):
        return True

    def modules(self):
        return []


def _registry(version="1.3.0"):
    return PluginRegistry(core_api_version="1.0", research_os_version=version)


def test_registry_rejects_incompatible_core_api():
    plugin = FakeIndustryPlugin(_manifest(api_version="9.0"))
    with pytest.raises(PluginCompatibilityError, match="api"):
        _registry().register(plugin)


def test_registry_rejects_duplicate_plugin_id():
    registry = _registry()
    registry.register(FakeIndustryPlugin())
    with pytest.raises(DuplicatePluginError, match="industry:synthetic"):
        registry.register(FakeIndustryPlugin())


def test_registry_rejects_plugin_type_mismatch():
    plugin = FakeMethodologyPlugin(_manifest(plugin_type="industry"))
    with pytest.raises(PluginCompatibilityError, match="industry"):
        _registry().register(plugin)


@pytest.mark.parametrize(
    ("runtime_version", "min_version", "max_version"),
    [
        ("1.3.0", "1.4.0", None),
        ("1.3.0", "1.2.0", "1.2.9"),
    ],
)
def test_registry_rejects_research_os_version_outside_manifest_range(
    runtime_version, min_version, max_version
):
    plugin = FakeIndustryPlugin(
        _manifest(min_version=min_version, max_version=max_version)
    )
    with pytest.raises(PluginCompatibilityError, match="Research OS"):
        _registry(runtime_version).register(plugin)


def test_registry_uses_semver_not_lexical_comparison():
    registry = _registry("1.10.0")
    plugin = FakeIndustryPlugin(_manifest(min_version="1.9.0", max_version="1.11.0"))
    registry.register(plugin)
    assert registry.get("industry:synthetic") is plugin


def test_registry_lists_manifests_deterministically_and_filters_type():
    registry = _registry()
    industry = FakeIndustryPlugin(_manifest(plugin_id="industry:zeta"))
    methodology = FakeMethodologyPlugin(
        _manifest(plugin_id="methodology:alpha", plugin_type="methodology")
    )
    registry.register(industry)
    registry.register(methodology)

    assert [m.plugin_id for m in registry.manifests()] == [
        "industry:zeta",
        "methodology:alpha",
    ]
    assert [m.plugin_id for m in registry.manifests("methodology")] == [
        "methodology:alpha"
    ]
