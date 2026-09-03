from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PersistenceBase(DeclarativeBase):
    pass


class EvidenceRecord(PersistenceBase):
    __tablename__ = "evidence"
    __table_args__ = (UniqueConstraint("evidence_id", "revision_no", name="uq_evidence_revision"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evidence_id: Mapped[str] = mapped_column(String, nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    company_id: Mapped[str] = mapped_column(String, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String, nullable=False)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    period: Mapped[str | None] = mapped_column(String, nullable=True)
    publish_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    value_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_value_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    scope: Mapped[str | None] = mapped_column(String, nullable=True)
    version: Mapped[str | None] = mapped_column(String, nullable=True)
    source_document_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_table: Mapped[str | None] = mapped_column(String, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_grade: Mapped[str] = mapped_column(String, nullable=False)
    verification_status: Mapped[str] = mapped_column(String, nullable=False)
    dataset_version: Mapped[str | None] = mapped_column(String, nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String, nullable=True)
    formula_version: Mapped[str | None] = mapped_column(String, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    comparison_basis: Mapped[str | None] = mapped_column(String, nullable=True)
    metric_kind: Mapped[str | None] = mapped_column(String, nullable=True)
    lineage_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String, nullable=True)


class ResearchRunRecord(PersistenceBase):
    __tablename__ = "research_run"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(String, nullable=False)
    decision_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    baseline_json: Mapped[str] = mapped_column(Text, nullable=False)
    versions_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)


class ResearchSnapshotRecord(PersistenceBase):
    __tablename__ = "research_snapshot"
    __table_args__ = (UniqueConstraint("run_id", name="uq_research_snapshot_run_id"),)

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(String, nullable=False)
    decision_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    versions_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str | None] = mapped_column(String, nullable=True)
    codec_version: Mapped[str | None] = mapped_column(String, nullable=True)
    hash_algorithm: Mapped[str | None] = mapped_column(String, nullable=True)
    run_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("research_run.run_id"), nullable=True
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    baseline_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    component_fingerprints_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_fingerprints_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    research_digest: Mapped[str | None] = mapped_column(String, nullable=True)
    integrity_digest: Mapped[str | None] = mapped_column(String, nullable=True)


class ArtifactIndexRecord(PersistenceBase):
    __tablename__ = "artifact_index"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_id",
            "artifact_id",
            "schema_version",
            "provider_id",
            name="uq_artifact_index_snapshot_key_provider",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(
        String, ForeignKey("research_snapshot.snapshot_id"), nullable=False
    )
    artifact_id: Mapped[str] = mapped_column(String, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)
    provider_id: Mapped[str] = mapped_column(String, nullable=False)
    fingerprint: Mapped[str] = mapped_column(String, nullable=False)
