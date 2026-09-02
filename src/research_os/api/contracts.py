"""Typed HTTP/query projections for the read-only API v1."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

from research_os.application.result import RunVersionSet
from research_os.contracts.evidence import EvidenceRef


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_CURSOR = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("query timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


class _ReadModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ResearchRunView(_ReadModel):
    run_id: str
    company_id: str
    decision_ts: datetime
    created_at: datetime
    execution_completion: Literal["COMPLETE", "INCOMPLETE"]
    research_readiness: Literal["READY", "NOT_READY"]
    versions: RunVersionSet
    snapshot_id: str | None = None

    @field_validator("decision_ts", "created_at")
    @classmethod
    def _timestamps(cls, value: datetime) -> datetime:
        return _utc(value)


class ArtifactView(_ReadModel):
    run_id: str
    artifact_id: str
    schema_version: str
    producer_ids: tuple[str, ...] = Field(min_length=1)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    value: JsonValue

    @field_validator("producer_ids")
    @classmethod
    def _canonical_producers(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("artifact producer IDs must be non-empty")
        return tuple(sorted(set(values)))


class SnapshotView(_ReadModel):
    snapshot_id: str
    schema_version: Literal["2.0"]
    codec_version: str
    hash_algorithm: Literal["sha256"]
    run_id: str
    company_id: str
    decision_ts: datetime
    created_at: datetime
    research_digest: str
    integrity_digest: str
    payload: dict[str, JsonValue]

    @field_validator("decision_ts", "created_at")
    @classmethod
    def _timestamps(cls, value: datetime) -> datetime:
        return _utc(value)

    @field_validator("research_digest", "integrity_digest")
    @classmethod
    def _digests(cls, value: str) -> str:
        if not _DIGEST.fullmatch(value):
            raise ValueError("snapshot digest must be lowercase SHA-256 hex")
        return value


class SnapshotSummary(_ReadModel):
    snapshot_id: str
    run_id: str
    company_id: str
    decision_ts: datetime
    created_at: datetime
    research_digest: str
    integrity_digest: str

    @classmethod
    def from_snapshot(cls, snapshot: SnapshotView) -> Self:
        return cls(
            snapshot_id=snapshot.snapshot_id,
            run_id=snapshot.run_id,
            company_id=snapshot.company_id,
            decision_ts=snapshot.decision_ts,
            created_at=snapshot.created_at,
            research_digest=snapshot.research_digest,
            integrity_digest=snapshot.integrity_digest,
        )

    @field_validator("decision_ts", "created_at")
    @classmethod
    def _timestamps(cls, value: datetime) -> datetime:
        return _utc(value)

    @field_validator("research_digest", "integrity_digest")
    @classmethod
    def _digests(cls, value: str) -> str:
        if not _DIGEST.fullmatch(value):
            raise ValueError("snapshot digest must be lowercase SHA-256 hex")
        return value


class SnapshotQuery(_ReadModel):
    company_id: str
    decision_ts_lte: datetime | None = None
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = None

    @field_validator("company_id")
    @classmethod
    def _company_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("company_id must be non-empty")
        return value

    @field_validator("decision_ts_lte")
    @classmethod
    def _decision_ts_lte(cls, value: datetime | None) -> datetime | None:
        return None if value is None else _utc(value)

    @field_validator("cursor")
    @classmethod
    def _cursor(cls, value: str | None) -> str | None:
        if value is not None and (
            len(value) > 512 or not _OPAQUE_CURSOR.fullmatch(value)
        ):
            raise ValueError("cursor must be an opaque base64url token")
        return value


class SnapshotPage(_ReadModel):
    items: tuple[SnapshotSummary, ...] = Field(default_factory=tuple)
    next_cursor: str | None = None

    @field_validator("next_cursor")
    @classmethod
    def _cursor(cls, value: str | None) -> str | None:
        if value is not None and (
            len(value) > 512 or not _OPAQUE_CURSOR.fullmatch(value)
        ):
            raise ValueError("next_cursor must be an opaque base64url token")
        return value


class HumanReadableResearchView(_ReadModel):
    snapshot_id: str
    company_id: str
    decision_ts: datetime
    presentation_version: str
    content: dict[str, JsonValue]

    @field_validator("decision_ts")
    @classmethod
    def _decision_ts(cls, value: datetime) -> datetime:
        return _utc(value)


class HealthView(_ReadModel):
    status: Literal["ok"] = "ok"
    http_api_version: Literal["v1"] = "v1"


class ProblemDetails(_ReadModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    request_id: str
