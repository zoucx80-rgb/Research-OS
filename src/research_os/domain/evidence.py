from datetime import date, datetime
from typing import Any
from pydantic import BaseModel, ConfigDict
from .enums import ConfidenceGrade, EvidenceType, VerificationStatus


class Evidence(BaseModel):
    model_config=ConfigDict(frozen=True)
    evidence_id: str
    company_id: str
    evidence_type: EvidenceType
    period_end: date | None=None
    period: str | None=None
    publish_ts: datetime
    ingested_at: datetime
    value: Any=None
    raw_value: Any=None
    normalized_value: Any=None
    unit: str | None=None
    scope: str | None=None
    version: str | None=None
    source_document_id: str | None=None
    source_page: int | None=None
    source_table: str | None=None
    source_url: str | None=None
    confidence_grade: ConfidenceGrade
    verification_status: VerificationStatus
    dataset_version: str | None=None
    parser_version: str | None=None
    formula_version: str | None=None
    model_version: str | None=None
    revision_no: int=1
