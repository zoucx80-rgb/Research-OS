from __future__ import annotations

from typing import Literal, Self

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.contracts.evidence import EvidenceRef


PluginType = Literal["industry", "methodology"]
PluginMaturity = Literal["experimental", "candidate", "stable", "deprecated"]


def _canonical_evidence_refs(
    references: tuple[EvidenceRef, ...],
) -> tuple[EvidenceRef, ...]:
    by_id: dict[str, EvidenceRef] = {}
    for reference in references:
        existing = by_id.get(reference.evidence_id)
        if existing is not None and existing != reference:
            raise ValueError("plugin assessment lineage has conflicting evidence revisions")
        by_id[reference.evidence_id] = reference
    return tuple(
        sorted(
            by_id.values(),
            key=lambda item: (
                item.evidence_id,
                item.revision,
                item.content_fingerprint,
            ),
        )
    )


class PluginManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    plugin_id: str
    plugin_type: PluginType
    plugin_version: str
    plugin_api_version: Literal["2.0"]
    core_api_specifier: str
    research_os_specifier: str
    supported_business_models: frozenset[str] = Field(default_factory=frozenset)
    service_capabilities: frozenset[str] = Field(default_factory=frozenset)
    priority: int = 100
    maturity: PluginMaturity = "experimental"

    @field_validator("plugin_id")
    @classmethod
    def _non_empty_identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("plugin_id must be non-empty")
        return value

    @field_validator("plugin_version")
    @classmethod
    def _valid_plugin_version(cls, value: str) -> str:
        try:
            Version(value)
        except InvalidVersion as exc:
            raise ValueError("plugin_version must be a valid PEP 440 version") from exc
        return value

    @field_validator("core_api_specifier", "research_os_specifier")
    @classmethod
    def _valid_specifier(cls, value: str) -> str:
        try:
            specifier = SpecifierSet(value)
        except InvalidSpecifier as exc:
            raise ValueError("plugin compatibility range must be a valid specifier") from exc
        if not str(specifier):
            raise ValueError("plugin compatibility range must be non-empty")
        return value

    @field_validator("supported_business_models", "service_capabilities")
    @classmethod
    def _valid_identifiers(cls, values: frozenset[str]) -> frozenset[str]:
        if any(not value.strip() for value in values):
            raise ValueError("plugin identifiers must be non-empty")
        return values


class ApplicabilityResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    applicable: bool
    rule_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    limitations: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("evidence_refs")
    @classmethod
    def _canonical_lineage(cls, references: tuple[EvidenceRef, ...]) -> tuple[EvidenceRef, ...]:
        return _canonical_evidence_refs(references)


class SupportAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    supported: bool
    rationale: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    limitations: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("evidence_refs")
    @classmethod
    def _canonical_lineage(cls, references: tuple[EvidenceRef, ...]) -> tuple[EvidenceRef, ...]:
        return _canonical_evidence_refs(references)


class ResolvedPlugin(BaseModel):
    model_config = ConfigDict(frozen=True)

    plugin_id: str
    plugin_type: PluginType
    plugin_version: str
    plugin_api_version: Literal["2.0"]
    priority: int
    maturity: PluginMaturity
    applicability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)

    @field_validator("evidence_refs")
    @classmethod
    def _canonical_lineage(cls, references: tuple[EvidenceRef, ...]) -> tuple[EvidenceRef, ...]:
        return _canonical_evidence_refs(references)


class CoverageGap(BaseModel):
    model_config = ConfigDict(frozen=True)

    gap_type: Literal[
        "industry_strategy",
        "methodology",
        "capability",
        "business_model_taxonomy",
        "business_model_evidence",
        "business_model_ambiguity",
    ]
    business_model: str | None = None
    missing_capability: str | None = None
    reason: str
    reason_code: str | None = None
    affected_capabilities: tuple[str, ...] = Field(default_factory=tuple)
    fallback_available: bool | None = None


class StrategyResolution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    industry_plugins: tuple[ResolvedPlugin, ...] = Field(default_factory=tuple)
    methodology_plugins: tuple[ResolvedPlugin, ...] = Field(default_factory=tuple)
    coverage_gaps: tuple[CoverageGap, ...] = Field(default_factory=tuple)
    rationale: tuple[str, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)

    @field_validator("evidence_refs")
    @classmethod
    def _canonical_lineage(cls, references: tuple[EvidenceRef, ...]) -> tuple[EvidenceRef, ...]:
        return _canonical_evidence_refs(references)


class ExtensionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_id: str
    business_model: str
    coverage_gaps: tuple[CoverageGap, ...] = Field(default_factory=tuple)
    evidence_requirements: tuple[str, ...] = Field(default_factory=tuple)
    requested_capabilities: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _require_a_gap_or_capability(self) -> Self:
        if not self.coverage_gaps and not self.requested_capabilities:
            raise ValueError("extension request requires a gap or requested capability")
        return self
