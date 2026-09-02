import pytest
from pydantic import ValidationError

from research_os.plugins.models import PluginManifest


def _manifest(**overrides) -> PluginManifest:
    fields = {
        "plugin_id": "industry:synthetic",
        "plugin_type": "industry",
        "plugin_version": "1.0.0",
        "plugin_api_version": "2.0",
        "core_api_specifier": "~=2.0",
        "research_os_specifier": ">=1.6,<2",
        "supported_business_models": frozenset({"synthetic"}),
        "service_capabilities": frozenset({"kpi.metrics"}),
        "maturity": "stable",
    }
    fields.update(overrides)
    return PluginManifest(**fields)


def test_manifest_exposes_only_the_frozen_api_v2_fields():
    manifest = _manifest()

    assert set(PluginManifest.model_fields) == {
        "plugin_id",
        "plugin_type",
        "plugin_version",
        "plugin_api_version",
        "core_api_specifier",
        "research_os_specifier",
        "supported_business_models",
        "service_capabilities",
        "priority",
        "maturity",
    }
    assert manifest.plugin_api_version == "2.0"


@pytest.mark.parametrize(
    "legacy_field",
    [
        "api_version",
        "min_research_os_version",
        "max_research_os_version",
        "provides",
        "requires",
    ],
)
def test_manifest_rejects_removed_api_v1_fields(legacy_field):
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        _manifest(**{legacy_field: "removed"})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("plugin_version", "not-a-version"),
        ("core_api_specifier", "not a specifier"),
        ("research_os_specifier", ""),
    ],
)
def test_manifest_rejects_invalid_pep440_version_inputs(field, value):
    with pytest.raises(ValidationError):
        _manifest(**{field: value})


def test_manifest_keeps_independent_frozen_defaults():
    first = _manifest(
        plugin_id="methodology:first",
        plugin_type="methodology",
        supported_business_models=frozenset(),
        service_capabilities=frozenset(),
    )
    second = _manifest(
        plugin_id="methodology:second",
        plugin_type="methodology",
        supported_business_models=frozenset(),
        service_capabilities=frozenset(),
    )

    assert first.supported_business_models == frozenset()
    assert second.service_capabilities == frozenset()
    assert first.model_config["frozen"] is True
