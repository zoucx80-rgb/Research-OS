from __future__ import annotations

from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from research_os.adapters.persistence.schema import PersistenceBase
from research_os.adapters.persistence.snapshot_repository import SqlSnapshotRepository
from research_os.application.repositories import SnapshotCursorError, SnapshotQuery
from research_os.application.result import RunVersionSet
from research_os.contracts.artifacts import artifact_value_fingerprint
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.snapshots.codec import ArtifactDecoderRegistry, SnapshotCodecV2
from research_os.snapshots.models import (
    ArtifactFingerprint,
    ResearchSnapshotPayloadV2,
    ResearchSnapshotV2,
    SnapshotArtifactV2,
)
from research_os.snapshots.repository import InMemorySnapshotRepository


def _repository(backend: str, tmp_path) -> Any:
    if backend == "memory":
        return InMemorySnapshotRepository()
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'contract.sqlite3'}")
    PersistenceBase.metadata.create_all(engine)
    registry = ArtifactDecoderRegistry()
    registry.register(
        artifact_id="decision.record",
        schema_version="2.0",
        type_id="decision-record-v2",
        decoder=lambda value: MappingProxyType(dict(value)),
    )
    return SqlSnapshotRepository(sessionmaker(engine)(), registry)


def _baseline() -> BaselineFingerprint:
    return BaselineFingerprint(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        commit_sha="a" * 40,
        research_os_version="1.6.0",
        core_api_version="2.0",
    )


def _versions() -> RunVersionSet:
    return RunVersionSet(
        research_os_version="1.6.0",
        core_api_version="2.0",
        plugin_api_version="2.0",
        snapshot_schema_version="2.0",
        http_api_version="v1",
    )


def _snapshot(snapshot_id: str, decision_ts: datetime) -> ResearchSnapshotV2:
    baseline = _baseline()
    versions = _versions()
    payload = ResearchSnapshotPayloadV2(
        company=CompanyRef(company_id="000001.SZ"),
        decision_ts=decision_ts,
        baseline=baseline,
        versions=versions,
        component_fingerprints=(),
        artifacts=(
            SnapshotArtifactV2(
                artifact_id="decision.record",
                schema_version="2.0",
                type_id="decision-record-v2",
                producer_ids=("decision",),
                payload=MappingProxyType({"state": "WAIT"}),
            ),
        ),
    )
    return ResearchSnapshotV2(
        snapshot_id=snapshot_id,
        schema_version="2.0",
        codec_version="jcs-1",
        hash_algorithm="sha256",
        run_id=f"run-{snapshot_id}",
        company_id="000001.SZ",
        decision_ts=decision_ts,
        created_at=decision_ts,
        baseline=baseline,
        versions=versions,
        component_fingerprints=(),
        artifact_fingerprints=(
            ArtifactFingerprint(
                artifact_id="decision.record",
                schema_version="2.0",
                type_id="decision-record-v2",
                value_fingerprint=artifact_value_fingerprint(payload.artifacts[0].payload),
            ),
        ),
        payload=payload,
        payload_hash=SnapshotCodecV2().research_digest(payload),
    )


def test_in_memory_snapshot_repository_is_append_only_and_returns_immutable_values() -> None:
    repository = InMemorySnapshotRepository()
    snapshot = _snapshot("snapshot-1", datetime(2026, 9, 1, tzinfo=timezone.utc))
    repository.append(snapshot)

    restored = repository.get("snapshot-1")

    assert restored == snapshot
    with pytest.raises(ValueError, match="already exists"):
        repository.append(snapshot)
    with pytest.raises(TypeError):
        restored.payload.artifacts[0].payload["state"] = "BUY"  # type: ignore[index]


@pytest.mark.parametrize("backend", ("memory", "sql"))
def test_snapshot_repository_lists_company_snapshots_as_of_cutoff(backend: str, tmp_path) -> None:
    repository = _repository(backend, tmp_path)
    early = _snapshot("snapshot-early", datetime(2026, 9, 1, tzinfo=timezone.utc))
    late = _snapshot("snapshot-late", datetime(2026, 9, 2, tzinfo=timezone.utc))
    repository.append(late)
    repository.append(early)

    page = repository.list_for_company(
        SnapshotQuery(
            company_id="000001.SZ",
            decision_ts_lte=datetime(2026, 9, 1, 23, 59, tzinfo=timezone.utc),
            limit=10,
        )
    )

    assert page.items == (early,)
    assert page.next_cursor is None


@pytest.mark.parametrize("backend", ("memory", "sql"))
def test_snapshot_repository_paginates_with_stable_opaque_cursor(backend: str, tmp_path) -> None:
    repository = _repository(backend, tmp_path)
    timestamp = datetime(2026, 9, 1, tzinfo=timezone.utc)
    snapshots = tuple(_snapshot(f"snapshot-{index}", timestamp) for index in range(3))
    for snapshot in snapshots:
        repository.append(snapshot)

    first = repository.list_for_company(SnapshotQuery(company_id="000001.SZ", limit=2))
    second = repository.list_for_company(
        SnapshotQuery(
            company_id="000001.SZ",
            limit=2,
            cursor=first.next_cursor,
        )
    )

    assert [item.snapshot_id for item in first.items] == ["snapshot-2", "snapshot-1"]
    assert first.next_cursor is not None
    assert [item.snapshot_id for item in second.items] == ["snapshot-0"]
    assert second.next_cursor is None
    with pytest.raises(SnapshotCursorError):
        repository.list_for_company(SnapshotQuery(company_id="000001.SZ", cursor="eA=="))
