from __future__ import annotations

from research_os.contracts.versioning import (
    CORE_API_VERSION,
    PLUGIN_API_VERSION,
    RESEARCH_OS_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
)
from research_os.release import CURRENT_RELEASE_MANIFEST
from research_os.version import __version__


def test_v1_6_version_constants_are_consistent() -> None:
    assert RESEARCH_OS_VERSION == "1.6.0"
    assert __version__ == RESEARCH_OS_VERSION
    assert CORE_API_VERSION == "2.0"
    assert PLUGIN_API_VERSION == "2.0"
    assert SNAPSHOT_SCHEMA_VERSION == "2.0"


def test_stable_manifest_lists_implemented_v1_6_components() -> None:
    manifest = CURRENT_RELEASE_MANIFEST

    assert manifest.release_version == "1.6.0"
    assert manifest.status == "stable"
    assert manifest.core_api_version == "2.0"
    assert manifest.plugin_api_version == "2.0"
    assert manifest.snapshot_schema_version == "2.0"
    assert (
        manifest.module_versions["research_os.runtime"]
        == "research-runtime-v1.6.0-m1"
    )
    assert (
        manifest.module_versions["research_os.fixtures"]
        == "research-fixtures-v1.6.0-m1"
    )
    assert (
        manifest.module_versions["research_os.decision"]
        == "research-decision-v1.6.0-m2"
    )
    assert (
        manifest.module_versions["research_os.forecasting"]
        == "research-forecasting-v1.6.0-m3"
    )
    assert (
        manifest.module_versions["research_os.reporting"]
        == "research-reporting-v1.6.0-m4"
    )
    assert (
        manifest.module_versions["research_os.presentation"]
        == "research-presentation-v1.6.0-m4"
    )
    assert (
        manifest.module_versions["research_os.release"]
        == "research-release-governance-v1.6.0"
    )
