from __future__ import annotations

import json
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any

from research_os.contracts.artifacts import artifact_value_fingerprint
from research_os.contracts.evidence import evidence_content_fingerprint
from research_os.domain.evidence import Evidence
from research_os.snapshots.codec import (
    ArtifactDecoderRegistry,
    SnapshotCodecV2,
    build_core_artifact_decoder_registry,
)
from research_os.snapshots.models import ResearchSnapshotPayloadV2, ResearchSnapshotV2
from research_os.application.repositories import ResearchRun

from .schema import EvidenceRecord, ResearchRunRecord, ResearchSnapshotRecord


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _dumps(value: Any) -> str | None:
    if value is None:
        return None
    return SnapshotCodecV2().encode_value(value).decode("utf-8")


def _loads(value: str | None) -> Any:
    return None if value is None else SnapshotCodecV2().decode_value(value)


def evidence_to_record(evidence: Evidence) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=evidence.evidence_id,
        revision_no=evidence.revision_no,
        company_id=evidence.company_id,
        evidence_type=evidence.evidence_type.value,
        period_end=evidence.period_end,
        period=evidence.period,
        publish_ts=_utc(evidence.publish_ts),
        ingested_at=_utc(evidence.ingested_at),
        value_json=_dumps(evidence.value),
        raw_value_json=_dumps(evidence.raw_value),
        normalized_value_json=_dumps(evidence.normalized_value),
        unit=evidence.unit,
        scope=evidence.scope,
        version=evidence.version,
        source_document_id=evidence.source_document_id,
        source_page=evidence.source_page,
        source_table=evidence.source_table,
        source_url=evidence.source_url,
        confidence_grade=evidence.confidence_grade.value,
        verification_status=evidence.verification_status.value,
        dataset_version=evidence.dataset_version,
        parser_version=evidence.parser_version,
        formula_version=evidence.formula_version,
        model_version=evidence.model_version,
        comparison_basis=evidence.comparison_basis,
        metric_kind=evidence.metric_kind,
        lineage_json=None,
        content_hash=evidence_content_fingerprint(evidence),
    )


def evidence_from_record(record: EvidenceRecord) -> Evidence:
    evidence = Evidence.model_validate(
        {
            "evidence_id": record.evidence_id,
            "revision_no": record.revision_no,
            "company_id": record.company_id,
            "evidence_type": record.evidence_type,
            "period_end": record.period_end,
            "period": record.period,
            "publish_ts": _utc(record.publish_ts),
            "ingested_at": _utc(record.ingested_at),
            "value": _loads(record.value_json),
            "raw_value": _loads(record.raw_value_json),
            "normalized_value": _loads(record.normalized_value_json),
            "unit": record.unit,
            "scope": record.scope,
            "version": record.version,
            "source_document_id": record.source_document_id,
            "source_page": record.source_page,
            "source_table": record.source_table,
            "source_url": record.source_url,
            "confidence_grade": record.confidence_grade,
            "verification_status": record.verification_status,
            "dataset_version": record.dataset_version,
            "parser_version": record.parser_version,
            "formula_version": record.formula_version,
            "model_version": record.model_version,
            "comparison_basis": record.comparison_basis,
            "metric_kind": record.metric_kind,
        }
    )
    if record.content_hash is not None and record.content_hash != evidence_content_fingerprint(
        evidence
    ):
        raise ValueError(
            f"evidence content hash mismatch: {record.evidence_id}@{record.revision_no}"
        )
    return evidence


def _freeze_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_value(item) for key, item in value.items()})
    return value


