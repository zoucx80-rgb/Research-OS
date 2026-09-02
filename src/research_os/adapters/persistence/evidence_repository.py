from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from research_os.contracts.evidence import EvidenceRef, EvidenceSet, evidence_content_fingerprint
from research_os.domain.evidence import Evidence

from .mappers import evidence_from_record, evidence_to_record
from .schema import EvidenceRecord


class SqlEvidenceRepository:
    """Append-only evidence storage with a database-side point-in-time query."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(self, evidence: Evidence) -> None:
        self._session.add(evidence_to_record(evidence))
        self._session.flush()

    def latest_as_of(self, company_id: str, decision_ts: datetime) -> EvidenceSet:
        ranked = (
            select(
                EvidenceRecord.id.label("row_id"),
                func.row_number()
                .over(
                    partition_by=EvidenceRecord.evidence_id,
                    order_by=(EvidenceRecord.publish_ts.desc(), EvidenceRecord.revision_no.desc()),
                )
                .label("row_number"),
            )
            .where(EvidenceRecord.company_id == company_id)
            .where(EvidenceRecord.publish_ts <= decision_ts)
            .subquery()
        )
        statement = (
            select(EvidenceRecord)
            .join(ranked, EvidenceRecord.id == ranked.c.row_id)
            .where(ranked.c.row_number == 1)
            .order_by(EvidenceRecord.evidence_id)
        )
        items = tuple(evidence_from_record(record) for record in self._session.scalars(statement))
        return EvidenceSet(
            items=items,
            evidence_refs=tuple(
                EvidenceRef(
                    evidence_id=item.evidence_id,
                    revision=item.revision_no,
                    content_fingerprint=evidence_content_fingerprint(item),
                )
                for item in items
            ),
        )
