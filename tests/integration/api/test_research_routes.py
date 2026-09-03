from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from research_os.api.app import create_app
from research_os.api.contracts import (
    ArtifactView,
    HumanReadableResearchView,
    ResearchRunView,
    SnapshotPage,
    SnapshotQuery,
    SnapshotSummary,
    SnapshotView,
)
from research_os.api.errors import SnapshotNotFoundError
from research_os.application.result import RunVersionSet


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


def _snapshot() -> SnapshotView:
    return SnapshotView(
        snapshot_id="snapshot-1",
        schema_version="2.0",
        codec_version="jcs-1",
        hash_algorithm="sha256",
        run_id="run-1",
        company_id="company-1",
        decision_ts=DECISION_TS,
        created_at=CREATED_AT,
        research_digest="b" * 64,
        integrity_digest="c" * 64,
        payload={"result": "ready"},
    )


class _QueryService:
    def __init__(self) -> None:
        self.last_query: SnapshotQuery | None = None

    def get_run(self, run_id: str) -> ResearchRunView:
        return ResearchRunView(
            run_id=run_id,
            company_id="company-1",
            decision_ts=DECISION_TS,
            created_at=CREATED_AT,
            execution_completion="COMPLETE",
            research_readiness="READY",
            versions=_versions(),
            snapshot_id="snapshot-1",
        )

    def get_artifact(self, run_id: str, artifact_id: str) -> ArtifactView:
        return ArtifactView(
            run_id=run_id,
            artifact_id=artifact_id,
            schema_version="2.0",
            producer_ids=("core:test",),
            value={"status": "ready"},
        )

    def list_snapshots(self, query: SnapshotQuery) -> SnapshotPage:
        self.last_query = query
        return SnapshotPage(
            items=(SnapshotSummary.from_snapshot(_snapshot()),),
            next_cursor="next_page",
        )

    def get_snapshot(self, snapshot_id: str) -> SnapshotView:
        if snapshot_id == "missing":
            raise SnapshotNotFoundError(snapshot_id)
        return _snapshot()

    def get_research_view(self, snapshot_id: str) -> HumanReadableResearchView:
        return HumanReadableResearchView(
            snapshot_id=snapshot_id,
            company_id="company-1",
            decision_ts=DECISION_TS,
            presentation_version="research-view@2",
            content={"summary": "ready"},
        )


def _client() -> tuple[TestClient, _QueryService]:
    service = _QueryService()
    return TestClient(create_app(service)), service


def test_all_six_read_only_routes_return_typed_responses() -> None:
    client, _ = _client()

    responses = (
        client.get("/api/v1/research-runs/run-1"),
        client.get("/api/v1/research-runs/run-1/artifacts/valuation.summary"),
        client.get("/api/v1/companies/company-1/snapshots"),
        client.get("/api/v1/snapshots/snapshot-1"),
        client.get("/api/v1/snapshots/snapshot-1/research-view"),
        client.get("/api/v1/health"),
    )

    assert [response.status_code for response in responses] == [200] * 6
    assert responses[0].json()["run_id"] == "run-1"
    assert responses[1].json()["schema_version"] == "2.0"
    assert responses[2].json()["items"][0]["snapshot_id"] == "snapshot-1"
    assert responses[3].json()["integrity_digest"] == "c" * 64
    assert responses[4].json()["content"] == {"summary": "ready"}
    assert responses[5].json() == {"status": "ok", "http_api_version": "v1"}


def test_snapshot_route_passes_pagination_and_pit_parameters() -> None:
    client, service = _client()

    response = client.get(
        "/api/v1/companies/company-1/snapshots",
        params={
            "decision_ts_lte": "2026-08-29T00:00:00Z",
            "limit": 25,
            "cursor": "next_page",
        },
    )

    assert response.status_code == 200
    assert service.last_query == SnapshotQuery(
        company_id="company-1",
        decision_ts_lte=datetime(2026, 8, 29, tzinfo=timezone.utc),
        limit=25,
        cursor="next_page",
    )


def test_not_found_uses_rfc7807_problem_json_with_request_id() -> None:
    client, _ = _client()

    response = client.get(
        "/api/v1/snapshots/missing",
        headers={"X-Request-ID": "upstream-request-1"},
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.headers["X-Request-ID"] == "upstream-request-1"
    assert response.json() == {
        "type": "urn:research-os:error:snapshot-not-found",
        "title": "Snapshot not found",
        "status": 404,
        "detail": "No snapshot exists for identifier 'missing'.",
        "instance": "/api/v1/snapshots/missing",
        "request_id": "upstream-request-1",
    }


def test_every_response_has_request_id_and_valid_upstream_id_is_preserved() -> None:
    client, _ = _client()

    generated = client.get("/api/v1/health")
    preserved = client.get("/api/v1/health", headers={"X-Request-ID": "edge:request/123"})

    assert generated.headers["X-Request-ID"]
    assert preserved.headers["X-Request-ID"] == "edge:request/123"


def test_request_id_with_control_characters_is_rejected() -> None:
    client, _ = _client()

    response = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": "invalid\x01request"},
    )

    assert response.status_code == 400
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "urn:research-os:error:invalid-request-id"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_invalid_cursor_and_naive_pit_timestamp_use_problem_json() -> None:
    client, _ = _client()

    invalid_cursor = client.get(
        "/api/v1/companies/company-1/snapshots",
        params={"cursor": "not an opaque cursor"},
    )
    naive_timestamp = client.get(
        "/api/v1/companies/company-1/snapshots",
        params={"decision_ts_lte": "2026-08-29T00:00:00"},
    )

    for response in (invalid_cursor, naive_timestamp):
        assert response.status_code == 422
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.json()["type"] == "urn:research-os:error:request-validation-failed"


def test_framework_404_and_405_errors_use_problem_json() -> None:
    client, _ = _client()

    responses = (
        client.get("/api/v1/unknown"),
        client.post("/api/v1/health"),
    )

    assert [response.status_code for response in responses] == [404, 405]
    for response in responses:
        assert response.headers["content-type"].startswith("application/problem+json")
        assert response.headers["X-Request-ID"] == response.json()["request_id"]


def test_unexpected_query_failure_uses_non_leaking_problem_json() -> None:
    service = _QueryService()

    def fail(run_id: str) -> ResearchRunView:
        del run_id
        raise RuntimeError("database password must not leak")

    service.get_run = fail  # type: ignore[method-assign]
    client = TestClient(create_app(service), raise_server_exceptions=False)

    response = client.get("/api/v1/research-runs/run-1")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["type"] == "urn:research-os:error:internal-error"
    assert "password" not in response.text
