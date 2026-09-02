"""Test-only immutable in-memory implementations of application ports."""

from __future__ import annotations

from datetime import datetime

from research_os.application.repositories import (
    ResearchRun,
    SnapshotPage,
    SnapshotQuery,
    decode_snapshot_cursor,
    encode_snapshot_cursor,
)
from research_os.contracts.evidence import EvidenceRef, EvidenceSet, evidence_content_fingerprint
from research_os.domain.evidence import Evidence
from research_os.snapshots.models import ResearchSnapshotV2


class InMemorySnapshotRepository:
    """A test adapter. Production code must use a durable repository."""

    def __init__(self) -> None:
        self._snapshots: dict[str, ResearchSnapshotV2] = {}

    def append(self, snapshot: ResearchSnapshotV2) -> None:
        if snapshot.snapshot_id in self._snapshots:
            raise ValueError(f"snapshot already exists: {snapshot.snapshot_id}")
        self._snapshots[snapshot.snapshot_id] = snapshot

    def get(self, snapshot_id: str) -> ResearchSnapshotV2:
        return self._snapshots[snapshot_id]

    def list_for_company(self, query: SnapshotQuery) -> SnapshotPage:
        snapshots = tuple(
            snapshot
            for snapshot in sorted(
                self._snapshots.values(),
                key=lambda item: (item.decision_ts, item.snapshot_id),
                reverse=True,
            )
            if snapshot.company_id == query.company_id
            and (
                query.decision_ts_lte is None
                or snapshot.decision_ts <= query.decision_ts_lte
            )
        )
        cursor = decode_snapshot_cursor(query.cursor) if query.cursor else None
        if cursor is not None:
            cursor_ts, cursor_id = cursor
            snapshots = tuple(
                snapshot
                for snapshot in snapshots
                if (snapshot.decision_ts, snapshot.snapshot_id)
                < (cursor_ts, cursor_id)
            )
        page_items = snapshots[: query.limit]
        next_cursor = None
        if len(snapshots) > query.limit and page_items:
            last = page_items[-1]
            next_cursor = encode_snapshot_cursor(last.decision_ts, last.snapshot_id)
        return SnapshotPage(items=page_items, next_cursor=next_cursor)


class InMemoryResearchRunRepository:
    """A test adapter that enforces append-only run identities."""

    def __init__(self) -> None:
        self._runs: dict[str, ResearchRun] = {}

    def append(self, run: ResearchRun) -> None:
        if run.run_id in self._runs:
            raise ValueError(f"run already exists: {run.run_id}")
        self._runs[run.run_id] = run

    def get(self, run_id: str) -> ResearchRun:
        return self._runs[run_id]


class InMemoryEvidenceRepository:
    """A test adapter whose selection semantics mirror the SQL port."""

    def __init__(self) -> None:
        self._evidence: dict[tuple[str, int], Evidence] = {}

    def append(self, evidence: Evidence) -> None:
        key = evidence.evidence_id, evidence.revision_no
        if key in self._evidence:
            raise ValueError(
                f"evidence revision already exists: {evidence.evidence_id}@{evidence.revision_no}"
            )
        self._evidence[key] = evidence.model_copy(deep=True)

    def latest_as_of(self, company_id: str, decision_ts: datetime) -> EvidenceSet:
        latest: dict[str, Evidence] = {}
        for evidence in self._evidence.values():
            if evidence.company_id != company_id or evidence.publish_ts > decision_ts:
                continue
            current = latest.get(evidence.evidence_id)
            if current is None or (evidence.publish_ts, evidence.revision_no) > (
                current.publish_ts,
                current.revision_no,
            ):
                latest[evidence.evidence_id] = evidence
        items = tuple(
            item.model_copy(deep=True)
            for _, item in sorted(latest.items(), key=lambda entry: entry[0])
        )
        return EvidenceSet(
            items=items,
            evidence_refs=tuple(
                EvidenceRef(
                    evidence_id=item.evidence_id,
                    revision=item.revision_no,
                    content_fingerprint=evidence_content_fingerprint(item),
                )
                for item in items
            ),
        )
