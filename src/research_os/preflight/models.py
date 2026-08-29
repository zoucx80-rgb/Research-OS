from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class RepositoryPreflightEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    repository_full_name: str
    repository_id: int
    branch: str
    head_sha: str
    head_commit_message: str
    agents_blob_sha: str
    research_prompt_blob_sha: str
    verified_at: datetime
    agents_ref: str
    research_prompt_ref: str


class PreflightValidationResult(BaseModel):
    status: Literal["PASS"] = "PASS"
    repository_full_name: str
    repository_id: int
    branch: str
    head_sha: str
