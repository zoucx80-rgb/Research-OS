from datetime import datetime, timedelta, timezone
from types import MappingProxyType

import pytest
from pydantic import ValidationError
from pydantic import BaseModel, ConfigDict

from research_os.application.result import ComponentFingerprint, RunVersionSet
from research_os.contracts.artifacts import artifact_value_fingerprint
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.snapshots.models import (
    ArtifactFingerprint,
    SnapshotArtifactV2,
    ResearchSnapshotPayloadV2,
    ResearchSnapshotV2,
)


def _versions() -> RunVersionSet:
    return RunVersionSet(
        research_os_version="1.6.0",
        core_api_version="2.0",
        plugin_api_version="2.0",
        snapshot_schema_version="2.0",
        http_api_version="v1",
    )


def _baseline() -> BaselineFingerprint:
    return BaselineFingerprint(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        commit_sha="a" * 40,
        research_os_version="1.6.0",
        core_api_version="2.0",
    )


def _payload() -> ResearchSnapshotPayloadV2:
    return ResearchSnapshotPayloadV2(
        company=CompanyRef(company_id="001287.SZ"),
        decision_ts=datetime(2026, 9, 1, tzinfo=timezone.utc),
        baseline=_baseline(),
        versions=_versions(),
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
            SnapshotArtifactV2(
                artifact_id="decision.record",
                schema_version="2.0",
                type_id="decision-record-v2",
                producer_ids=("decision",),
                payload=MappingProxyType({"state": "WAIT"}),
            ),
        ),
    )


def _snapshot_with_fingerprints(
    payload: ResearchSnapshotPayloadV2,
    fingerprints: tuple[ArtifactFingerprint, ...],
) -> ResearchSnapshotV2:
    return ResearchSnapshotV2(
        snapshot_id="snapshot-fingerprint",
        schema_version="2.0",
        codec_version="jcs-1",
        hash_algorithm="sha256",
        run_id="run-fingerprint",
        company_id=payload.company.company_id,
        decision_ts=payload.decision_ts,
        created_at=payload.decision_ts,
        baseline=payload.baseline,
        versions=payload.versions,
        component_fingerprints=payload.component_fingerprints,
        artifact_fingerprints=fingerprints,
        payload=payload,
        payload_hash="e" * 64,
    )


def test_snapshot_requires_explicit_versions_and_all_audit_identity_fields() -> None:
    """Removing an audit-bound snapshot identity field must fail validation."""
    payload = _payload()
    with pytest.raises(ValidationError):
        ResearchSnapshotV2(
            snapshot_id="snap-1",
            run_id="run-1",
            company_id="001287.SZ",
            decision_ts=datetime(2026, 9, 1, tzinfo=timezone.utc),
            created_at=datetime(2026, 9, 1, tzinfo=timezone.utc),
            baseline=_baseline(),
            versions=_versions(),
            component_fingerprints=(),
            artifact_fingerprints=(),
            payload=payload,
            payload_hash="c" * 64,
        )


def test_snapshot_rejects_non_utc_timestamps() -> None:
    """Accepting non-UTC timestamps would make the byte representation ambiguous."""
    with pytest.raises(ValidationError, match="UTC"):
        ResearchSnapshotPayloadV2(
            company=CompanyRef(company_id="001287.SZ"),
            decision_ts=datetime(2026, 9, 1, tzinfo=timezone(timedelta(hours=8))),
            baseline=_baseline(),
            versions=_versions(),
            component_fingerprints=(),
            artifacts=(),
        )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_snapshot_rejects_non_finite_artifact_payloads(value: float) -> None:
    """Changing finite-value validation must be caught before a nonportable hash is written."""
    with pytest.raises(ValidationError, match="finite"):
        SnapshotArtifactV2(
            artifact_id="decision.record",
            schema_version="2.0",
            type_id="decision-record-v2",
            producer_ids=("decision",),
            payload=MappingProxyType({"value": value}),
        )


def test_snapshot_requires_schema_bound_artifacts() -> None:
    """An artifact without schema/type identity must not enter a Schema 2.0 snapshot."""
    with pytest.raises(ValidationError):
        SnapshotArtifactV2(
            artifact_id="decision.record",
            schema_version="",
            type_id="",
            producer_ids=("decision",),
            payload=MappingProxyType({"state": "WAIT"}),
        )


