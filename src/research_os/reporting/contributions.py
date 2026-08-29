from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReportContribution(BaseModel):
    model_config = ConfigDict(frozen=True)

    contribution_id: str
    section: str
    order: int
    artifact_keys: list[str] = Field(default_factory=list)
    required: bool = False
