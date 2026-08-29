import json
from datetime import datetime
from sqlalchemy import Date, DateTime, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from research_os.domain.evidence import Evidence

class Base(DeclarativeBase):
    pass

class EvidenceRow(Base):
    __tablename__="evidence"
    __table_args__=(UniqueConstraint("evidence_id","revision_no",name="uq_evidence_revision"),)
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    evidence_id: Mapped[str]=mapped_column(String,nullable=False)
    revision_no: Mapped[int]=mapped_column(Integer,nullable=False,default=1)
    company_id: Mapped[str]=mapped_column(String,index=True,nullable=False)
    evidence_type: Mapped[str]=mapped_column(String,nullable=False)
    period_end: Mapped[object | None]=mapped_column(Date,nullable=True)
    publish_ts: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True,nullable=False)
    ingested_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
    value_json: Mapped[str | None]=mapped_column(Text,nullable=True)
    unit: Mapped[str | None]=mapped_column(String,nullable=True)
    scope: Mapped[str | None]=mapped_column(String,nullable=True)
    source_document_id: Mapped[str | None]=mapped_column(String,nullable=True)
    source_page: Mapped[int | None]=mapped_column(Integer,nullable=True)
    source_table: Mapped[str | None]=mapped_column(String,nullable=True)
    source_url: Mapped[str | None]=mapped_column(Text,nullable=True)
    confidence_grade: Mapped[str]=mapped_column(String,nullable=False)
    verification_status: Mapped[str]=mapped_column(String,nullable=False)
    dataset_version: Mapped[str | None]=mapped_column(String,nullable=True)
    parser_version: Mapped[str | None]=mapped_column(String,nullable=True)
    formula_version: Mapped[str | None]=mapped_column(String,nullable=True)
    model_version: Mapped[str | None]=mapped_column(String,nullable=True)

    @classmethod
    def from_domain(cls,e: Evidence):
        return cls(
            evidence_id=e.evidence_id,revision_no=e.revision_no,company_id=e.company_id,
            evidence_type=e.evidence_type.value,period_end=e.period_end,publish_ts=e.publish_ts,
            ingested_at=e.ingested_at,value_json=json.dumps(e.value,ensure_ascii=False,default=str),
            unit=e.unit,scope=e.scope,source_document_id=e.source_document_id,source_page=e.source_page,
            source_table=e.source_table,source_url=e.source_url,confidence_grade=e.confidence_grade.value,
            verification_status=e.verification_status.value,dataset_version=e.dataset_version,
            parser_version=e.parser_version,formula_version=e.formula_version,model_version=e.model_version,
        )
    def to_domain(self):
        return Evidence(
            evidence_id=self.evidence_id,revision_no=self.revision_no,company_id=self.company_id,
            evidence_type=self.evidence_type,period_end=self.period_end,publish_ts=self.publish_ts,
            ingested_at=self.ingested_at,value=json.loads(self.value_json) if self.value_json is not None else None,
            unit=self.unit,scope=self.scope,source_document_id=self.source_document_id,source_page=self.source_page,
            source_table=self.source_table,source_url=self.source_url,confidence_grade=self.confidence_grade,
            verification_status=self.verification_status,dataset_version=self.dataset_version,
            parser_version=self.parser_version,formula_version=self.formula_version,model_version=self.model_version,
        )

class EvidenceStore:
    def __init__(self,session): self.session=session
    def append(self,evidence: Evidence)->None:
        self.session.add(EvidenceRow.from_domain(evidence)); self.session.flush()
    def as_of(self,company_id: str,decision_ts: datetime)->list[Evidence]:
        stmt=(select(EvidenceRow).where(EvidenceRow.company_id==company_id)
              .where(EvidenceRow.publish_ts<=decision_ts)
              .order_by(EvidenceRow.publish_ts,EvidenceRow.revision_no))
        return [r.to_domain() for r in self.session.scalars(stmt)]
    def latest_as_of(self,company_id: str,decision_ts: datetime)->list[Evidence]:
        latest: dict[str,Evidence]={}
        for e in self.as_of(company_id,decision_ts):
            prev=latest.get(e.evidence_id)
            if prev is None or (e.publish_ts,e.revision_no) >= (prev.publish_ts,prev.revision_no):
                latest[e.evidence_id]=e
        return sorted(latest.values(),key=lambda e:e.evidence_id)
