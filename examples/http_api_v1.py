"""Minimal HTTP API v1 wiring example.

The example builds the FastAPI adapter and its OpenAPI contract without starting a
server or opening a database. Replace ExampleResearchQuery with ResearchQueryService
backed by a verified persistence repository in production.
"""

from __future__ import annotations

import json

from research_os.api.app import create_app


class ExampleResearchQuery:
    def get_run(self, run_id):
        raise KeyError(run_id)

    def get_artifact(self, run_id, artifact_id):
        raise KeyError((run_id, artifact_id))

    def list_snapshots(self, query):
        raise KeyError(query.company_id)

    def get_snapshot(self, snapshot_id):
        raise KeyError(snapshot_id)

    def get_research_view(self, snapshot_id):
        raise KeyError(snapshot_id)


def main() -> None:
    app = create_app(ExampleResearchQuery())
    schema = app.openapi()
    paths = sorted(schema["paths"])
    required = {
        "/api/v1/health",
        "/api/v1/research-runs/{run_id}",
        "/api/v1/snapshots/{snapshot_id}",
        "/api/v1/snapshots/{snapshot_id}/research-view",
    }
    if not required.issubset(paths):
        raise RuntimeError("HTTP API v1 example is missing required routes")
    print(json.dumps({"api_version": app.version, "paths": paths}, sort_keys=True))


if __name__ == "__main__":
    main()
