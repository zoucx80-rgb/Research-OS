import pytest
from pydantic import ValidationError

from research_os.plugins.models import PluginManifest


def test_manifest_rejects_empty_capability_ids():
    with pytest.raises(ValidationError, match="capability"):
        PluginManifest(
            plugin_id="industry:synthetic",
            plugin_type="industry",
            plugin_version="1.0.0",
            api_version="1.0",
            min_research_os_version="1.3.0",
            provides={""},
            requires={"business_model.profile"},
            supported_business_models={"synthetic"},
            maturity="stable",
        )


def test_manifest_uses_independent_set_defaults():
    first = PluginManifest(
        plugin_id="methodology:first",
        plugin_type="methodology",
        plugin_version="1.0.0",
        api_version="1.0",
        min_research_os_version="1.3.0",
        provides={"analysis.first"},
        requires=set(),
    )
    second = PluginManifest(
        plugin_id="methodology:second",
        plugin_type="methodology",
        plugin_version="1.0.0",
        api_version="1.0",
        min_research_os_version="1.3.0",
        provides={"analysis.second"},
        requires=set(),
    )

    assert first.supported_business_models == set()
    assert second.supported_business_models == set()
    assert first.supported_business_models is not second.supported_business_models


def test_manifest_rejects_empty_plugin_identity():
    with pytest.raises(ValidationError, match="plugin"):
        PluginManifest(
            plugin_id=" ",
            plugin_type="industry",
            plugin_version="1.0.0",
            api_version="1.0",
            min_research_os_version="1.3.0",
            provides={"kpi.synthetic"},
            requires=set(),
        )
