from __future__ import annotations

from typing import Literal, Self

from pydantic import field_validator, model_validator

from research_os.contracts.artifact_values import DomainArtifact, LineageValue


CoverageLevel = Literal["COMPLETE", "PARTIAL", "MISSING", "NOT_APPLICABLE"]
ModelExecutability = Literal["EXECUTABLE", "BLOCKED", "NOT_APPLICABLE"]
SufficiencyStatus = Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT_EVIDENCE"]


def _canonical_strings(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values)
    if any(not value for value in normalized):
        raise ValueError(f"{label} must be non-empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} must be unique")
    return tuple(sorted(normalized))


class MaterialResearchGap(LineageValue):
    gap_key: str
    domain_id: str
    reason_code: str
    description: str
    required_evidence: tuple[str, ...]

    @field_validator("gap_key", "domain_id", "reason_code", "description")
    @classmethod
    def _non_empty_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("material gap fields must be non-empty")
        return normalized

    @field_validator("required_evidence")
    @classmethod
    def _canonical_required_evidence(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        canonical = _canonical_strings(value, label="required evidence")
        if not canonical:
            raise ValueError("material gap requires upgrade evidence")
        return canonical


class DomainSufficiencyAssessment(LineageValue):
    domain_id: str
    coverage: CoverageLevel
    evidence_quality: CoverageLevel
    temporal_coverage: CoverageLevel
    benchmark_coverage: CoverageLevel
    peer_coverage: CoverageLevel
    model_executability: ModelExecutability
    known_items: tuple[str, ...]
    unknown_items: tuple[str, ...]
    why_unknown: tuple[str, ...]
    upgrade_evidence_requirements: tuple[str, ...]
    material_gaps: tuple[MaterialResearchGap, ...]

    @field_validator("domain_id")
    @classmethod
    def _non_empty_domain_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("sufficiency domain_id must be non-empty")
        return normalized

    @field_validator(
        "known_items",
        "unknown_items",
        "why_unknown",
        "upgrade_evidence_requirements",
    )
    @classmethod
    def _canonical_items(cls, value: tuple[str, ...], info: object) -> tuple[str, ...]:
        return _canonical_strings(
            value,
            label=getattr(info, "field_name", "sufficiency items").replace("_", " "),
        )

    @field_validator("material_gaps")
    @classmethod
    def _canonical_material_gaps(
        cls,
        value: tuple[MaterialResearchGap, ...],
    ) -> tuple[MaterialResearchGap, ...]:
        identities = tuple(item.gap_key for item in value)
        if len(identities) != len(set(identities)):
            raise ValueError("material gap identities must be unique")
        return tuple(sorted(value, key=lambda item: item.gap_key))

    @model_validator(mode="after")
    def _gaps_belong_to_domain(self) -> Self:
        foreign = tuple(
            item.gap_key for item in self.material_gaps if item.domain_id != self.domain_id
        )
        if foreign:
            raise ValueError("material gaps must belong to their sufficiency domain")
        return self


class ResearchSufficiencyAssessment(DomainArtifact):
    overall_status: SufficiencyStatus = "INSUFFICIENT_EVIDENCE"
    domains: tuple[DomainSufficiencyAssessment, ...] = ()
    blocking_gap_keys: tuple[str, ...] = ()

    @field_validator("domains")
    @classmethod
    def _canonical_domains(
        cls,
        value: tuple[DomainSufficiencyAssessment, ...],
    ) -> tuple[DomainSufficiencyAssessment, ...]:
        identities = tuple(item.domain_id for item in value)
        if len(identities) != len(set(identities)):
            raise ValueError("sufficiency domain identities must be unique")
        return tuple(sorted(value, key=lambda item: item.domain_id))

    @field_validator("blocking_gap_keys")
    @classmethod
    def _canonical_blocking_gaps(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _canonical_strings(value, label="blocking gap keys")

    @model_validator(mode="after")
    def _blocking_gaps_are_material(self) -> Self:
        material_keys = {gap.gap_key for domain in self.domains for gap in domain.material_gaps}
        unknown = set(self.blocking_gap_keys) - material_keys
        if unknown:
            raise ValueError("blocking gaps must reference material gap identities")
        if self.overall_status == "SUFFICIENT" and self.blocking_gap_keys:
            raise ValueError("sufficient research cannot have blocking gaps")
        return self

    def require_domain(self, domain_id: str) -> DomainSufficiencyAssessment:
        for domain in self.domains:
            if domain.domain_id == domain_id:
                return domain
        raise KeyError(f"unknown sufficiency domain: {domain_id}")
