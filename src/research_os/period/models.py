from __future__ import annotations

from datetime import date
from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PeriodType = Literal["Q1", "H1", "Q1_Q3", "FY", "CUSTOM"]


class ReportingPeriod(BaseModel):
    model_config = ConfigDict(frozen=True)

    period_type: PeriodType = "FY"
    period_start: date | None = None
    period_end: date | None = None
    period_days: int | None = Field(default=None, gt=0)
    is_cumulative: bool = True

    @field_validator("period_type", mode="before")
    @classmethod
    def normalize_period_type(cls, value: Any):
        if value is None:
            return "FY"
        text = str(value).strip().upper().replace("-", "_")
        if text == "Q1_Q3":
            return "Q1_Q3"
        return text

    @model_validator(mode="after")
    def validate_dates(self):
        if (
            self.period_start is not None
            and self.period_end is not None
            and self.period_end < self.period_start
        ):
            raise ValueError("period_end must be on or after period_start")
        return self

    @classmethod
    def coerce(cls, value: ReportingPeriod | Mapping[str, Any] | None) -> ReportingPeriod:
        if isinstance(value, cls):
            return value
        if value is None:
            return cls(period_type="FY")
        return cls.model_validate(dict(value))

    @classmethod
    def from_facts(cls, facts: Mapping[str, Any]) -> ReportingPeriod:
        raw = facts.get("reporting_period")
        if raw is not None:
            return cls.coerce(raw)
        return cls.model_validate(
            {
                "period_type": facts.get("period_type", "FY"),
                "period_start": facts.get("period_start"),
                "period_end": facts.get("period_end"),
                "period_days": facts.get("period_days"),
                "is_cumulative": facts.get("is_cumulative", True),
            }
        )
