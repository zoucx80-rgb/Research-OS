from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from types import MappingProxyType

import pytest
from pydantic import BaseModel, ConfigDict

from research_os.application.result import ComponentFingerprint, RunVersionSet
from research_os.contracts.artifacts import artifact_value_fingerprint
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.snapshots.codec import (
    ArtifactDecoderRegistry,
    SnapshotCodecError,
    SnapshotCodecV2,
)
from research_os.snapshots.models import (
    ArtifactFingerprint,
    ResearchSnapshotPayloadV2,
    ResearchSnapshotV2,
    SnapshotArtifactV2,
)


class _State(StrEnum):
    WAIT = "WAIT"


class _ExampleModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    amount: Decimal


def _payload(*, run_payload: object) -> ResearchSnapshotPayloadV2:
    try:
        artifact = SnapshotArtifactV2(
            artifact_id="decision.record",
            schema_version="2.0",
            type_id="decision-record-v2",
            producer_ids=("decision",),
            payload=run_payload,
        )
    except Exception:
        # A storage adapter can hold malformed historical bytes; the codec must
        # reject that data even when the public model constructor was bypassed.
        artifact = SnapshotArtifactV2.model_construct(
            artifact_id="decision.record",
            schema_version="2.0",
            type_id="decision-record-v2",
            producer_ids=("decision",),
            payload=run_payload,
            evidence_refs=(),
        )
    return ResearchSnapshotPayloadV2(
        company=CompanyRef(company_id="001287.SZ"),
        decision_ts=datetime(2026, 9, 1, 8, 30, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.6.0",
            core_api_version="2.0",
        ),
        versions=RunVersionSet(
            research_os_version="1.6.0",
            core_api_version="2.0",
            plugin_api_version="2.0",
            snapshot_schema_version="2.0",
            http_api_version="v1",
        ),
        component_fingerprints=(
            ComponentFingerprint(
                component_id="research.engine",
                component_type="module",
                component_version="2.0.0",
                api_version="2.0",
                fingerprint="b" * 64,
            ),
        ),
        artifacts=(
            artifact,
        ),
    )


def _snapshot(payload: ResearchSnapshotPayloadV2, *, run_id: str) -> ResearchSnapshotV2:
    return ResearchSnapshotV2(
        snapshot_id=f"snapshot-{run_id}",
        schema_version="2.0",
        codec_version="jcs-1",
        hash_algorithm="sha256",
        run_id=run_id,
        company_id="001287.SZ",
        decision_ts=payload.decision_ts,
        created_at=datetime(2026, 9, 1, 8, 31, tzinfo=timezone.utc),
        baseline=payload.baseline,
        versions=payload.versions,
        component_fingerprints=payload.component_fingerprints,
        artifact_fingerprints=(
            ArtifactFingerprint(
                artifact_id="decision.record",
                schema_version="2.0",
                type_id="decision-record-v2",
                value_fingerprint=artifact_value_fingerprint(
                    payload.artifacts[0].payload
                ),
            ),
        ),
        payload=payload,
        payload_hash="d" * 64,
    )


def test_canonical_encoding_ignores_mapping_order_and_separates_digest_scopes() -> None:
    """A codec that preserves dict insertion order would make equivalent research diverge."""
    codec = SnapshotCodecV2()
    left = _payload(run_payload=MappingProxyType({"a": 1, "b": 2}))
    right = _payload(run_payload=MappingProxyType({"b": 2, "a": 1}))

    assert codec.encode_research_projection(left) == codec.encode_research_projection(right)
    assert codec.research_digest(left) == codec.research_digest(right)
    assert codec.integrity_digest(_snapshot(left, run_id="run-a")) != codec.integrity_digest(
        _snapshot(right, run_id="run-b")
    )


def test_canonical_encoding_has_one_form_for_datetime_decimal_enum_and_model() -> None:
    """Changing normalization must be observable in the persisted canonical bytes."""
    codec = SnapshotCodecV2()
    utc = datetime(2026, 9, 1, 8, 30, tzinfo=timezone.utc)
    offset = utc.astimezone(timezone(timedelta(hours=8)))
    left = _payload(
        run_payload=MappingProxyType(
            {"when": utc, "amount": Decimal("1.2300"), "state": _State.WAIT, "model": _ExampleModel(name="x", amount=Decimal("2.0"))}
        )
    )
    right = _payload(
        run_payload=MappingProxyType(
            {"model": _ExampleModel(name="x", amount=Decimal("2")), "state": _State.WAIT, "amount": Decimal("1.23"), "when": offset}
        )
    )

    assert codec.encode_research_projection(left) == codec.encode_research_projection(right)


@pytest.mark.parametrize(
"payload",
[
    MappingProxyType({1: "not-a-string-key"}),
    MappingProxyType({"value": float("nan")}),
    MappingProxyType({"value": float("inf")}),
    object(),
],
)
def test_canonical_encoding_fails_closed_for_unrepresentable_values(payload: object) -> None:
    """Relaxing the codec to stringify invalid values would corrupt the audit hash."""
    codec = SnapshotCodecV2()
    with pytest.raises(SnapshotCodecError):
        codec.encode_research_projection(_payload(run_payload=payload))


def test_decoder_registry_rejects_unknown_schema_type_and_import_paths() -> None:
    """Allowing an unregistered decoder would turn snapshot input into executable configuration."""
    registry = ArtifactDecoderRegistry()
    with pytest.raises(SnapshotCodecError, match="not registered"):
        registry.decode(
            artifact_id="decision.record",
            schema_version="9.9",
            type_id="os.system",
            payload={"command": "not executed"},
        )

    registry.register(
        artifact_id="decision.record",
        schema_version="2.0",
        type_id="decision-record-v2",
        decoder=lambda value: value,
    )
    with pytest.raises(SnapshotCodecError, match="not registered"):
        registry.decode(
            artifact_id="decision.record",
            schema_version="2.0",
            type_id="importlib:import_module",
            payload={},
        )


def test_canonical_encoding_separates_reserved_key_mappings_from_typed_values() -> None:
    codec = SnapshotCodecV2()
    ordinary_mapping = MappingProxyType({"$type": "integer", "value": "1"})

    assert codec.encode_value(ordinary_mapping) != codec.encode_value(1)
