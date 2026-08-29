from typing import Literal

from pydantic import BaseModel, Field


ModuleStatus = Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"]
FinalStatus = Literal["COMPLETE", "INCOMPLETE"]


class ResearchCompletionInput(BaseModel):
    module_statuses: dict[str, ModuleStatus]
    tool_completed: bool = False
    claimed_conclusions: list[str] = Field(default_factory=list)


class ResearchCompletionResult(BaseModel):
    final_status: FinalStatus
    blocking_modules: list[str] = Field(default_factory=list)
    module_statuses: dict[str, ModuleStatus]
