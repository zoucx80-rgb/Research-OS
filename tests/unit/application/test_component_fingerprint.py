from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from research_os.application.service import _implementation_fingerprint


def _load_component(path: Path, module_name: str) -> object:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.Component()


def test_implementation_fingerprint_covers_delegated_component_source(
    tmp_path: Path,
):
    plugin_path = tmp_path / "plugin_impl.py"
    provider_path = tmp_path / "provider_impl.py"
    plugin_path.write_text("class Component:\n    marker = 'plugin'\n", encoding="utf-8")
    provider_path.write_text("class Component:\n    marker = 'provider-v1'\n", encoding="utf-8")
    plugin = _load_component(plugin_path, "test_plugin_impl")
    provider = _load_component(provider_path, "test_provider_impl")

    first = _implementation_fingerprint(
        (plugin, provider),
        ("plugin", "external:test", "2.0.0", "2.0"),
    )
    provider_path.write_text("class Component:\n    marker = 'provider-v2'\n", encoding="utf-8")
    second = _implementation_fingerprint(
        (plugin, provider),
        ("plugin", "external:test", "2.0.0", "2.0"),
    )

    assert first != second