def snapshot_to_record(snapshot: ResearchSnapshotV2) -> ResearchSnapshotRecord:
    codec = SnapshotCodecV2()
    payload_json = codec.encode_research_projection(snapshot.payload).decode("utf-8")
    research_digest = codec.research_digest(snapshot.payload)
    if snapshot.payload_hash != research_digest:
        raise ValueError("snapshot research digest does not match payload")
    return ResearchSnapshotRecord(
        snapshot_id=snapshot.snapshot_id,
        company_id=snapshot.company_id,
        decision_ts=_utc(snapshot.decision_ts),
        versions_json=json.dumps(
            snapshot.versions.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        payload_json=payload_json,
        payload_hash=snapshot.payload_hash,
        schema_version=snapshot.schema_version,
        codec_version=snapshot.codec_version,
        hash_algorithm=snapshot.hash_algorithm,
        run_id=snapshot.run_id,
        created_at=_utc(snapshot.created_at),
        baseline_json=json.dumps(
            snapshot.baseline.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        component_fingerprints_json=json.dumps(
            [item.model_dump(mode="json") for item in snapshot.component_fingerprints],
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        artifact_fingerprints_json=json.dumps(
            [item.model_dump(mode="json") for item in snapshot.artifact_fingerprints],
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        research_digest=research_digest,
        integrity_digest=codec.integrity_digest(snapshot),
    )


def snapshot_from_record(
    record: ResearchSnapshotRecord,
    decoder_registry: ArtifactDecoderRegistry | None = None,
) -> ResearchSnapshotV2:
    if (
        record.schema_version != "2.0"
        or record.codec_version != "jcs-1"
        or record.hash_algorithm is None
        or record.run_id is None
        or record.created_at is None
        or record.baseline_json is None
        or record.component_fingerprints_json is None
        or record.artifact_fingerprints_json is None
    ):
        raise ValueError("only complete Snapshot Schema 2.0 rows using codec jcs-1 can be read")
    payload_data = SnapshotCodecV2().decode_value(record.payload_json)
    if not isinstance(payload_data, dict):
        raise ValueError("stored snapshot payload must be an object")
    artifacts = payload_data.get("artifacts", [])
    if not isinstance(artifacts, (list, tuple)):
        raise ValueError("stored snapshot artifacts must be an array")
    fingerprint_data = json.loads(record.artifact_fingerprints_json)
    if not isinstance(fingerprint_data, list):
        raise ValueError("stored artifact fingerprints must be an array")
    fingerprints = {
        (
            item.get("artifact_id", ""),
            item.get("schema_version", ""),
            item.get("type_id", ""),
        ): item.get("value_fingerprint", "")
        for item in fingerprint_data
        if isinstance(item, dict)
    }
    registry = decoder_registry or build_core_artifact_decoder_registry()
    for artifact in artifacts:
        if not isinstance(artifact, dict) or "payload" not in artifact:
            raise ValueError("stored snapshot artifact must be an object")
        identity = (
            artifact.get("artifact_id", ""),
            artifact.get("schema_version", ""),
            artifact.get("type_id", ""),
        )
        artifact["payload"] = registry.decode(
            artifact_id=identity[0],
            schema_version=identity[1],
            type_id=identity[2],
            payload=artifact["payload"],
        )
        expected_fingerprint = fingerprints.get(identity)
        actual_fingerprint = artifact_value_fingerprint(artifact["payload"])
        if expected_fingerprint != actual_fingerprint:
            raise ValueError(
                "stored artifact fingerprint drift after controlled decode: "
                f"{identity[0]}@{identity[1]} ({identity[2]}), "
                f"expected={expected_fingerprint}, actual={actual_fingerprint}"
            )
    assumptions = payload_data.get("input_assumptions")
    if isinstance(assumptions, (list, tuple)):
        payload_data["input_assumptions"] = tuple(_freeze_value(item) for item in assumptions)
    payload = ResearchSnapshotPayloadV2.model_validate(payload_data)
    snapshot = ResearchSnapshotV2.model_validate(
        {
            "snapshot_id": record.snapshot_id,
            "schema_version": record.schema_version,
            "codec_version": record.codec_version,
            "hash_algorithm": record.hash_algorithm,
            "run_id": record.run_id,
            "company_id": record.company_id,
            "decision_ts": _utc(record.decision_ts),
            "created_at": _utc(record.created_at),
            "baseline": json.loads(record.baseline_json),
            "versions": json.loads(record.versions_json),
            "component_fingerprints": json.loads(record.component_fingerprints_json),
            "artifact_fingerprints": fingerprint_data,
            "payload": payload,
            "payload_hash": record.payload_hash,
        }
    )
    codec = SnapshotCodecV2()
    if record.payload_json != codec.encode_research_projection(snapshot.payload).decode("utf-8"):
        raise ValueError("stored snapshot payload is not canonical")
    if record.research_digest != codec.research_digest(snapshot.payload):
        raise ValueError("stored snapshot research digest does not match payload")
    if record.integrity_digest != codec.integrity_digest(snapshot):
        raise ValueError("stored snapshot integrity digest does not match envelope")
    return snapshot


def run_to_record(run: ResearchRun) -> ResearchRunRecord:
    return ResearchRunRecord(
        run_id=run.run_id,
        company_id=run.company_id,
        decision_ts=_utc(run.decision_ts),
        created_at=_utc(run.created_at),
        baseline_json=json.dumps(
            run.baseline.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        versions_json=json.dumps(
            run.versions.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ),
        payload_json=run.payload_json,
    )


def run_from_record(record: ResearchRunRecord) -> ResearchRun:
    return ResearchRun.model_validate(
        {
            "run_id": record.run_id,
            "company_id": record.company_id,
            "decision_ts": _utc(record.decision_ts),
            "created_at": _utc(record.created_at),
            "baseline": json.loads(record.baseline_json),
            "versions": json.loads(record.versions_json),
            "payload_json": record.payload_json,
        }
    )
