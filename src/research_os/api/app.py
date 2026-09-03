"""FastAPI adapter for the read-only Research OS HTTP API v1."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException

from research_os.api.contracts import (
    ArtifactView,
    HealthView,
    HumanReadableResearchView,
    ProblemDetails,
    ResearchRunView,
    SnapshotPage,
    SnapshotQuery,
    SnapshotView,
)
from research_os.api.errors import ResearchQueryError
from research_os.api.query import ResearchQuery
from research_os.version import HTTP_API_VERSION


_REQUEST_ID = re.compile(r"^[\x21-\x7e]{1,128}$")
_PROBLEM_SCHEMA = ProblemDetails.model_json_schema()
_BAD_REQUEST_RESPONSE: dict[int | str, dict[str, Any]] = {
    400: {
        "description": "The request ID or pagination cursor is invalid.",
        "content": {"application/problem+json": {"schema": _PROBLEM_SCHEMA}},
    }
}
_NOT_FOUND_RESPONSE: dict[int | str, dict[str, Any]] = {
    404: {
        "description": "The requested research resource does not exist.",
        "content": {"application/problem+json": {"schema": _PROBLEM_SCHEMA}},
    }
}
_VALIDATION_RESPONSE: dict[int | str, dict[str, Any]] = {
    422: {
        "description": "One or more request parameters are invalid.",
        "content": {"application/problem+json": {"schema": _PROBLEM_SCHEMA}},
    }
}
_INTERNAL_RESPONSE: dict[int | str, dict[str, Any]] = {
    500: {
        "description": "The request could not be completed.",
        "content": {"application/problem+json": {"schema": _PROBLEM_SCHEMA}},
    }
}
_READ_RESPONSES = {
    **_BAD_REQUEST_RESPONSE,
    **_NOT_FOUND_RESPONSE,
    **_VALIDATION_RESPONSE,
    **_INTERNAL_RESPONSE,
}
_LIST_RESPONSES = {
    **_BAD_REQUEST_RESPONSE,
    **_VALIDATION_RESPONSE,
    **_INTERNAL_RESPONSE,
}
_HEALTH_RESPONSES = {**_BAD_REQUEST_RESPONSE, **_INTERNAL_RESPONSE}


def _request_id(request: Request) -> str:
    return str(request.state.request_id)


def _problem(
    request: Request,
    *,
    problem_type: str,
    title: str,
    status: int,
    detail: str,
) -> JSONResponse:
    body = ProblemDetails(
        type=f"urn:research-os:error:{problem_type}",
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        request_id=_request_id(request),
    )
    return JSONResponse(
        status_code=status,
        content=body.model_dump(mode="json"),
        media_type="application/problem+json",
    )


def create_app(query_service: ResearchQuery) -> FastAPI:
    app = FastAPI(title="Research OS", version=HTTP_API_VERSION)

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next: Any) -> Any:
        supplied = request.headers.get("X-Request-ID")
        generated = uuid4().hex
        request.state.request_id = supplied if supplied is not None else generated
        if supplied is not None and not _REQUEST_ID.fullmatch(supplied):
            request.state.request_id = generated
            response = _problem(
                request,
                problem_type="invalid-request-id",
                title="Invalid request ID",
                status=400,
                detail="X-Request-ID must contain visible ASCII characters only.",
            )
        else:
            response = await call_next(request)
        response.headers["X-Request-ID"] = _request_id(request)
        return response

    @app.exception_handler(ResearchQueryError)
    async def query_error_handler(request: Request, error: ResearchQueryError) -> JSONResponse:
        return _problem(
            request,
            problem_type=error.problem_type,
            title=error.title,
            status=error.status,
            detail=error.detail,
        )

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, error: RequestValidationError | ValidationError
    ) -> JSONResponse:
        del error
        return _problem(
            request,
            problem_type="request-validation-failed",
            title="Request validation failed",
            status=422,
            detail="One or more request parameters are invalid.",
        )

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, error: HTTPException) -> JSONResponse:
        return _problem(
            request,
            problem_type="http-error",
            title="HTTP request failed",
            status=error.status_code,
            detail=str(error.detail),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, error: Exception) -> JSONResponse:
        del error
        return _problem(
            request,
            problem_type="internal-error",
            title="Internal server error",
            status=500,
            detail="The request could not be completed.",
        )

    @app.get(
        "/api/v1/research-runs/{run_id}",
        response_model=ResearchRunView,
        responses=_READ_RESPONSES,
    )
    def get_run(run_id: str) -> ResearchRunView:
        return query_service.get_run(run_id)

    @app.get(
        "/api/v1/research-runs/{run_id}/artifacts/{artifact_id}",
        response_model=ArtifactView,
        responses=_READ_RESPONSES,
    )
    def get_artifact(run_id: str, artifact_id: str) -> ArtifactView:
        return query_service.get_artifact(run_id, artifact_id)

    @app.get(
        "/api/v1/companies/{company_id}/snapshots",
        response_model=SnapshotPage,
        responses=_LIST_RESPONSES,
    )
    def list_snapshots(
        company_id: str,
        decision_ts_lte: datetime | None = None,
        limit: int = Query(default=50, ge=1, le=100),
        cursor: str | None = None,
    ) -> SnapshotPage:
        return query_service.list_snapshots(
            SnapshotQuery(
                company_id=company_id,
                decision_ts_lte=decision_ts_lte,
                limit=limit,
                cursor=cursor,
            )
        )

    @app.get(
        "/api/v1/snapshots/{snapshot_id}",
        response_model=SnapshotView,
        responses=_READ_RESPONSES,
    )
    def get_snapshot(snapshot_id: str) -> SnapshotView:
        return query_service.get_snapshot(snapshot_id)

    @app.get(
        "/api/v1/snapshots/{snapshot_id}/research-view",
        response_model=HumanReadableResearchView,
        responses=_READ_RESPONSES,
    )
    def get_research_view(snapshot_id: str) -> HumanReadableResearchView:
        return query_service.get_research_view(snapshot_id)

    @app.get(
        "/api/v1/health",
        response_model=HealthView,
        responses=_HEALTH_RESPONSES,
    )
    def health() -> HealthView:
        return HealthView()

    return app
