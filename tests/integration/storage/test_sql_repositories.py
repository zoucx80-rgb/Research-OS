from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from research_os.adapters.persistence.evidence_repository import SqlEvidenceRepository
from research_os.adapters.persistence.schema import PersistenceBase
from research_os.adapters.persistence.snapshot_repository import SqlSnapshotRepository
from research_os.application.result import RunVersionSet
from research_os.contracts.artifacts import artifact_value_fingerprint
from research_os.contracts.evidence import evidence_content_fingerprint
from research_os.domain.evidence import Evidence
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.snapshots.models import (
    ArtifactFingerprint,
    ResearchSnapshotPayloadV2,
    ResearchSnapshotV2,
    SnapshotArtifactV2,
)
from research_os.snapshots.codec import ArtifactDecoderRegistry, SnapshotCodecV2
from types import MappingProxyType


def _evidence(**changes: object) -> Evidence:
    values: dict[str, object] = {
        "evidence_id": "revenue",
        "company_id": "000001.SZ",
        "evidence_type": "filing_fact",
        "period_end": "2026-06-30",
        "period": "2026H1",
        "publish_ts": datetime(2026, 8, 1, tzinfo=timezone.utc),
        "ingested_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
        "value": 10,
        "raw_value": "10",
        "normalized_value": 10,
        "unit": "CNY",
        "scope": "consolidated",
        "comparison_basis": "reported",
        "metric_kind": "flow",
        "confidence_grade": "A",
        "verification_status": "PRIMARY_VERIFIED",
    }
    values.update(changes)
    return Evidence.model_validate(values)


def _repository() -> SqlEvidenceRepository:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    PersistenceBase.metadata.create_all(engine)
    return SqlEvidenceRepository(sessionmaker(engine)())


def test_latest_as_of_selects_database_revision_and_binds_evidence_refs() -> None:
    repository = _repository()
    revision_one = _evidence(revision_no=1, value=10)
    future_revision = _evidence(
        revision_no=2,
        value=12,
        publish_ts=datetime(2026, 8, 20, tzinfo=timezone.utc),
    )
    another_fact = _evidence(evidence_id="margin", value=3, revision_no=1)
    repository.append(revision_one)
    repository.append(future_revision)
    repository.append(another_fact)

    result = repository.latest_as_of("000001.SZ", datetime(2026, 8, 15, tzinfo=timezone.utc))

    assert [(item.evidence_id, item.revision_no, item.value) for item in result.items] == [
        ("margin", 1, 3),
        ("revenue", 1, 10),
    ]
    assert result.evidence_refs == tuple(
        sorted(
            (reference for reference in result.evidence_refs),
            key=lambda reference: reference.evidence_id,
        )
    )
    assert result.evidence_refs[1].revision == 1
    assert result.evidence_refs[1].content_fingerprint == evidence_content_fingerprint(revision_one)


def test_evidence_mapper_round_trips_v1_6_semantic_and_lineage_columns() -> None:
    repository = _repository()
    evidence = _evidence(
        evidence_id="cash-flow",
        comparison_basis="constant_currency",
        metric_kind="stock",
        source_document_id="annual-report",
        source_page=88,
        source_table="cash-flow",
        source_url="https://example.invalid/report",
        dataset_version="dataset@1",
        parser_version="parser@1",
        formula_version="formula@1",
        model_version="model@1",
    )
    repository.append(evidence)

    restored = repository.latest_as_of(
        "000001.SZ", datetime(2026, 8, 2, tzinfo=timezone.utc)
    ).items[0]

    assert restored.model_dump(mode="python") == evidence.model_dump(mode="python")


def test_evidence_mapper_round_trips_reserved_codec_keys_as_ordinary_data() -> None:
    repository = _repository()
    reserved = {
        "$type": "decimal",
        "value": "1.2",
        "nested": {"$type": "integer", "value": "1"},
    }
    evidence = _evidence(
        evidence_id="reserved-keys",
        value=reserved,
        raw_value=reserved,
        normalized_value=reserved,
    )
    repository.append(evidence)

    restored = repository.latest_as_of(
        "000001.SZ", datetime(2026, 8, 2, tzinfo=timezone.utc)
    ).items[0]

    assert restored.value == reserved
    assert restored.raw_value == reserved
    assert restored.normalized_value == reserved


def test_evidence_repository_rejects_content_tampering() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    PersistenceBase.metadata.create_all(engine)
    session = sessionmaker(engine)()
    repository = SqlEvidenceRepository(session)
    repository.append(_evidence())
    session.commit()
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE evidence SET normalized_value_json = '999' WHERE evidence_id = 'revenue'")
        )

    with pytest.raises(ValueError, match="content hash"):
        repository.latest_as_of("000001.SZ", datetime(2026, 8, 2, tzinfo=timezone.utc))


