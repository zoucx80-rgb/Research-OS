from __future__ import annotations

from sqlalchemy.orm import Session

from research_os.application.repositories import ResearchRun

from .mappers import run_from_record, run_to_record
from .schema import ResearchRunRecord


class SqlResearchRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, run: ResearchRun) -> None:
        self._session.add(run_to_record(run))
        self._session.flush()

    def get(self, run_id: str) -> ResearchRun:
        record = self._session.get(ResearchRunRecord, run_id)
        if record is None:
            raise KeyError(run_id)
        return run_from_record(record)
