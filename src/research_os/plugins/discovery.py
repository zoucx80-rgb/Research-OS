from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from importlib import metadata
from typing import Any

from research_os.contracts.errors import PluginContractError
from research_os.plugins.models import PluginManifest
from research_os.plugins.registry import PluginRegistry


PLUGIN_ENTRY_POINT_GROUP = "research_os.plugins"


class PluginDiscoveryError(PluginContractError):
    code = "PLUGIN_DISCOVERY_FAILED"


def _distribution_name(entry_point: Any) -> str:
    distribution = getattr(entry_point, "dist", None)
    return str(getattr(distribution, "name", None) or "unknown-distribution")


def _load_plugin(entry_point: Any) -> Any:
    try:
        loaded = entry_point.load()
        if inspect.isclass(loaded):
            return loaded()
        if isinstance(getattr(loaded, "manifest", None), PluginManifest):
            return loaded
        return loaded()
    except Exception as exc:
        raise PluginDiscoveryError(
            "failed to load plugin entry point "
            f"distribution={_distribution_name(entry_point)} "
            f"entry_point={entry_point.name} value={entry_point.value}",
            context={
                "distribution": _distribution_name(entry_point),
                "entry_point": str(entry_point.name),
                "entry_point_value": str(entry_point.value),
            },
        ) from exc


def discover_plugins(
    registry: PluginRegistry,
    *,
    entry_points: Iterable[Any] | None = None,
    entry_point_query: Callable[..., Iterable[Any]] = metadata.entry_points,
) -> tuple[Any, ...]:
    """Load API 2.0 plugins and register them in deterministic plugin-ID order."""

    try:
        candidates = (
            tuple(entry_points)
            if entry_points is not None
            else tuple(entry_point_query(group=PLUGIN_ENTRY_POINT_GROUP))
        )
    except Exception as exc:
        raise PluginDiscoveryError(
            "failed to query plugin entry points",
            context={"entry_point_group": PLUGIN_ENTRY_POINT_GROUP},
        ) from exc
    loaded: list[tuple[Any, Any]] = []
    for entry_point in candidates:
        if (
            getattr(entry_point, "group", PLUGIN_ENTRY_POINT_GROUP)
            != PLUGIN_ENTRY_POINT_GROUP
        ):
            raise PluginDiscoveryError(
                f"unsupported plugin entry point group: {entry_point.group}",
                context={
                    "entry_point": str(entry_point.name),
                    "entry_point_group": str(entry_point.group),
                },
            )
        loaded.append((entry_point, _load_plugin(entry_point)))

    ordered = tuple(
        sorted(
            loaded,
            key=lambda candidate: getattr(
                getattr(candidate[1], "manifest", None), "plugin_id", ""
            ),
        )
    )
    for entry_point, plugin in ordered:
        try:
            registry.register(plugin)
        except Exception as exc:
            plugin_id = str(
                getattr(getattr(plugin, "manifest", None), "plugin_id", "unknown")
            )
            raise PluginDiscoveryError(
                "failed to register discovered plugin "
                f"distribution={_distribution_name(entry_point)} "
                f"entry_point={entry_point.name} value={entry_point.value}",
                context={
                    "distribution": _distribution_name(entry_point),
                    "entry_point": str(entry_point.name),
                    "entry_point_value": str(entry_point.value),
                    "plugin_id": plugin_id,
                },
            ) from exc
    return tuple(plugin for _, plugin in ordered)
