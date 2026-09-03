"""Application-owned persistence ports and immutable query values."""

from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from research_os.application.result import RunVersionSet
from research_os.contracts.evidence import EvidenceSet
from research_os.domain.evidence import Evidence
from research_os.runtime.context import BaselineFingerprint
from research_os.snapshots.models import ResearchSnapshotV2


class SnapshotQuery(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_id: str
    decision_ts_lte: datetime | None = None
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = None


class SnapshotPage(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    items: tuple[ResearchSnapshotV2, ...]
    next_cursor: str | None = None


class SnapshotCursorError(ValueError):
    """Raised only when a repository pagination cursor cannot be decoded."""


def encode_snapshot_cursor(decision_ts: datetime, snapshot_id: str) -> str:
    value = f"{decision_ts.isoformat()}|{snapshot_id}".encode("utf-8")
    return base64.urlsafe_b64encode(value).decode("ascii")


def decode_snapshot_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        value = base64.b64decode(cursor.encode("ascii"), altchars=b"-_", validate=True).decode(
            "utf-8"
        )
        timestamp, snapshot_id = value.rsplit("|", 1)
        decision_ts = datetime.fromisoformat(timestamp)
        if (
            decision_ts.tzinfo is None
            or decision_ts.utcoffset() is None
            or decision_ts.utcoffset() != timezone.utc.utcoffset(decision_ts)
            or not snapshot_id
        ):
            raise ValueError("cursor content is incomplete")
        return decision_ts, snapshot_id
    except (
        binascii.Error,
        UnicodeDecodeError,
        UnicodeEncodeError,
        ValueError,
    ) as exc:
        raise SnapshotCursorError("invalid snapshot cursor") from exc


class ResearchRun(BaseModel):
    """The durable run envelope; semantic detail belongs in its snapshot."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    company_id: str
    decision_ts: datetime
    created_at: datetime
    baseline: BaselineFingerprint
    versions: RunVersionSet
    payload_json: str


class EvidenceRepository(Protocol):
    def append(self, evidence: Evidence) -> None: ...

    def latest_as_of(self, company_id: str, decision_ts: datetime) -> EvidenceSet: ...


class ResearchRunRepository(Protocol):
    def append(self, run: ResearchRun) -> None: ...

    def get(self, run_id: str) -> ResearchRun: ...


class SnapshotRepository(Protocol):
    def append(self, snapshot: ResearchSnapshotV2) -> None: ...

    def get(self, snapshot_id: str) -> ResearchSnapshotV2: ...

    def list_for_company(self, query: SnapshotQuery) -> SnapshotPage: ...


class UnitOfWork(Protocol):
    evidence: EvidenceRepository
    runs: ResearchRunRepository
    snapshots: SnapshotRepository

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
