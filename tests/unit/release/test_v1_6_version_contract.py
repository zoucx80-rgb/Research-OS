from __future__ import annotations

import json
from pathlib import Path

import research_os
from research_os.release.manifest import CURRENT_RELEASE
from research_os.version import (
    CORE_API_VERSION,
    HTTP_API_VERSION,
    PLUGIN_API_VERSION,
    RESEARCH_OS_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
)


def test_v1_6_version_contract_is_authoritative_across_public_surfaces() -> None:
    assert RESEARCH_OS_VERSION == research_os.__version__ == "1.6.0"
    assert CORE_API_VERSION == "2.0"
    assert PLUGIN_API_VERSION == "2.0"
    assert SNAPSHOT_SCHEMA_VERSION == "2.0"
    assert HTTP_API_VERSION == "v1"

    assert CURRENT_RELEASE.version == RESEARCH_OS_VERSION
    assert CURRENT_RELEASE.core_api_version == CORE_API_VERSION
    assert CURRENT_RELEASE.plugin_api_version == PLUGIN_API_VERSION
    assert CURRENT_RELEASE.snapshot_schema_version == SNAPSHOT_SCHEMA_VERSION
    assert CURRENT_RELEASE.http_api_version == HTTP_API_VERSION
    assert CURRENT_RELEASE.status == "stable"


def test_generated_public_metadata_matches_the_v1_6_manifest() -> None:
    metadata = json.loads(Path("research_os_version.json").read_text(encoding="utf-8"))

    assert metadata == CURRENT_RELEASE.to_public_metadata()


def test_stable_manifest_lists_implemented_v1_6_components() -> None:
    assert CURRENT_RELEASE.module_versions == {
        "repository_preflight": "2.0.0",
        "pit_lineage": "2.0.0",
        "financial_fact_snapshot": "1.0.0",
        "business_model": "2.0.0",
        "resolved_strategy": "2.0.0",
        "kpi_provider": "2.0.0",
        "completion_evaluator": "2.0.0",
        "readiness_evaluator": "2.0.0",
        "snapshot_codec": "2.0.0",
        "sql_persistence": "2.0.0",
        "research_query": "1.0.0",
        "http_api": "1.0.0",
        "research_view": "2.0.0",
        "report_composer": "2.0.0",
        "markdown_renderer": "2.0.0",
        "html_renderer": "1.0.0",
        "pdf_adapter": "1.0.0",
        "historical_replay": "1.0.0",
    }
