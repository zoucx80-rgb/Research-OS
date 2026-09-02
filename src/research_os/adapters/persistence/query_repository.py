"""SQL-backed projections for the read-only Research OS query service."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import cast

from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.orm import Session

from research_os.api.contracts import (
    ArtifactView,
    ResearchRunView,
    SnapshotPage,
    SnapshotQuery,
    SnapshotSummary,
    SnapshotView,
)
from research_os.api.errors import InvalidCursorError
from research_os.application.repositories import (
    SnapshotCursorError,
    SnapshotQuery as RepositorySnapshotQuery,
)
from research_os.snapshots.codec import ArtifactDecoderRegistry, SnapshotCodecV2
from research_os.snapshots.models import ResearchSnapshotV2

from .mappers import snapshot_from_record
from .schema import ResearchRunRecord, ResearchSnapshotRecord
from .snapshot_repository import SqlSnapshotRepository


def _json_value(codec: SnapshotCodecV2, value: object) -> JsonValue:
    decoded = codec.decode_value(codec.encode_value(value))
    return _json_compatible(codec, decoded)


def _json_compatible(codec: SnapshotCodecV2, value: object) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("query JSON mappings require string keys")
        return {
            key: _json_compatible(codec, item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_json_compatible(codec, item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [
            _json_compatible(codec, item)
            for item in sorted(value, key=codec.encode_value)
        ]
    raise TypeError(f"cannot project {type(value).__name__} as query JSON")


class SqlResearchQueryRepository:
    def __init__(
        self,
        session_factory: Callable[[], Session],
        decoder_registry: ArtifactDecoderRegistry | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._decoder_registry = decoder_registry
        self._codec = SnapshotCodecV2()

    def get_run(self, run_id: str) -> ResearchRunView | None:
        with self._session_factory() as session:
            run = session.get(ResearchRunRecord, run_id)
            snapshot_record = session.scalar(
                select(ResearchSnapshotRecord).where(
                    ResearchSnapshotRecord.run_id == run_id,
                    ResearchSnapshotRecord.schema_version == "2.0",
                )
            )
            if run is None or snapshot_record is None:
                return None
            snapshot = snapshot_from_record(snapshot_record, self._decoder_registry)
            completion = snapshot.payload.execution_completion
            readiness = snapshot.payload.research_readiness
            if completion is None or readiness is None:
                return None
            return ResearchRunView(
                run_id=run.run_id,
                company_id=run.company_id,
                decision_ts=snapshot.decision_ts,
                created_at=snapshot.created_at,
                execution_completion=completion.final_status,
                research_readiness=readiness.final_status,
                versions=snapshot.versions,
                snapshot_id=snapshot.snapshot_id,
            )

    def get_artifact(self, run_id: str, artifact_id: str) -> ArtifactView | None:
        with self._session_factory() as session:
            record = session.scalar(
                select(ResearchSnapshotRecord).where(
                    ResearchSnapshotRecord.run_id == run_id,
                    ResearchSnapshotRecord.schema_version == "2.0",
                )
            )
            if record is None:
                return None
            snapshot = snapshot_from_record(record, self._decoder_registry)
            artifact = next(
                (
                    item
                    for item in snapshot.payload.artifacts
                    if item.artifact_id == artifact_id
                ),
                None,
            )
            if artifact is None:
                return None
            return ArtifactView(
                run_id=run_id,
                artifact_id=artifact.artifact_id,
                schema_version=artifact.schema_version,
                producer_ids=artifact.producer_ids,
                evidence_refs=artifact.evidence_refs,
                value=_json_value(self._codec, artifact.payload),
            )

    def list_snapshots(self, query: SnapshotQuery) -> SnapshotPage:
        with self._session_factory() as session:
            repository = SqlSnapshotRepository(session, self._decoder_registry)
            try:
                page = repository.list_for_company(
                    RepositorySnapshotQuery(
                        company_id=query.company_id,
                        decision_ts_lte=query.decision_ts_lte,
                        limit=query.limit,
                        cursor=query.cursor,
                    )
                )
            except SnapshotCursorError as exc:
                raise InvalidCursorError() from exc
            return SnapshotPage(
                items=tuple(
                    SnapshotSummary.from_snapshot(self._snapshot_view(snapshot))
                    for snapshot in page.items
                ),
                next_cursor=page.next_cursor,
            )

    def get_snapshot(self, snapshot_id: str) -> SnapshotView | None:
        with self._session_factory() as session:
            record = session.get(ResearchSnapshotRecord, snapshot_id)
            if record is None or record.schema_version != "2.0":
                return None
            snapshot = snapshot_from_record(record, self._decoder_registry)
            return self._snapshot_view(snapshot)

    def _snapshot_view(self, snapshot: ResearchSnapshotV2) -> SnapshotView:
        return SnapshotView(
            snapshot_id=snapshot.snapshot_id,
            schema_version=snapshot.schema_version,
            codec_version=snapshot.codec_version,
            hash_algorithm=snapshot.hash_algorithm,
            run_id=snapshot.run_id,
            company_id=snapshot.company_id,
            decision_ts=snapshot.decision_ts,
            created_at=snapshot.created_at,
            research_digest=snapshot.payload_hash,
            integrity_digest=self._codec.integrity_digest(snapshot),
            payload=cast(dict[str, JsonValue], _json_value(self._codec, snapshot.payload)),
        )
