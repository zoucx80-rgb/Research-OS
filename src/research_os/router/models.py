from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_os.contracts.evidence import EvidenceRef


ClassificationStatus = Literal[
    "classified",
    "unsupported_taxonomy",
    "insufficient_evidence",
]


class BusinessModelProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    company_id: str
    primary_model: str
    secondary_models: tuple[str, ...] = Field(default_factory=tuple)
    confidence: float = Field(ge=0, le=1)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    router_version: str = "router@1.1.0"
    manual_override: bool = False
    classification_status: ClassificationStatus = "classified"
    classification_reason: str | None = None
    lease_heavy: bool = False

    @field_validator("evidence_refs")
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
