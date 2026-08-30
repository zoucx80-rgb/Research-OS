from typing import Literal

from pydantic import BaseModel, Field


ClassificationStatus = Literal[
    "classified",
    "unsupported_taxonomy",
    "insufficient_evidence",
]


class BusinessModelProfile(BaseModel):
    company_id: str
    primary_model: str
    secondary_models: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    router_version: str = "router@1.1.0"
    manual_override: bool = False
    classification_status: ClassificationStatus = "classified"
    classification_reason: str | None = None
    lease_heavy: bool = False
