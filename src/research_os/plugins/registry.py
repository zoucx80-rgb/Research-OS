from __future__ import annotations

from typing import Any

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from research_os.contracts.errors import (
    PluginContractError,
    PluginError,
    PluginVersionUnsupportedError,
)
from research_os.plugins.models import PluginManifest
from research_os.plugins.protocols import KpiProvider, PluginServices


class DuplicatePluginError(PluginError):
    code = "PLUGIN_DUPLICATE"


def _version(value: str, label: str) -> Version:
    try:
        return Version(value)
    except InvalidVersion as exc:
        raise PluginVersionUnsupportedError(
            f"{label} must be a valid PEP 440 version",
            context={"version_label": label, "version_value": value},
        ) from exc


class PluginRegistry:
    def __init__(self, *, core_api_version: str, research_os_version: str):
        self._core_api_version = _version(core_api_version, "core_api_version")
        self._research_os_version = _version(
            research_os_version, "Research OS version"
        )
        self.core_api_version = core_api_version
        self.research_os_version = research_os_version
        self._plugins: dict[str, Any] = {}
        self._services: dict[str, PluginServices] = {}

    @staticmethod
    def _validate_shape(plugin: Any, manifest: PluginManifest) -> PluginServices:
        if manifest.plugin_type == "industry":
            required = ("applicability", "services")
        else:
            required = ("supports", "services")
        missing = [
            name for name in required if not callable(getattr(plugin, name, None))
        ]
        if missing:
            raise PluginContractError(
                f"{manifest.plugin_type} plugin {manifest.plugin_id} is missing contract methods: "
                + ", ".join(missing),
                context={"plugin_id": manifest.plugin_id},
            )
        try:
            services = plugin.services()
        except Exception as exc:
            raise PluginContractError(
                f"plugin {manifest.plugin_id} services() failed",
                context={"plugin_id": manifest.plugin_id},
            ) from exc
        if not isinstance(services, PluginServices):
            raise PluginContractError(
                f"plugin {manifest.plugin_id} services() must return PluginServices",
                context={"plugin_id": manifest.plugin_id},
            )
        if services.kpi_provider is not None:
            if not isinstance(services.kpi_provider, KpiProvider):
                raise PluginContractError(
                    f"plugin {manifest.plugin_id} kpi_provider does not satisfy "
                    "KpiProvider",
                    context={"plugin_id": manifest.plugin_id},
                )
            _version(
                services.kpi_provider.provider_version,
                f"plugin {manifest.plugin_id} KPI provider version",
            )
            if not services.kpi_provider.provider_id.strip():
                raise PluginContractError(
                    f"plugin {manifest.plugin_id} KPI provider_id must be non-empty",
                    context={"plugin_id": manifest.plugin_id},
                )
        actual_capabilities = frozenset(
            capability
            for capability, present in (
                ("kpi.metrics", services.kpi_provider is not None),
                ("valuation.methods", bool(services.valuation_methods)),
                ("forecast.methods", bool(services.forecast_methods)),
                ("policy.contributions", bool(services.policy_contributions)),
                ("report.contributions", bool(services.report_contributions)),
            )
            if present
        )
        if manifest.service_capabilities != actual_capabilities:
            raise PluginContractError(
                f"plugin {manifest.plugin_id} service_capabilities do not match "
                "services(); "
                f"declared={sorted(manifest.service_capabilities)}, "
                f"actual={sorted(actual_capabilities)}",
                context={"plugin_id": manifest.plugin_id},
            )
        return services

    def _validate_compatibility(self, manifest: PluginManifest) -> None:
        core_api_specifier = SpecifierSet(manifest.core_api_specifier)
        if self._core_api_version not in core_api_specifier:
            raise PluginVersionUnsupportedError(
                f"plugin {manifest.plugin_id} is incompatible with core API "
                f"{self.core_api_version}; required {manifest.core_api_specifier}",
                context={
                    "plugin_id": manifest.plugin_id,
                    "core_api_version": self.core_api_version,
                    "required_specifier": manifest.core_api_specifier,
                },
            )
        research_os_specifier = SpecifierSet(manifest.research_os_specifier)
        if self._research_os_version not in research_os_specifier:
            raise PluginVersionUnsupportedError(
                f"plugin {manifest.plugin_id} is incompatible with Research OS "
                f"{self.research_os_version}; required "
                f"{manifest.research_os_specifier}",
                context={
                    "plugin_id": manifest.plugin_id,
                    "research_os_version": self.research_os_version,
                    "required_specifier": manifest.research_os_specifier,
                },
            )

    def register(self, plugin: Any) -> None:
        manifest = getattr(plugin, "manifest", None)
        if not isinstance(manifest, PluginManifest):
            raise PluginContractError("plugin must expose a PluginManifest as manifest")
        if manifest.plugin_id in self._plugins:
            raise DuplicatePluginError(
                f"duplicate plugin_id: {manifest.plugin_id}",
                context={"plugin_id": manifest.plugin_id},
            )

        services = self._validate_shape(plugin, manifest)
        self._validate_compatibility(manifest)
        self._plugins[manifest.plugin_id] = plugin
        self._services[manifest.plugin_id] = services

    def manifests(self, plugin_type: str | None = None) -> list[PluginManifest]:
        manifests = [plugin.manifest for plugin in self._plugins.values()]
        if plugin_type is not None:
            manifests = [m for m in manifests if m.plugin_type == plugin_type]
        return sorted(manifests, key=lambda manifest: manifest.plugin_id)

    def get(self, plugin_id: str) -> Any | None:
        return self._plugins.get(plugin_id)

    def require(self, plugin_id: str) -> Any:
        plugin = self.get(plugin_id)
        if plugin is None:
            raise PluginContractError(
                f"plugin is not registered: {plugin_id}",
                context={"plugin_id": plugin_id},
            )
        return plugin

    def services(self, plugin_id: str) -> PluginServices | None:
        return self._services.get(plugin_id)
