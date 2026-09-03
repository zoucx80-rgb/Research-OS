from __future__ import annotations

from datetime import timezone

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from research_os.application.repositories import (
    SnapshotPage,
    SnapshotQuery,
    decode_snapshot_cursor,
    encode_snapshot_cursor,
)
from research_os.snapshots.codec import ArtifactDecoderRegistry, SnapshotCodecV2
from research_os.snapshots.models import ResearchSnapshotV2

from .mappers import snapshot_from_record, snapshot_to_record
from .schema import ArtifactIndexRecord, ResearchSnapshotRecord


class SqlSnapshotRepository:
    def __init__(
        self,
        session: Session,
        decoder_registry: ArtifactDecoderRegistry | None = None,
    ) -> None:
        self.session = session
        self._decoder_registry = decoder_registry

    def append(self, snapshot: ResearchSnapshotV2) -> None:
        snapshot.validate_artifact_bindings()
        self.session.add(snapshot_to_record(snapshot))
        for fingerprint in snapshot.artifact_fingerprints:
            producers = next(
                artifact.producer_ids
                for artifact in snapshot.payload.artifacts
                if artifact.artifact_id == fingerprint.artifact_id
                and artifact.schema_version == fingerprint.schema_version
                and artifact.type_id == fingerprint.type_id
            )
            for producer_id in producers:
                self.session.add(
                    ArtifactIndexRecord(
                        snapshot_id=snapshot.snapshot_id,
                        artifact_id=fingerprint.artifact_id,
                        schema_version=fingerprint.schema_version,
                        provider_id=producer_id,
                        fingerprint=fingerprint.value_fingerprint,
                    )
                )
        self.session.flush()

    def get(self, snapshot_id: str) -> ResearchSnapshotV2:
        record = self.session.get(ResearchSnapshotRecord, snapshot_id)
        if record is None:
            raise KeyError(snapshot_id)
        snapshot = snapshot_from_record(record, self._decoder_registry)
        codec = SnapshotCodecV2()
        research_digest = codec.research_digest(snapshot.payload)
        if record.research_digest != research_digest or snapshot.payload_hash != research_digest:
            raise ValueError("snapshot research payload digest mismatch")
        if record.integrity_digest != codec.integrity_digest(snapshot):
            raise ValueError("snapshot integrity digest mismatch")
        return snapshot

    def list_for_company(self, query: SnapshotQuery) -> SnapshotPage:
        statement: Select[tuple[ResearchSnapshotRecord]] = select(ResearchSnapshotRecord).where(
            ResearchSnapshotRecord.company_id == query.company_id,
            ResearchSnapshotRecord.schema_version == "2.0",
        )
        if query.decision_ts_lte is not None:
            statement = statement.where(ResearchSnapshotRecord.decision_ts <= query.decision_ts_lte)
        cursor = decode_snapshot_cursor(query.cursor) if query.cursor else None
        if cursor is not None:
            cursor_ts, cursor_id = cursor
            statement = statement.where(
                (ResearchSnapshotRecord.decision_ts < cursor_ts)
                | (
                    (ResearchSnapshotRecord.decision_ts == cursor_ts)
                    & (ResearchSnapshotRecord.snapshot_id < cursor_id)
                )
            )
        records = list(
            self.session.scalars(
                statement.order_by(
                    ResearchSnapshotRecord.decision_ts.desc(),
                    ResearchSnapshotRecord.snapshot_id.desc(),
                ).limit(query.limit + 1)
            )
        )
        has_next = len(records) > query.limit
        records = records[: query.limit]
        next_cursor = None
        if has_next and records:
            last = records[-1]
            decision_ts = last.decision_ts
            if decision_ts.tzinfo is None or decision_ts.utcoffset() is None:
                decision_ts = decision_ts.replace(tzinfo=timezone.utc)
            else:
                decision_ts = decision_ts.astimezone(timezone.utc)
            next_cursor = encode_snapshot_cursor(decision_ts, last.snapshot_id)
        return SnapshotPage(
            items=tuple(snapshot_from_record(record, self._decoder_registry) for record in records),
            next_cursor=next_cursor,
        )
