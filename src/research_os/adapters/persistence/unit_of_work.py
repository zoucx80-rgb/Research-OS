from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from .evidence_repository import SqlEvidenceRepository
from .run_repository import SqlResearchRunRepository
from .snapshot_repository import SqlSnapshotRepository


class SqlUnitOfWork:
    """A single SQL transaction shared by all persistence repositories."""

    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self.evidence: SqlEvidenceRepository
        self.runs: SqlResearchRunRepository
        self.snapshots: SqlSnapshotRepository

    def __enter__(self) -> SqlUnitOfWork:
        self._session = self._session_factory()
        self.evidence = SqlEvidenceRepository(self._session)
        self.runs = SqlResearchRunRepository(self._session)
        self.snapshots = SqlSnapshotRepository(self._session)
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if self._session is None:
            return
        if exc_type is not None:
            self.rollback()
        self._session.close()
        self._session = None

    def commit(self) -> None:
        self._require_session().commit()

    def rollback(self) -> None:
        self._require_session().rollback()

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork must be used as a context manager")
        return self._session
