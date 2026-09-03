from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_os.contracts.evidence import EvidenceRef
from research_os.router.segments import SegmentProfile


ClassificationStatus = Literal[
    "CLASSIFIED",
    "UNRESOLVED",
    "UNSUPPORTED_TAXONOMY",
    "INSUFFICIENT_EVIDENCE",
]

ConfidenceBand = Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]


class RoutingCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_id: str
    rule_match_score: float = Field(ge=0)
    positive_evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    counter_evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)


class BusinessModelProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    company_id: str
    primary_model: str
    secondary_models: tuple[str, ...] = Field(default_factory=tuple)
    rule_match_score: float = Field(default=0, ge=0)
    usable_evidence_coverage: float = Field(default=0, ge=0, le=1)
    confidence_band: ConfidenceBand = "UNKNOWN"
    ambiguity: float = Field(default=1, ge=0, le=1)
    candidates: tuple[RoutingCandidate, ...] = Field(default_factory=tuple)
    positive_evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    counter_evidence: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    segment_profiles: tuple[SegmentProfile, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    router_version: str = "router@1.1.0"
    manual_override: bool = False
    classification_status: ClassificationStatus = "CLASSIFIED"
    classification_reason: str | None = None
    lease_heavy: bool = False

    @field_validator("evidence_refs", "positive_evidence", "counter_evidence")
    @classmethod
    def _canonical_evidence_refs(
        cls, references: tuple[EvidenceRef, ...]
    ) -> tuple[EvidenceRef, ...]:
        by_id: dict[str, EvidenceRef] = {}
        for reference in references:
            existing = by_id.get(reference.evidence_id)
            if existing is not None and existing != reference:
                raise ValueError(
                    "business model lineage has conflicting evidence revisions"
                )
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
