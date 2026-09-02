from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PolicySelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_id: str
    policy_version: str
    parameters_fingerprint: str

    @field_validator("policy_id", "policy_version", "parameters_fingerprint")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("policy selection fields must be non-empty")
        return value


class PolicySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    policies: tuple[PolicySelection, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _sort_and_reject_duplicates(self) -> PolicySnapshot:
        policy_ids = [item.policy_id for item in self.policies]
        if len(policy_ids) != len(set(policy_ids)):
            raise ValueError("duplicate policy_id in policy snapshot")
        object.__setattr__(
            self,
            "policies",
            tuple(sorted(self.policies, key=lambda item: item.policy_id)),
        )
        return self

    def get(self, policy_id: str) -> PolicySelection | None:
        return next((item for item in self.policies if item.policy_id == policy_id), None)
