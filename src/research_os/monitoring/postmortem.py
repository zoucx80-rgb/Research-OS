from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from research_os.monitoring.attribution import (
    AttributionRecord,
    AttributionRequest,
    ProcessChangeCandidate,
    attribute_error,
)


class ResearchPostMortem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    prior_run_id: str
    current_run_id: str
    attributions: tuple[AttributionRecord, ...]
    attributed_count: int
    unknown_count: int
    category_counts: Mapping[str, int]
    process_change_candidates: tuple[ProcessChangeCandidate, ...]

    @field_validator("category_counts")
    @classmethod
    def _freeze_counts(cls, value: Mapping[str, int]) -> Mapping[str, int]:
        return MappingProxyType(dict(sorted(value.items())))

    @field_serializer("category_counts")
    def _serialize_counts(self, value: Mapping[str, int]) -> dict[str, int]:
        return dict(value)


class PostMortemService:
    def build(
        self,
        *,
        prior_run_id: str,
        current_run_id: str,
        requests: Sequence[AttributionRequest],
        process_change_candidates: Sequence[ProcessChangeCandidate] = (),
    ) -> ResearchPostMortem:
        if not prior_run_id.strip() or not current_run_id.strip():
            raise ValueError("postmortem run identities must be non-empty")
        if any(
            request.prior_statement.run_id != prior_run_id for request in requests
        ):
            raise ValueError("prior statement must reference the reviewed prior run")
        attributions = tuple(attribute_error(request) for request in requests)
        attribution_ids = {item.attribution_id for item in attributions}
        if len(attribution_ids) != len(attributions):
            raise ValueError("postmortem attribution IDs must be unique")
        unknown_ids = {
            item.attribution_id
            for item in attributions
            if item.category == "UNKNOWN"
        }
        for candidate in process_change_candidates:
            unknown = set(candidate.attribution_ids) - attribution_ids
            if unknown:
                raise ValueError(
                    "process-change candidate references unknown attribution IDs"
                )
            if set(candidate.attribution_ids) & unknown_ids:
                raise ValueError(
                    "process-change candidate cannot rely on UNKNOWN attribution"
                )
        counts = Counter(item.category for item in attributions)
        unknown_count = counts.get("UNKNOWN", 0)
        return ResearchPostMortem(
            prior_run_id=prior_run_id,
            current_run_id=current_run_id,
            attributions=attributions,
            attributed_count=len(attributions) - unknown_count,
            unknown_count=unknown_count,
            category_counts={str(category): count for category, count in counts.items()},
            process_change_candidates=tuple(process_change_candidates),
        )


__all__ = ["PostMortemService", "ResearchPostMortem"]
