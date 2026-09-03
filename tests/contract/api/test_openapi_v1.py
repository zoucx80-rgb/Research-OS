from __future__ import annotations

from typing import cast

from research_os.api.app import create_app
from research_os.api.query import ResearchQuery
from research_os.version import CORE_API_VERSION, HTTP_API_VERSION


class _UnusedQueryService:
    def __getattr__(self, name: str) -> object:
        raise AssertionError(f"OpenAPI generation must not call Query Service: {name}")


def test_openapi_v1_freezes_six_read_only_paths_and_independent_version() -> None:
    schema = create_app(cast(ResearchQuery, _UnusedQueryService())).openapi()

    assert schema["info"]["version"] == HTTP_API_VERSION == "v1"
    assert schema["info"]["version"] != CORE_API_VERSION
    assert set(schema["paths"]) == {
        "/api/v1/research-runs/{run_id}",
        "/api/v1/research-runs/{run_id}/artifacts/{artifact_id}",
        "/api/v1/companies/{company_id}/snapshots",
        "/api/v1/snapshots/{snapshot_id}",
        "/api/v1/snapshots/{snapshot_id}/research-view",
        "/api/v1/health",
    }
    assert all(set(operations) == {"get"} for operations in schema["paths"].values())


def test_snapshot_list_openapi_exposes_pagination_pit_and_response_model() -> None:
    schema = create_app(cast(ResearchQuery, _UnusedQueryService())).openapi()
    operation = schema["paths"]["/api/v1/companies/{company_id}/snapshots"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}

    assert set(parameters) == {"company_id", "decision_ts_lte", "limit", "cursor"}
    assert parameters["limit"]["schema"]["maximum"] == 100
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/SnapshotPage"
    }


def test_openapi_documents_problem_details_for_not_found() -> None:
    schema = create_app(cast(ResearchQuery, _UnusedQueryService())).openapi()
    operation = schema["paths"]["/api/v1/snapshots/{snapshot_id}"]["get"]

    problem_schema = operation["responses"]["404"]["content"]["application/problem+json"]["schema"]
    assert problem_schema["title"] == "ProblemDetails"
    assert set(problem_schema["required"]) == {
        "type",
        "title",
        "status",
        "detail",
        "instance",
        "request_id",
    }
    assert "500" in operation["responses"]


def test_openapi_documents_only_problem_json_for_error_responses() -> None:
    schema = create_app(cast(ResearchQuery, _UnusedQueryService())).openapi()

    for path in schema["paths"].values():
        for status, response in path["get"]["responses"].items():
            if status == "200":
                continue
            assert set(response["content"]) == {"application/problem+json"}