def _snapshot() -> ResearchSnapshotV2:
    baseline = BaselineFingerprint(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        commit_sha="a" * 40,
        research_os_version="1.6.0",
        core_api_version="2.0",
    )
    versions = RunVersionSet(
        research_os_version="1.6.0",
        core_api_version="2.0",
        plugin_api_version="2.0",
        snapshot_schema_version="2.0",
        http_api_version="v1",
    )
    decision_ts = datetime(2026, 9, 1, tzinfo=timezone.utc)
    payload = ResearchSnapshotPayloadV2(
        company=CompanyRef(company_id="000001.SZ"),
        decision_ts=decision_ts,
        baseline=baseline,
        versions=versions,
        component_fingerprints=(),
        artifacts=(
            SnapshotArtifactV2(
                artifact_id="decision.record",
                schema_version="2.0",
                type_id="decision-record-v2",
                producer_ids=("decision",),
                payload=MappingProxyType({"state": "WAIT"}),
            ),
        ),
    )
    return ResearchSnapshotV2(
        snapshot_id="snapshot-restart",
        schema_version="2.0",
        codec_version="jcs-1",
        hash_algorithm="sha256",
        run_id="run-restart",
        company_id="000001.SZ",
        decision_ts=decision_ts,
        created_at=decision_ts,
        baseline=baseline,
        versions=versions,
        component_fingerprints=(),
        artifact_fingerprints=(
            ArtifactFingerprint(
                artifact_id="decision.record",
                schema_version="2.0",
                type_id="decision-record-v2",
                value_fingerprint=artifact_value_fingerprint(payload.artifacts[0].payload),
            ),
        ),
        payload=payload,
        payload_hash=SnapshotCodecV2().research_digest(payload),
    )


def _decoder_registry() -> ArtifactDecoderRegistry:
    registry = ArtifactDecoderRegistry()
    registry.register(
        artifact_id="decision.record",
        schema_version="2.0",
        type_id="decision-record-v2",
        decoder=lambda value: MappingProxyType(dict(value)),
    )
    return registry


def test_snapshot_is_readable_after_session_restart(tmp_path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'snapshots.sqlite3'}")
    PersistenceBase.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    snapshot = _snapshot()
    repository = SqlSnapshotRepository(sessions(), _decoder_registry())
    repository.append(snapshot)
    repository.session.commit()
    repository.session.close()

    restored = SqlSnapshotRepository(sessions(), _decoder_registry()).get(snapshot.snapshot_id)

    assert restored == snapshot


def test_snapshot_restart_preserves_reserved_codec_keys_as_ordinary_data(
    tmp_path,
) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'reserved-keys.sqlite3'}")
    PersistenceBase.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    original = _snapshot()
    reserved = MappingProxyType({"$type": "integer", "value": "1"})
    artifact = original.payload.artifacts[0].model_copy(update={"payload": reserved})
    payload = original.payload.model_copy(update={"artifacts": (artifact,)})
    fingerprint = original.artifact_fingerprints[0].model_copy(
        update={"value_fingerprint": artifact_value_fingerprint(reserved)}
    )
    snapshot = original.model_copy(
        update={
            "payload": payload,
            "artifact_fingerprints": (fingerprint,),
            "payload_hash": SnapshotCodecV2().research_digest(payload),
        }
    )
    repository = SqlSnapshotRepository(sessions(), _decoder_registry())
    repository.append(snapshot)
    repository.session.commit()

    restored = SqlSnapshotRepository(sessions(), _decoder_registry()).get(snapshot.snapshot_id)

    assert restored.payload.artifacts[0].payload == reserved
    assert restored.payload_hash == snapshot.payload_hash


def test_snapshot_repository_rejects_tampered_persisted_payload(tmp_path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'tampered.sqlite3'}")
    PersistenceBase.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    snapshot = _snapshot()
    repository = SqlSnapshotRepository(sessions(), _decoder_registry())
    repository.append(snapshot)
    repository.session.commit()
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE research_snapshot SET payload_json = "
                "replace(payload_json, 'WAIT', 'BUY') "
                "WHERE snapshot_id = :snapshot_id"
            ),
            {"snapshot_id": snapshot.snapshot_id},
        )

    with pytest.raises(ValueError, match="digest|fingerprint"):
        SqlSnapshotRepository(sessions(), _decoder_registry()).get(snapshot.snapshot_id)


def test_snapshot_repository_rejects_unknown_codec_before_decoding(tmp_path) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'codec.sqlite3'}")
    PersistenceBase.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    snapshot = _snapshot()
    repository = SqlSnapshotRepository(sessions(), _decoder_registry())
    repository.append(snapshot)
    repository.session.commit()
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE research_snapshot SET codec_version = 'future-codec' "
                "WHERE snapshot_id = :snapshot_id"
            ),
            {"snapshot_id": snapshot.snapshot_id},
        )

    with pytest.raises(ValueError, match="codec"):
        SqlSnapshotRepository(sessions(), _decoder_registry()).get(snapshot.snapshot_id)


def test_snapshot_repository_rejects_noncanonical_persisted_payload_bytes(
    tmp_path,
) -> None:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'noncanonical.sqlite3'}")
    PersistenceBase.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    snapshot = _snapshot()
    repository = SqlSnapshotRepository(sessions(), _decoder_registry())
    repository.append(snapshot)
    repository.session.commit()
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE research_snapshot SET payload_json = ' ' || payload_json "
                "WHERE snapshot_id = :snapshot_id"
            ),
            {"snapshot_id": snapshot.snapshot_id},
        )

    with pytest.raises(ValueError, match="canonical"):
        SqlSnapshotRepository(sessions(), _decoder_registry()).get(snapshot.snapshot_id)


def test_snapshot_repository_rejects_invalid_digest_before_insert() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    PersistenceBase.metadata.create_all(engine)
    repository = SqlSnapshotRepository(sessionmaker(engine)(), _decoder_registry())
    invalid = _snapshot().model_copy(update={"payload_hash": "0" * 64})

    with pytest.raises(ValueError, match="research digest"):
        repository.append(invalid)


def test_snapshot_repository_rechecks_artifact_bindings_before_insert() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    PersistenceBase.metadata.create_all(engine)
    repository = SqlSnapshotRepository(sessionmaker(engine)(), _decoder_registry())
    invalid = _snapshot().model_copy(update={"artifact_fingerprints": ()})

    with pytest.raises(ValueError, match="one-to-one"):
        repository.append(invalid)
