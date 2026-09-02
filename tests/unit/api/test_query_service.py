from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from research_os.api.contracts import (
    ArtifactView,
    HumanReadableResearchView,
    ResearchRunView,
    SnapshotPage,
    SnapshotQuery,
    SnapshotSummary,
    SnapshotView,
)
from research_os.api.errors import (
    ArtifactNotFoundError,
    QueryContractError,
    RunNotFoundError,
    SnapshotNotFoundError,
)
from research_os.api.query import ResearchQueryService
from research_os.application.result import RunVersionSet
from research_os.contracts.evidence import EvidenceRef


DECISION_TS = datetime(2026, 8, 29, tzinfo=timezone.utc)
CREATED_AT = datetime(2026, 8, 30, tzinfo=timezone.utc)


def _versions() -> RunVersionSet:
    return RunVersionSet(
        research_os_version="1.6.0",
        core_api_version="2.0",
        plugin_api_version="2.0",
        snapshot_schema_version="2.0",
        http_api_version="v1",
    )


def _run() -> ResearchRunView:
    return ResearchRunView(
        run_id="run-1",
        company_id="company-1",
        decision_ts=DECISION_TS,
        created_at=CREATED_AT,
        execution_completion="COMPLETE",
        research_readiness="READY",
        versions=_versions(),
        snapshot_id="snapshot-1",
    )


def _artifact() -> ArtifactView:
    return ArtifactView(
        run_id="run-1",
        artifact_id="valuation.summary",
        schema_version="2.0",
        producer_ids=("methodology:valuation",),
        evidence_refs=(
            EvidenceRef(
                evidence_id="evidence-1",
                revision=2,
                content_fingerprint="a" * 64,
            ),
        ),
        value={"status": "SUPPORTED"},
    )


def _snapshot(*, decision_ts: datetime = DECISION_TS) -> SnapshotView:
    return SnapshotView(
        snapshot_id="snapshot-1",
        schema_version="2.0",
        codec_version="jcs-1",
        hash_algorithm="sha256",
        run_id="run-1",
        company_id="company-1",
        decision_ts=decision_ts,
        created_at=CREATED_AT,
        research_digest="b" * 64,
        integrity_digest="c" * 64,
        payload={"result": "ready"},
    )


class _Repository:
    def __init__(self) -> None:
        self.run: ResearchRunView | None = _run()
        self.artifact: ArtifactView | None = _artifact()
        self.snapshot: SnapshotView | None = _snapshot()
        self.page = SnapshotPage(
            items=(SnapshotSummary.from_snapshot(_snapshot()),),
            next_cursor="next_page",
        )
        self.last_query: SnapshotQuery | None = None

    def get_run(self, run_id: str) -> ResearchRunView | None:
        return self.run if run_id == "run-1" else None

    def get_artifact(self, run_id: str, artifact_id: str) -> ArtifactView | None:
        if (run_id, artifact_id) == ("run-1", "valuation.summary"):
            return self.artifact
        return None

    def list_snapshots(self, query: SnapshotQuery) -> SnapshotPage:
        self.last_query = query
        return self.page

    def get_snapshot(self, snapshot_id: str) -> SnapshotView | None:
        return self.snapshot if snapshot_id == "snapshot-1" else None


class _Projector:
    def __init__(self) -> None:
        self.snapshot: SnapshotView | None = None

    def project(self, snapshot: SnapshotView) -> HumanReadableResearchView:
        self.snapshot = snapshot
        return HumanReadableResearchView(
            snapshot_id=snapshot.snapshot_id,
            company_id=snapshot.company_id,
            decision_ts=snapshot.decision_ts,
            presentation_version="research-view@2",
            content={"summary": "ready"},
        )


def _service() -> tuple[ResearchQueryService, _Repository, _Projector]:
    repository = _Repository()
    projector = _Projector()
    return ResearchQueryService(repository, projector), repository, projector


def test_query_service_returns_artifact_schema_provider_and_revision_lineage() -> None:
    service, _, _ = _service()

    artifact = service.get_artifact("run-1", "valuation.summary")

    assert artifact.schema_version == "2.0"
    assert artifact.producer_ids == ("methodology:valuation",)
    assert artifact.evidence_refs[0].revision == 2


@pytest.mark.parametrize(
    ("operation", "error_type"),
    [
        (lambda service: service.get_run("missing"), RunNotFoundError),
        (
            lambda service: service.get_artifact("run-1", "missing"),
            ArtifactNotFoundError,
        ),
        (lambda service: service.get_snapshot("missing"), SnapshotNotFoundError),
        (lambda service: service.get_research_view("missing"), SnapshotNotFoundError),
    ],
)
def test_query_service_raises_typed_not_found_errors(operation, error_type) -> None:
    service, _, _ = _service()

    with pytest.raises(error_type):
        operation(service)


def test_snapshot_query_rejects_invalid_cursor_and_excessive_limit() -> None:
    with pytest.raises(ValidationError, match="cursor"):
        SnapshotQuery(company_id="company-1", cursor="not an opaque cursor")
    with pytest.raises(ValidationError, match="limit"):
        SnapshotQuery(company_id="company-1", limit=101)


def test_snapshot_query_accepts_padded_base64url_cursor_from_sql_adapter() -> None:
    cursor = "MjAyNi0wOS0wMlQwMDowMDowMCswMDowMHxhYg=="

    query = SnapshotQuery(company_id="company-1", cursor=cursor)
    page = SnapshotPage(next_cursor=cursor)

    assert query.cursor == cursor
    assert page.next_cursor == cursor


def test_query_service_enforces_pit_upper_bound_on_repository_results() -> None:
    service, repository, _ = _service()
    repository.page = SnapshotPage(
        items=(
            SnapshotSummary.from_snapshot(
                _snapshot(decision_ts=DECISION_TS + timedelta(seconds=1))
            ),
        )
    )

    with pytest.raises(QueryContractError, match="PIT upper bound"):
        service.list_snapshots(
            SnapshotQuery(
                company_id="company-1",
                decision_ts_lte=DECISION_TS,
            )
        )


def test_query_service_projects_research_view_from_the_selected_snapshot() -> None:
    service, _, projector = _service()

    view = service.get_research_view("snapshot-1")

    assert view.snapshot_id == "snapshot-1"
    assert projector.snapshot == _snapshot()
