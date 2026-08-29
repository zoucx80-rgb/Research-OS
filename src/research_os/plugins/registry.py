from __future__ import annotations

import re
from typing import Any

from research_os.plugins.models import PluginManifest


class PluginCompatibilityError(ValueError):
    pass


class DuplicatePluginError(ValueError):
    pass


_SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _semver(value: str, label: str) -> tuple[int, int, int]:
    match = _SEMVER_RE.fullmatch(value.strip())
    if match is None:
        raise PluginCompatibilityError(
            f"{label} must use MAJOR.MINOR.PATCH semantic versioning: {value!r}"
        )
    return tuple(int(part) for part in match.groups())


class PluginRegistry:
    def __init__(self, *, core_api_version: str, research_os_version: str):
        if not core_api_version.strip():
            raise ValueError("core_api_version must be non-empty")
        self.core_api_version = core_api_version
        self.research_os_version = research_os_version
        self._research_os_semver = _semver(research_os_version, "Research OS version")
        self._plugins: dict[str, Any] = {}

    @staticmethod
    def _validate_shape(plugin: Any, manifest: PluginManifest) -> None:
        if manifest.plugin_type == "industry":
            required = ("applicability", "modules", "report_contributions")
        else:
            required = ("supports", "modules")
        missing = [name for name in required if not callable(getattr(plugin, name, None))]
        if missing:
            raise PluginCompatibilityError(
                f"{manifest.plugin_type} plugin {manifest.plugin_id} is missing contract methods: "
                + ", ".join(missing)
            )

    def _validate_compatibility(self, manifest: PluginManifest) -> None:
        if manifest.api_version != self.core_api_version:
            raise PluginCompatibilityError(
                f"plugin {manifest.plugin_id} api_version {manifest.api_version} is incompatible "
                f"with core api {self.core_api_version}"
            )

        _semver(manifest.plugin_version, f"plugin {manifest.plugin_id} version")
        minimum = _semver(
            manifest.min_research_os_version,
            f"plugin {manifest.plugin_id} min Research OS version",
        )
        maximum = None
        if manifest.max_research_os_version is not None:
            maximum = _semver(
                manifest.max_research_os_version,
                f"plugin {manifest.plugin_id} max Research OS version",
            )
            if maximum < minimum:
                raise PluginCompatibilityError(
                    f"plugin {manifest.plugin_id} Research OS version range is invalid"
                )

        if self._research_os_semver < minimum or (
            maximum is not None and self._research_os_semver > maximum
        ):
            upper = manifest.max_research_os_version or "unbounded"
            raise PluginCompatibilityError(
                f"plugin {manifest.plugin_id} is incompatible with Research OS "
                f"{self.research_os_version}; supported range is "
                f"{manifest.min_research_os_version}..{upper}"
            )

    def register(self, plugin: Any) -> None:
        manifest = getattr(plugin, "manifest", None)
        if not isinstance(manifest, PluginManifest):
            raise PluginCompatibilityError("plugin must expose a PluginManifest as manifest")
        if manifest.plugin_id in self._plugins:
            raise DuplicatePluginError(f"duplicate plugin_id: {manifest.plugin_id}")

        self._validate_shape(plugin, manifest)
        self._validate_compatibility(manifest)
        self._plugins[manifest.plugin_id] = plugin

    def manifests(self, plugin_type: str | None = None) -> list[PluginManifest]:
        manifests = [plugin.manifest for plugin in self._plugins.values()]
        if plugin_type is not None:
            manifests = [m for m in manifests if m.plugin_type == plugin_type]
        return sorted(manifests, key=lambda manifest: manifest.plugin_id)

    def get(self, plugin_id: str) -> Any | None:
        return self._plugins.get(plugin_id)
