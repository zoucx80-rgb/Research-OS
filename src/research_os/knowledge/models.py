from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    topic: str
    business_model: str | None = None
    as_of: datetime
    tags: set[str] = Field(default_factory=set)


class KnowledgeItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    knowledge_id: str
    content: Any
    source_id: str
    publish_ts: datetime | None = None
    version: str
    evidence_ids: list[str] = Field(default_factory=list)
