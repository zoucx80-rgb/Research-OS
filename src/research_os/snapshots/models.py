"""Frozen Snapshot Schema 2.0 value models."""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.application.result import (
    ComponentFingerprint,
    RunVersionSet,
)
from research_os.completion import ExecutionCompletionResult
from research_os.contracts.artifacts import artifact_value_fingerprint
from research_os.contracts.evidence import EvidenceRef
from research_os.readiness import ResearchReadinessAssessment
from research_os.runtime.context import BaselineFingerprint, CompanyRef


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("snapshot timestamps must be timezone-aware UTC")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError("snapshot timestamps must be UTC")
    return value


def _validate_immutable(value: object) -> None:
    """Reject mutable values before they can be retained by a frozen model."""
    if value is None or isinstance(value, (bool, int, str, bytes)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("snapshot values must be finite")
        return
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("snapshot values must be finite")
        return
    if isinstance(value, (datetime, date, Enum)):
        return
    if isinstance(value, BaseModel):
        if not value.model_config.get("frozen", False):
            raise ValueError("snapshot payload models must be immutable")
        return
    if isinstance(value, Mapping):
        if not isinstance(value, MappingProxyType):
            raise ValueError("snapshot payload mappings must be immutable")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("snapshot payload mappings require string keys")
            _validate_immutable(item)
        return
    if isinstance(value, tuple):
        for item in value:
            _validate_immutable(item)
        return
    if isinstance(value, frozenset):
        for item in value:
            _validate_immutable(item)
        return
    if isinstance(value, (list, set, bytearray, dict)):
        raise ValueError("snapshot payload values must be immutable")
    raise ValueError(f"snapshot payload cannot contain {type(value).__name__}")


def _copy_payload(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_copy(
            update={
                field_name: _copy_payload(getattr(value, field_name))
                for field_name in type(value).model_fields
            }
        )
    if isinstance(value, MappingProxyType):
        return MappingProxyType(
            {key: _copy_payload(item) for key, item in value.items()}
        )
    if isinstance(value, dict):
        return {key: _copy_payload(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_copy_payload(item) for item in value)
    if isinstance(value, list):
        return [_copy_payload(item) for item in value]
    if isinstance(value, frozenset):
        return frozenset(_copy_payload(item) for item in value)
    if isinstance(value, set):
        return {_copy_payload(item) for item in value}
    return copy.deepcopy(value)


class _FrozenSnapshotModel(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True, extra="forbid")


class ArtifactFingerprint(_FrozenSnapshotModel):
    artifact_id: str
    schema_version: str
    type_id: str
    value_fingerprint: str

    @field_validator("artifact_id", "schema_version", "type_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("artifact fingerprint identity fields must be non-empty")
        return value

    @field_validator("value_fingerprint")
    @classmethod
    def _sha256(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("value_fingerprint must be lowercase SHA-256 hex")
        return value


class SnapshotArtifactV2(_FrozenSnapshotModel):
    artifact_id: str
    schema_version: str
    type_id: str
    producer_ids: tuple[str, ...] = Field(min_length=1)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    payload: object

    @field_validator("artifact_id", "schema_version", "type_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("artifact schema identity fields must be non-empty")
        return value

    @field_validator("producer_ids")
    @classmethod
    def _producer_ids(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not producer_id.strip() for producer_id in value):
            raise ValueError("artifact producer IDs must be non-empty")
        return tuple(sorted(set(value)))

    @field_validator("payload")
    @classmethod
    def _immutable_payload(cls, value: object) -> object:
        _validate_immutable(value)
        return value

    def model_post_init(self, __context: object) -> None:
        object.__setattr__(
            self,
            "payload",
            _copy_payload(object.__getattribute__(self, "payload")),
        )

    def __getattribute__(self, name: str) -> object:
        value = super().__getattribute__(name)
        if name == "payload":
            return _copy_payload(value)
        return value


class ResearchSnapshotPayloadV2(_FrozenSnapshotModel):
    """The run-independent semantic projection used for the research digest."""

    company: CompanyRef
    decision_ts: datetime
    baseline: BaselineFingerprint
    versions: RunVersionSet
    component_fingerprints: tuple[ComponentFingerprint, ...] = Field(default_factory=tuple)
    artifacts: tuple[SnapshotArtifactV2, ...] = Field(default_factory=tuple)
    input_assumptions: tuple[object, ...] = Field(default_factory=tuple)
    execution_completion: ExecutionCompletionResult | None = None
    research_readiness: ResearchReadinessAssessment | None = None

    @field_validator("decision_ts")
    @classmethod
    def _utc_decision_ts(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @field_validator("input_assumptions")
    @classmethod
    def _immutable_assumptions(cls, value: tuple[object, ...]) -> tuple[object, ...]:
        for item in value:
            _validate_immutable(item)
        return value

    @field_validator("artifacts")
    @classmethod
    def _unique_artifacts(
        cls, value: tuple[SnapshotArtifactV2, ...]
    ) -> tuple[SnapshotArtifactV2, ...]:
        identities = [
            (item.artifact_id, item.schema_version, item.type_id) for item in value
        ]
        if len(identities) != len(set(identities)):
            raise ValueError("snapshot artifacts must have unique schema identities")
        return value

    @field_validator("execution_completion", "research_readiness")
    @classmethod
    def _immutable_models(
        cls,
        value: ExecutionCompletionResult | ResearchReadinessAssessment | None,
    ) -> ExecutionCompletionResult | ResearchReadinessAssessment | None:
        if value is not None:
            _validate_immutable(value)
        return value

    def model_post_init(self, __context: object) -> None:
        object.__setattr__(
            self,
            "input_assumptions",
            tuple(
                _copy_payload(item)
                for item in object.__getattribute__(self, "input_assumptions")
            ),
        )

    def __getattribute__(self, name: str) -> object:
        value = super().__getattribute__(name)
        if name == "input_assumptions":
            return tuple(_copy_payload(item) for item in value)
        return value


class ResearchSnapshotV2(_FrozenSnapshotModel):
    snapshot_id: str
    schema_version: Literal["2.0"]
    codec_version: Literal["jcs-1"]
    hash_algorithm: Literal["sha256"]
    run_id: str
    company_id: str
    decision_ts: datetime
    created_at: datetime
    baseline: BaselineFingerprint
    versions: RunVersionSet
    component_fingerprints: tuple[ComponentFingerprint, ...]
    artifact_fingerprints: tuple[ArtifactFingerprint, ...]
    payload: ResearchSnapshotPayloadV2
    payload_hash: str

    @field_validator("snapshot_id", "codec_version", "run_id", "company_id")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("snapshot identity fields must be non-empty")
        return value

    @field_validator("decision_ts", "created_at")
    @classmethod
    def _utc_timestamps(cls, value: datetime) -> datetime:
        return _require_utc(value)

    @field_validator("payload_hash")
    @classmethod
    def _payload_hash(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("payload_hash must be lowercase SHA-256 hex")
        return value

    @model_validator(mode="after")
    def _bind_envelope_to_projection(self) -> ResearchSnapshotV2:
        if self.company_id != self.payload.company.company_id:
            raise ValueError("snapshot company_id must match semantic payload")
        if self.decision_ts != self.payload.decision_ts:
            raise ValueError("snapshot decision_ts must match semantic payload")
        if self.baseline != self.payload.baseline:
            raise ValueError("snapshot baseline must match semantic payload")
        if self.versions != self.payload.versions:
            raise ValueError("snapshot versions must match semantic payload")
        if self.component_fingerprints != self.payload.component_fingerprints:
            raise ValueError("snapshot component fingerprints must match semantic payload")
        self.validate_artifact_bindings()
        return self

    def validate_artifact_bindings(self) -> None:
        fingerprint_by_identity = {
            (item.artifact_id, item.schema_version, item.type_id): item
            for item in self.artifact_fingerprints
        }
        if len(fingerprint_by_identity) != len(self.artifact_fingerprints):
            raise ValueError("snapshot artifact fingerprints must be unique")
        artifact_by_identity = {
            (item.artifact_id, item.schema_version, item.type_id): item
            for item in self.payload.artifacts
        }
        if set(fingerprint_by_identity) != set(artifact_by_identity):
            raise ValueError(
                "snapshot artifacts and fingerprints must form a one-to-one set"
            )
        for identity, artifact in artifact_by_identity.items():
            if (
                fingerprint_by_identity[identity].value_fingerprint
                != artifact_value_fingerprint(artifact.payload)
            ):
                raise ValueError("snapshot artifact fingerprint does not match its value")
