"""Read-only application query service and adapter-facing ports."""

from __future__ import annotations

from typing import Protocol

from research_os.api.contracts import (
    ArtifactView,
    HumanReadableResearchView,
    ResearchRunView,
    SnapshotPage,
    SnapshotQuery,
    SnapshotView,
)
from research_os.api.errors import (
    ArtifactNotFoundError,
    QueryContractError,
    RunNotFoundError,
    SnapshotNotFoundError,
)


class ResearchQueryRepository(Protocol):
    def get_run(self, run_id: str) -> ResearchRunView | None: ...

    def get_artifact(self, run_id: str, artifact_id: str) -> ArtifactView | None: ...

    def list_snapshots(self, query: SnapshotQuery) -> SnapshotPage: ...

    def get_snapshot(self, snapshot_id: str) -> SnapshotView | None: ...


class ResearchViewProjector(Protocol):
    def project(self, snapshot: SnapshotView) -> HumanReadableResearchView: ...


class SnapshotResearchViewProjector:
    """Initial human-readable projection; M4 may enrich presentation only."""

    def project(self, snapshot: SnapshotView) -> HumanReadableResearchView:
        return HumanReadableResearchView(
            snapshot_id=snapshot.snapshot_id,
            company_id=snapshot.company_id,
            decision_ts=snapshot.decision_ts,
            presentation_version="snapshot-2.0",
            content=snapshot.payload,
        )


class ResearchQuery(Protocol):
    def get_run(self, run_id: str) -> ResearchRunView: ...

    def get_artifact(self, run_id: str, artifact_id: str) -> ArtifactView: ...

    def list_snapshots(self, query: SnapshotQuery) -> SnapshotPage: ...

    def get_snapshot(self, snapshot_id: str) -> SnapshotView: ...

    def get_research_view(self, snapshot_id: str) -> HumanReadableResearchView: ...


class ResearchQueryService:
    def __init__(
        self,
        repository: ResearchQueryRepository,
        projector: ResearchViewProjector,
    ) -> None:
        self._repository = repository
        self._projector = projector

    def get_run(self, run_id: str) -> ResearchRunView:
        result = self._repository.get_run(run_id)
        if result is None:
            raise RunNotFoundError(run_id)
        return result

    def get_artifact(self, run_id: str, artifact_id: str) -> ArtifactView:
        result = self._repository.get_artifact(run_id, artifact_id)
        if result is None:
            raise ArtifactNotFoundError(run_id, artifact_id)
        return result

    def list_snapshots(self, query: SnapshotQuery) -> SnapshotPage:
        result = self._repository.list_snapshots(query)
        if len(result.items) > query.limit:
            raise QueryContractError("repository returned more snapshots than requested")
        for snapshot in result.items:
            if snapshot.company_id != query.company_id:
                raise QueryContractError("repository returned a different company")
            if query.decision_ts_lte is not None and snapshot.decision_ts > query.decision_ts_lte:
                raise QueryContractError("repository violated the PIT upper bound")
        return result

    def get_snapshot(self, snapshot_id: str) -> SnapshotView:
        result = self._repository.get_snapshot(snapshot_id)
        if result is None:
            raise SnapshotNotFoundError(snapshot_id)
        return result

    def get_research_view(self, snapshot_id: str) -> HumanReadableResearchView:
        return self._projector.project(self.get_snapshot(snapshot_id))
