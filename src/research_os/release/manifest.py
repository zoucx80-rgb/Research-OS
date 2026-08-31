from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
import re

from research_os.version import CORE_API_VERSION, RESEARCH_OS_VERSION


_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class ReleaseManifest:
    """Immutable description of one Research OS release.

    Version identity comes from the import-free ``research_os.version`` leaf so
    build tooling can read it before the package is installed. The manifest is
    the canonical descriptor for release policy, component fingerprints and
    verification composition.
    """

    version: str
    core_api_version: str
    status: str
    module_versions: Mapping[str, str]
    verification_packs: tuple[str, ...]
    field_replay_profiles: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _SEMVER.fullmatch(self.version):
            raise ValueError(f"invalid Research OS version: {self.version!r}")
        if not self.core_api_version:
            raise ValueError("core_api_version must not be empty")
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
            "status": self.status,
            "module_versions": dict(self.module_versions),
        }


CURRENT_RELEASE = ReleaseManifest(
    version=RESEARCH_OS_VERSION,
    core_api_version=CORE_API_VERSION,
    status="stable",
    module_versions={
        "finance_core": "2.0.1",
        "router": "1.2.0",
        "driver_engine": "1.4.0",
        "thesis_engine": "1.2.0",
        "expectation_engine": "1.2.0",
        "valuation": "2.2.0",
        "evidence_lineage": "2.0.0",
        "safety_gates": "1.0.0",
        "period_semantics": "1.1.0",
        "missing_value_semantics": "1.1.0",
        "funding_loop": "1.1.0",
        "kpi_applicability": "1.0.0",
        "completion_gate": "1.1.0",
        "report_template": "3.1.2",
        "semantic_presentation": "1.0.0",
        "semantic_research_view": "1.6.0",
        "financial_fact_snapshot": "1.0.0",
        "research_completeness": "1.0.0",
        "report_composer": "1.3.0",
        "markdown_renderer": "1.3.0",
        "html_renderer": "1.0.0",
        "pdf_adapter": "1.0.0",
    },
    verification_packs=(
        "stable-baseline",
        "release-governance",
        "semantic-correctness",
    ),
    field_replay_profiles=(
        "field-v1.5.08",
        "field-v1.5.09",
        "field-v1.5.10",
        "field-v1.5.11",
    ),
)
