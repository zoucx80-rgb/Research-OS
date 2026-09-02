from __future__ import annotations

from datetime import datetime, timezone
from types import MappingProxyType

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from research_os.adapters.persistence.schema import PersistenceBase
from research_os.adapters.persistence.unit_of_work import SqlUnitOfWork
from research_os.application.repositories import ResearchRun
from research_os.application.result import RunVersionSet
from research_os.contracts.artifacts import artifact_value_fingerprint
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.snapshots.codec import SnapshotCodecV2
from research_os.snapshots.models import (
    ArtifactFingerprint,
    ResearchSnapshotPayloadV2,
    ResearchSnapshotV2,
    SnapshotArtifactV2,
)


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


def _run(run_id: str) -> ResearchRun:
    return ResearchRun(
        run_id=run_id,
        company_id="000001.SZ",
        decision_ts=datetime(2026, 9, 1, tzinfo=timezone.utc),
        created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
        baseline=_baseline(),
        versions=_versions(),
        payload_json="{}",
    )


def _snapshot(snapshot_id: str, run_id: str) -> ResearchSnapshotV2:
    decision_ts = datetime(2026, 9, 1, tzinfo=timezone.utc)
    payload = ResearchSnapshotPayloadV2(
        company=CompanyRef(company_id="000001.SZ"),
        decision_ts=decision_ts,
        baseline=_baseline(),
        versions=_versions(),
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
        run_id=run_id,
        company_id="000001.SZ",
        decision_ts=decision_ts,
        created_at=decision_ts,
        baseline=_baseline(),
        versions=_versions(),
        component_fingerprints=(),
        artifact_fingerprints=(
            ArtifactFingerprint(
                artifact_id="decision.record",
                schema_version="2.0",
                type_id="decision-record-v2",
                value_fingerprint=artifact_value_fingerprint(
                    payload.artifacts[0].payload
                ),
            ),
        ),
        payload=payload,
        payload_hash=SnapshotCodecV2().research_digest(payload),
    )


def test_unit_of_work_rolls_back_snapshot_when_run_append_fails() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    PersistenceBase.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    with SqlUnitOfWork(sessions) as uow:
        uow.runs.append(_run("run-duplicate"))
        uow.commit()

    with pytest.raises(IntegrityError):
        with SqlUnitOfWork(sessions) as uow:
            uow.snapshots.append(_snapshot("snapshot-rolled-back", "run-duplicate"))
            uow.runs.append(_run("run-duplicate"))
            uow.commit()

    with SqlUnitOfWork(sessions) as uow:
        assert uow.runs.get("run-duplicate").run_id == "run-duplicate"
        with pytest.raises(KeyError):
            uow.snapshots.get("snapshot-rolled-back")
