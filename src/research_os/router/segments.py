from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import Ratio


class SegmentProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    segment_id: str
    business_model: str
    revenue_share: Ratio | None = None
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)

    @field_validator("segment_id", "business_model")
    @classmethod
    def _identity_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("segment profile identity must be non-empty")
        return normalized

    @field_validator("revenue_share")
    @classmethod
    def _valid_share(cls, value: Ratio | None) -> Ratio | None:
        if value is not None and not 0 <= value.decimal_value <= 1:
            raise ValueError("segment revenue share must be between zero and one")
        return value


def primary_segment(
    profiles: tuple[SegmentProfile, ...],
) -> SegmentProfile | None:
    """Return a primary segment only when all revenue shares are explicit."""

    if not profiles or any(item.revenue_share is None for item in profiles):
        return None
    return sorted(
        profiles,
        key=lambda item: (-item.revenue_share.decimal_value, item.segment_id),  # type: ignore[union-attr]
    )[0]


__all__ = ["SegmentProfile", "primary_segment"]
