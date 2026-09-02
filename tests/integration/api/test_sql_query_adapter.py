from __future__ import annotations

import subprocess
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker

from research_os.adapters.persistence.query_repository import SqlResearchQueryRepository
from research_os.adapters.persistence.schema import PersistenceBase, ResearchSnapshotRecord
from research_os.api.contracts import SnapshotQuery
from research_os.api.errors import InvalidCursorError
from research_os.adapters.persistence.unit_of_work import SqlUnitOfWork
from research_os.api.app import create_app
from research_os.api.query import ResearchQueryService, SnapshotResearchViewProjector
from research_os.application import ResearchApplication, ResearchRunCommand
from research_os.application.bootstrap import RepositoryAttestation
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)


DECISION_TS = datetime(2026, 9, 2, tzinfo=timezone.utc)
COMPANY_ID = "synthetic:http-persistence"


def _head() -> str:
    return subprocess.check_output(("git", "rev-parse", "HEAD"), text=True).strip()


class _Attestor:
    def attest(self) -> RepositoryAttestation:
        return RepositoryAttestation(
            repository_host="github.com",
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            head_sha=_head(),
        )


def _command() -> ResearchRunCommand:
    return ResearchRunCommand(
        context=ResearchContext(
            run_id="run:http-persistence",
            company=CompanyRef(company_id=COMPANY_ID),
            decision_ts=DECISION_TS,
            baseline=BaselineFingerprint(
                repository_full_name="zoucx80-rgb/Research-OS",
                repository_id=1350382205,
                branch="main",
                commit_sha=_head(),
                research_os_version="1.6.0",
                core_api_version="2.0",
            ),
            evidence=EvidenceView(
                (), company_id=COMPANY_ID, decision_ts=DECISION_TS
            ),
            facts=FactView(
                company_id=COMPANY_ID,
                decision_ts=DECISION_TS,
                values={},
                evidence_refs_by_fact={},
                reporting_period=ReportingPeriod(period_type="FY"),
                accounting_scope=AccountingScope(),
            ),
        )
    )


def test_sql_query_adapter_serves_persisted_run_snapshot_and_artifact(tmp_path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'api.sqlite3'}")
    PersistenceBase.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    result = ResearchApplication.build(
        repository_attestor=_Attestor(),
        unit_of_work_factory=lambda: SqlUnitOfWork(sessions),
    ).run(_command())
    assert result.snapshot is not None
    query = ResearchQueryService(
        SqlResearchQueryRepository(sessions),
        SnapshotResearchViewProjector(),
    )
    client = TestClient(create_app(query))

    run_response = client.get(f"/api/v1/research-runs/{result.run_id}")
    artifact_response = client.get(
        f"/api/v1/research-runs/{result.run_id}/artifacts/validation.repository_preflight"
    )
    list_response = client.get(f"/api/v1/companies/{COMPANY_ID}/snapshots")
    snapshot_response = client.get(
        f"/api/v1/snapshots/{result.snapshot.snapshot_id}"
    )
    research_view_response = client.get(
        f"/api/v1/snapshots/{result.snapshot.snapshot_id}/research-view"
    )

    assert [
        run_response.status_code,
        artifact_response.status_code,
        list_response.status_code,
        snapshot_response.status_code,
        research_view_response.status_code,
    ] == [200, 200, 200, 200, 200]
    assert run_response.json()["snapshot_id"] == result.snapshot.snapshot_id
    assert artifact_response.json()["producer_ids"] == ["core:repository-preflight"]
    assert artifact_response.json()["value"]["repository_full_name"] == (
        "zoucx80-rgb/Research-OS"
    )
    assert "$ros_type" not in artifact_response.json()["value"]
    assert list_response.json()["items"][0]["research_digest"] == result.snapshot.research_digest
    assert snapshot_response.json()["integrity_digest"] == result.snapshot.integrity_digest
    assert snapshot_response.json()["payload"]["company"]["company_id"] == COMPANY_ID
    assert "$ros_type" not in snapshot_response.json()["payload"]
    assert research_view_response.json()["snapshot_id"] == result.snapshot.snapshot_id

    invalid_cursor = client.get(
        f"/api/v1/companies/{COMPANY_ID}/snapshots", params={"cursor": "x"}
    )
    assert invalid_cursor.status_code == 400
    assert invalid_cursor.json()["type"] == "urn:research-os:error:invalid-cursor"


def test_sql_query_adapter_does_not_misclassify_snapshot_tampering_as_cursor_error(
    tmp_path,
) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'tampered-api.sqlite3'}")
    PersistenceBase.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    result = ResearchApplication.build(
        repository_attestor=_Attestor(),
        unit_of_work_factory=lambda: SqlUnitOfWork(sessions),
    ).run(_command())
    assert result.snapshot is not None

    with sessions.begin() as session:
        session.execute(
            update(ResearchSnapshotRecord)
            .where(ResearchSnapshotRecord.snapshot_id == result.snapshot.snapshot_id)
            .values(payload_json="{}")
        )

    repository = SqlResearchQueryRepository(sessions)
    with pytest.raises(ValueError) as caught:
        repository.list_snapshots(
            SnapshotQuery(company_id=COMPANY_ID)
        )
    assert not isinstance(caught.value, InvalidCursorError)
