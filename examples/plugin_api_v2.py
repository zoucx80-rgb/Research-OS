"""Minimal Plugin API 2.0 registration example."""

from __future__ import annotations

import json

from research_os.plugins.models import ApplicabilityResult, PluginManifest
from research_os.plugins.protocols import PluginServices
from research_os.plugins.registry import PluginRegistry
from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


class ExampleIndustryPlugin:
    manifest = PluginManifest(
        plugin_id="example.industry.manufacturing",
        plugin_type="industry",
        plugin_version="1.0.0",
        plugin_api_version="2.0",
        core_api_specifier=">=2.0,<3.0",
        research_os_specifier=">=1.6,<2.0",
        supported_business_models=frozenset(("manufacturing",)),
        service_capabilities=frozenset(),
        priority=100,
        maturity="stable",
    )

    def applicability(self, context, business_model) -> ApplicabilityResult:
        del context
        applicable = business_model.primary_model in self.manifest.supported_business_models
        return ApplicabilityResult(
            applicable=applicable,
            rule_score=1.0 if applicable else 0.0,
            rationale=("example business-model match",),
        )

    def services(self) -> PluginServices:
        return PluginServices()


def main() -> None:
    registry = PluginRegistry(
        core_api_version=CORE_API_VERSION,
        research_os_version=RESEARCH_OS_VERSION,
    )
    plugin = ExampleIndustryPlugin()
    registry.register(plugin)
    registered = registry.require(plugin.manifest.plugin_id)
    print(
        json.dumps(
            {
                "plugin_id": registered.manifest.plugin_id,
                "plugin_api_version": registered.manifest.plugin_api_version,
                "core_api_specifier": registered.manifest.core_api_specifier,
                "service_capabilities": sorted(registered.manifest.service_capabilities),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
