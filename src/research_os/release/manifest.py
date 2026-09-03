from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
import re

from research_os.version import (
    CORE_API_VERSION,
    HTTP_API_VERSION,
    PLUGIN_API_VERSION,
    RESEARCH_OS_VERSION,
    SNAPSHOT_SCHEMA_VERSION,
)


_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class ReleaseManifest:
    """Immutable description of one Research OS release."""

    version: str
    core_api_version: str
    plugin_api_version: str
    snapshot_schema_version: str
    http_api_version: str
    status: str
    module_versions: Mapping[str, str]
    verification_packs: tuple[str, ...]
    field_replay_profiles: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _SEMVER.fullmatch(self.version):
            raise ValueError(f"invalid Research OS version: {self.version!r}")
        if not self.core_api_version:
            raise ValueError("core_api_version must not be empty")
        if not self.plugin_api_version:
            raise ValueError("plugin_api_version must not be empty")
        if not self.snapshot_schema_version:
            raise ValueError("snapshot_schema_version must not be empty")
        if not self.http_api_version:
            raise ValueError("http_api_version must not be empty")
        if self.status not in {"development", "stable"}:
            raise ValueError(f"unsupported release status: {self.status!r}")
        if len(self.verification_packs) != len(set(self.verification_packs)):
            raise ValueError("verification_packs must be unique")
        if len(self.field_replay_profiles) != len(set(self.field_replay_profiles)):
            raise ValueError("field_replay_profiles must be unique")
        object.__setattr__(self, "module_versions", MappingProxyType(dict(self.module_versions)))

    def to_public_metadata(self) -> dict[str, object]:
        return {
            "research_os_version": self.version,
            "core_api_version": self.core_api_version,
            "plugin_api_version": self.plugin_api_version,
            "snapshot_schema_version": self.snapshot_schema_version,
            "http_api_version": self.http_api_version,
            "status": self.status,
            "module_versions": dict(self.module_versions),
        }


CURRENT_RELEASE = ReleaseManifest(
    version=RESEARCH_OS_VERSION,
    core_api_version=CORE_API_VERSION,
    plugin_api_version=PLUGIN_API_VERSION,
    snapshot_schema_version=SNAPSHOT_SCHEMA_VERSION,
    http_api_version=HTTP_API_VERSION,
    status="stable",
    module_versions={
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
    },
    verification_packs=(
        "m1-core-runtime",
        "m2-persistence-http",
        "m3-professional-foundations",
        "m4-reporting-replay",
        "m5-quality-release",
        "release-governance",
    ),
    field_replay_profiles=(
        "field-v1.5.08",
        "field-v1.5.09",
        "field-v1.5.10",
        "field-v1.5.11",
        "field-v1.5.12",
    ),
)
