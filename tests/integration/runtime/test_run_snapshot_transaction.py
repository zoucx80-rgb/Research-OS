from __future__ import annotations

import subprocess
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from research_os.adapters.persistence.schema import (
    ArtifactIndexRecord,
    PersistenceBase,
    ResearchRunRecord,
    ResearchSnapshotRecord,
)
from research_os.adapters.persistence.unit_of_work import SqlUnitOfWork
from research_os.application import ResearchApplication, ResearchRunCommand
from research_os.application.bootstrap import RepositoryAttestation
from research_os.application.command import ResearchRunOptions
from research_os.contracts.errors import PersistenceError
from research_os.contracts.evidence import EvidenceSet
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
from research_os.period.models import ReportingPeriod
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.snapshots.service import SnapshotService


DECISION_TS = datetime(2026, 9, 2, tzinfo=timezone.utc)
COMPANY_ID = "synthetic:persistence"


def _head() -> str:
    return subprocess.check_output(("git", "rev-parse", "HEAD"), text=True).strip()


class _RepositoryAttestor:
    def attest(self) -> RepositoryAttestation:
        return RepositoryAttestation(
            repository_host="github.com",
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            head_sha=_head(),
        )


def _command() -> ResearchRunCommand:
    item = Evidence(
        evidence_id="ev:unmodeled",
        revision_no=1,
        company_id=COMPANY_ID,
        evidence_type="filing_fact",
        publish_ts=DECISION_TS,
        ingested_at=DECISION_TS,
        value={"nested": [1]},
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
    )
    evidence = EvidenceView((item,), company_id=COMPANY_ID, decision_ts=DECISION_TS)
    reference = evidence.refs()[0]
    return ResearchRunCommand(
        context=ResearchContext(
            run_id="run:persistence",
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
            evidence=evidence,
            facts=FactView(
                company_id=COMPANY_ID,
                decision_ts=DECISION_TS,
                values={"unmodeled_payload": item.value},
                evidence_refs_by_fact={"unmodeled_payload": (reference,)},
                reporting_period=ReportingPeriod(period_type="FY"),
                accounting_scope=AccountingScope(),
            ),
        )
    )


def test_application_atomically_persists_run_snapshot_and_artifact_index(tmp_path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'research.sqlite3'}")
    PersistenceBase.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    application = ResearchApplication.build(
        repository_attestor=_RepositoryAttestor(),
        unit_of_work_factory=lambda: SqlUnitOfWork(sessions),
    )

    result = application.run(_command())

    assert result.snapshot is not None
    with SqlUnitOfWork(sessions) as uow:
        stored_run = uow.runs.get(result.run_id)
        stored_snapshot = uow.snapshots.get(result.snapshot.snapshot_id)
    with sessions() as session:
        artifact_count = session.scalar(select(func.count()).select_from(ArtifactIndexRecord))
    assert stored_run.run_id == result.run_id
    assert stored_snapshot.run_id == result.run_id
    assert stored_snapshot.payload_hash == result.snapshot.research_digest
    assert artifact_count == len(stored_snapshot.artifact_fingerprints)
    preflight = next(
        artifact
        for artifact in stored_snapshot.payload.artifacts
        if artifact.artifact_id == "validation.repository_preflight"
    )
    assert isinstance(preflight.payload, BaselineFingerprint)
    pit = next(
        artifact
        for artifact in stored_snapshot.payload.artifacts
        if artifact.artifact_id == "evidence.pit"
    )
    assert isinstance(pit.payload, EvidenceSet)
    assert pit.payload.items[0].value == {"nested": [1]}


def test_persistence_toggle_does_not_change_research_semantic_digest() -> None:
    base_command = _command()
    no_persist = base_command.model_copy(
        update={"options": ResearchRunOptions(persist_snapshot=False)}
    )
    persist = base_command.model_copy(update={"options": ResearchRunOptions(persist_snapshot=True)})
    result = ResearchApplication.build(repository_attestor=_RepositoryAttestor()).run(no_persist)
    service = SnapshotService(
        snapshot_id_factory=lambda: "snapshot:semantic",
        clock=lambda: DECISION_TS,
    )

    no_persist_digest = service.build(command=no_persist, result=result).payload_hash
    persist_digest = service.build(command=persist, result=result).payload_hash

    assert no_persist_digest == persist_digest


def test_application_rolls_back_run_when_snapshot_append_fails(tmp_path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'rollback.sqlite3'}")
    PersistenceBase.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    application = ResearchApplication.build(
        repository_attestor=_RepositoryAttestor(),
        unit_of_work_factory=lambda: SqlUnitOfWork(sessions),
    )
    command = _command()

    first = application.run(command)
    assert first.snapshot is not None

    with pytest.raises(PersistenceError):
        application.run(command)

    with sessions() as session:
        run_count = session.scalar(select(func.count()).select_from(ResearchRunRecord))
        snapshot_count = session.scalar(select(func.count()).select_from(ResearchSnapshotRecord))
    assert run_count == 1
    assert snapshot_count == 1
