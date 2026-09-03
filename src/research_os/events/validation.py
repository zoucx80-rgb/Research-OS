from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class NextVerificationEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_name: str
    event_time: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class TemporalValidationResult(BaseModel):
    status: Literal["PASS", "FAIL"]
    errors: list[str] = Field(default_factory=list)


class NextVerificationEventValidator:
    def validate(
        self,
        event: NextVerificationEvent,
        *,
        reference_time: datetime,
        used_evidence_ids: list[str],
    ) -> TemporalValidationResult:
        errors: list[str] = []
        if event.event_time is not None and event.event_time <= reference_time:
            errors.append("next verification event must occur after the research reference time")
        overlap = sorted(set(event.evidence_ids) & set(used_evidence_ids))
        if overlap:
            errors.append(
                f"next verification event reuses evidence already consumed by the run: {', '.join(overlap)}"
            )
        return TemporalValidationResult(status="FAIL" if errors else "PASS", errors=errors)