def test_snapshot_rejects_mutable_artifact_payloads() -> None:
    """Mutating a retained list or dict after construction must not alter a frozen snapshot."""
    with pytest.raises(ValidationError, match="immutable"):
        SnapshotArtifactV2(
            artifact_id="decision.record",
            schema_version="2.0",
            type_id="decision-record-v2",
            producer_ids=("decision",),
            payload={"states": ["WAIT"]},
        )


def test_snapshot_accepts_frozen_pydantic_artifact_values_only() -> None:
    """Artifact models are valid immutable values only when their contract is frozen."""

    class FrozenValue(BaseModel):
        model_config = ConfigDict(frozen=True)

        amount: int
        details: dict[str, list[int]]

    class MutableValue(BaseModel):
        amount: int

    artifact = SnapshotArtifactV2(
        artifact_id="decision.record",
        schema_version="2.0",
        type_id="decision-record-v2",
        producer_ids=("decision",),
        payload=FrozenValue(amount=1, details={"items": [1]}),
    )

    exposed = artifact.payload
    assert isinstance(exposed, FrozenValue)
    exposed.details["items"].append(2)
    assert artifact.payload == FrozenValue(amount=1, details={"items": [1]})
    with pytest.raises(ValidationError, match="immutable"):
        SnapshotArtifactV2(
            artifact_id="decision.record",
            schema_version="2.0",
            type_id="decision-record-v2",
            producer_ids=("decision",),
            payload=MutableValue(amount=1),
        )


def test_snapshot_defensively_copies_nested_mutable_assumption_values() -> None:
    class FrozenAssumption(BaseModel):
        model_config = ConfigDict(frozen=True)

        cases: dict[str, list[int]]

    original = FrozenAssumption(cases={"base": [1]})
    base = _payload()
    payload = ResearchSnapshotPayloadV2(
        company=base.company,
        decision_ts=base.decision_ts,
        baseline=base.baseline,
        versions=base.versions,
        component_fingerprints=base.component_fingerprints,
        artifacts=base.artifacts,
        input_assumptions=(original,),
    )

    original.cases["base"].append(2)
    exposed = payload.input_assumptions[0]
    assert isinstance(exposed, FrozenAssumption)
    exposed.cases["base"].append(3)

    assert payload.input_assumptions == (FrozenAssumption(cases={"base": [1]}),)


def test_artifact_fingerprint_binds_schema_and_value_hash() -> None:
    """Dropping a schema or content hash must invalidate the artifact fingerprint."""
    with pytest.raises(ValidationError):
        ArtifactFingerprint(
            artifact_id="decision.record",
            schema_version="",
            type_id="decision-record-v2",
            value_fingerprint="d" * 64,
        )


def test_snapshot_requires_one_content_bound_fingerprint_per_artifact() -> None:
    payload = _payload()
    with pytest.raises(ValidationError, match="fingerprint"):
        _snapshot_with_fingerprints(payload, ())


def test_snapshot_rejects_extra_duplicate_and_content_mismatched_fingerprints() -> None:
    payload = _payload()
    artifact = payload.artifacts[0]
    valid = ArtifactFingerprint(
        artifact_id=artifact.artifact_id,
        schema_version=artifact.schema_version,
        type_id=artifact.type_id,
        value_fingerprint=artifact_value_fingerprint(artifact.payload),
    )
    extra = ArtifactFingerprint(
        artifact_id="extra",
        schema_version="2.0",
        type_id="extra-v2",
        value_fingerprint="f" * 64,
    )
    mismatch = valid.model_copy(update={"value_fingerprint": "0" * 64})

    for fingerprints in ((valid, extra), (valid, valid), (mismatch,)):
        with pytest.raises(ValidationError, match="fingerprint"):
            _snapshot_with_fingerprints(payload, fingerprints)


def test_snapshot_rejects_duplicate_artifact_schema_identities() -> None:
    payload = _payload()
    with pytest.raises(ValidationError, match="unique schema identities"):
        ResearchSnapshotPayloadV2(
            company=payload.company,
            decision_ts=payload.decision_ts,
            baseline=payload.baseline,
            versions=payload.versions,
            component_fingerprints=payload.component_fingerprints,
            artifacts=(payload.artifacts[0], payload.artifacts[0]),
        )
