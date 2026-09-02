from __future__ import annotations

from types import MappingProxyType
from typing import Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research_os.runtime.modules import ModuleStatus


FinalStatus = Literal["COMPLETE", "INCOMPLETE"]


class ExecutionCompletionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    final_status: FinalStatus
    blocking_capabilities: tuple[str, ...] = Field(default_factory=tuple)
    module_statuses: Mapping[str, ModuleStatus]

    @model_validator(mode="after")
    def _freeze_and_validate(self) -> ExecutionCompletionResult:
        blocking = tuple(sorted(set(self.blocking_capabilities)))
        if (self.final_status == "COMPLETE") != (not blocking):
            raise ValueError("completion status must match blocking capabilities")
        object.__setattr__(self, "blocking_capabilities", blocking)
        object.__setattr__(
            self,
            "module_statuses",
            MappingProxyType(dict(sorted(self.module_statuses.items()))),
        )
        return self
