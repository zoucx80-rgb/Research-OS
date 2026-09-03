"""Stable query errors translated to RFC 7807 by the HTTP adapter."""

from __future__ import annotations


class ResearchQueryError(Exception):
    problem_type = "query-failed"
    title = "Research query failed"
    status = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class RunNotFoundError(ResearchQueryError):
    problem_type = "run-not-found"
    title = "Research run not found"
    status = 404

    def __init__(self, run_id: str) -> None:
        super().__init__(f"No research run exists for identifier '{run_id}'.")


class ArtifactNotFoundError(ResearchQueryError):
    problem_type = "artifact-not-found"
    title = "Artifact not found"
    status = 404

    def __init__(self, run_id: str, artifact_id: str) -> None:
        super().__init__(f"No artifact '{artifact_id}' exists for research run '{run_id}'.")


class SnapshotNotFoundError(ResearchQueryError):
    problem_type = "snapshot-not-found"
    title = "Snapshot not found"
    status = 404

    def __init__(self, snapshot_id: str) -> None:
        super().__init__(f"No snapshot exists for identifier '{snapshot_id}'.")


class QueryContractError(ResearchQueryError):
    problem_type = "query-contract-violation"
    title = "Query contract violation"
    status = 500


class InvalidCursorError(ResearchQueryError):
    problem_type = "invalid-cursor"
    title = "Invalid cursor"
    status = 400

    def __init__(self) -> None:
        super().__init__("The supplied pagination cursor is invalid or expired.")
