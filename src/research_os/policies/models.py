from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Literal, Mapping

from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
    field_validator,
    model_validator,
)


PolicyValueType = Literal["decimal", "integer", "boolean", "string"]


class PolicyParameter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    value: object
    value_type: PolicyValueType
    unit: str
    minimum: Decimal | int | None = None
    maximum: Decimal | int | None = None

    @field_validator("unit")
    @classmethod
    def _unit_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("policy parameter unit must be non-empty")
        return normalized

    @model_validator(mode="after")
    def _validate_declared_type_and_range(self) -> PolicyParameter:
        valid = {
            "decimal": isinstance(self.value, Decimal),
            "integer": isinstance(self.value, int) and not isinstance(self.value, bool),
            "boolean": isinstance(self.value, bool),
            "string": isinstance(self.value, str),
        }[self.value_type]
        if not valid:
            raise ValueError(
                f"policy parameter value must match declared {self.value_type} type"
            )
        if isinstance(self.value, (Decimal, int)) and not isinstance(self.value, bool):
            if self.minimum is not None and self.value < self.minimum:
                raise ValueError("policy parameter value is below minimum")
            if self.maximum is not None and self.value > self.maximum:
                raise ValueError("policy parameter value exceeds maximum")
        elif self.minimum is not None or self.maximum is not None:
            raise ValueError("only numeric policy parameters may declare a range")
        return self


class PolicyDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    policy_id: str
    policy_version: str
    policy_type: str
    applicability: frozenset[str]
    parameters: Mapping[str, PolicyParameter]
    rationale: str
    source: str

    @field_validator(
        "policy_id", "policy_version", "policy_type", "rationale", "source"
    )
    @classmethod
    def _identity_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("policy definition fields must be non-empty")
        return normalized

    @field_validator("parameters")
    @classmethod
    def _freeze_parameters(
        cls, value: Mapping[str, PolicyParameter]
    ) -> Mapping[str, PolicyParameter]:
        if not value or any(not key.strip() for key in value):
            raise ValueError("policy parameters must have non-empty keys")
        return MappingProxyType(dict(sorted(value.items())))

    @field_serializer("parameters")
    def _serialize_parameters(
        self, value: Mapping[str, PolicyParameter]
    ) -> dict[str, PolicyParameter]:
        return dict(value)


class PolicyOverride(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    policy_id: str
    base_policy_version: str
    operator: str
    reason: str
    override_ts: datetime
    parameters: Mapping[str, PolicyParameter]

    @field_validator("policy_id", "base_policy_version", "operator", "reason")
    @classmethod
    def _audit_fields_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("policy override audit fields must be non-empty")
        return normalized

    @field_validator("override_ts")
    @classmethod
    def _utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("policy override time must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("parameters")
    @classmethod
    def _freeze_parameters(
        cls, value: Mapping[str, PolicyParameter]
    ) -> Mapping[str, PolicyParameter]:
        if not value:
            raise ValueError("policy override must change at least one parameter")
        return MappingProxyType(dict(sorted(value.items())))

    @field_serializer("parameters")
    def _serialize_parameters(
        self, value: Mapping[str, PolicyParameter]
    ) -> dict[str, PolicyParameter]:
        return dict(value)


__all__ = ["PolicyDefinition", "PolicyOverride", "PolicyParameter", "PolicyValueType"]
