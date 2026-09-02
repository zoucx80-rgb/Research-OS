from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum

import pytest

from research_os.contracts.artifacts import (
    ArtifactCatalog,
    ArtifactDefinition,
    ArtifactKey,
    ArtifactMode,
    ArtifactStore,
    ArtifactWrite,
)
from research_os.contracts.errors import (
    ArtifactDefinitionError,
    ArtifactNotFoundError,
    ArtifactProviderConflictError,
    ArtifactTypeMismatchError,
)
from research_os.contracts.evidence import EvidenceRef


def _ref(evidence_id: str, revision: int = 1) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=evidence_id,
        revision=revision,
        content_fingerprint=f"{'0' * 63}{revision}",
    )


def test_artifact_key_rejects_empty_identity_and_non_type_value_type():
    with pytest.raises(ArtifactDefinitionError, match="artifact_id"):
        ArtifactKey("", "1.0", dict)
    with pytest.raises(ArtifactDefinitionError, match="schema_version"):
        ArtifactKey("example.payload", " ", dict)
    with pytest.raises(ArtifactDefinitionError, match="value_type"):
        ArtifactKey("example.payload", "1.0", "dict")  # type: ignore[arg-type]


def test_artifact_definition_rejects_untyped_mode():
    with pytest.raises(ArtifactDefinitionError, match="ArtifactMode"):
        ArtifactDefinition(
            key=ArtifactKey("example.payload", "1.0", dict),
            mode="exclusive",  # type: ignore[arg-type]
        )


def test_catalog_rejects_duplicate_definition_and_collection_without_reducer():
    key = ArtifactKey("example.items", "1.0", tuple)
    catalog = ArtifactCatalog()

    with pytest.raises(ArtifactDefinitionError, match="reducer"):
        catalog.register(ArtifactDefinition(key=key, mode=ArtifactMode.COLLECTION))

    catalog.register(
        ArtifactDefinition(
            key=key,
            mode=ArtifactMode.COLLECTION,
            reducer_id="tuple.concat.v1",
        ),
        reducer=lambda values: tuple(item for value in values for item in value),
    )
    with pytest.raises(ArtifactDefinitionError, match="duplicate artifact definition"):
        catalog.register(
            ArtifactDefinition(
                key=ArtifactKey("example.items", "1.0", tuple),
                mode=ArtifactMode.COLLECTION,
                reducer_id="tuple.concat.v1",
            ),
            reducer=lambda values: (),
        )


def test_store_rejects_wrong_value_type_and_second_exclusive_provider():
    key = ArtifactKey("example.payload", "1.0", dict)
    catalog = ArtifactCatalog()
    catalog.register(ArtifactDefinition(key=key, mode=ArtifactMode.EXCLUSIVE))
    store = ArtifactStore(catalog)

    with pytest.raises(ArtifactTypeMismatchError, match="example.payload"):
        store.write(ArtifactWrite(key=key, value="wrong", producer_id="producer:a"))

    store.write(ArtifactWrite(key=key, value={"value": 1}, producer_id="producer:a"))
    with pytest.raises(ArtifactProviderConflictError, match="producer:a.*producer:b"):
        store.write(ArtifactWrite(key=key, value={"value": 2}, producer_id="producer:b"))


def test_collection_reduction_is_deterministic_and_preserves_lineage():
    key = ArtifactKey("example.items", "1.0", tuple)
    catalog = ArtifactCatalog()
    catalog.register(
        ArtifactDefinition(
            key=key,
            mode=ArtifactMode.COLLECTION,
            reducer_id="tuple.concat.v1",
        ),
        reducer=lambda values: tuple(item for value in values for item in value),
    )

    def build(writes):
        store = ArtifactStore(catalog)
        for write in writes:
            store.write(write)
        return store.freeze()

    first = ArtifactWrite(
        key=key,
        value=("a",),
        producer_id="producer:a",
        evidence_refs=(_ref("ev:2"), _ref("ev:1")),
    )
    second = ArtifactWrite(
        key=key,
        value=("b",),
        producer_id="producer:b",
        evidence_refs=(_ref("ev:1"), _ref("ev:3")),
    )

    forward = build([first, second])
    reverse = build([second, first])

    assert forward.require(key) == reverse.require(key) == ("a", "b")
    assert forward.envelope(key).producer_ids == ("producer:a", "producer:b")
    assert forward.envelope(key).evidence_refs == (
        _ref("ev:1"),
        _ref("ev:2"),
        _ref("ev:3"),
    )


def test_artifact_write_rejects_conflicting_revisions_for_one_evidence_id():
    key = ArtifactKey("example.payload", "1.0", tuple)

    with pytest.raises(ArtifactProviderConflictError, match="conflicting revisions.*ev:1"):
        ArtifactWrite(
            key=key,
            value=("ambiguous",),
            producer_id="producer:a",
            evidence_refs=(
                _ref("ev:1", revision=1),
                _ref("ev:1", revision=2),
            ),
        )


def test_artifact_store_rejects_conflicting_revisions_across_providers():
    key = ArtifactKey("example.items", "1.0", tuple)
    catalog = ArtifactCatalog()
    catalog.register(
        ArtifactDefinition(
            key=key,
            mode=ArtifactMode.COLLECTION,
            reducer_id="tuple.concat.v1",
        ),
        reducer=lambda values: tuple(item for value in values for item in value),
    )
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            key=key,
            value=("historical",),
            producer_id="producer:a",
            evidence_refs=(_ref("ev:1", revision=1),),
        )
    )
    store.write(
        ArtifactWrite(
            key=key,
            value=("restated",),
            producer_id="producer:b",
            evidence_refs=(_ref("ev:1", revision=2),),
        )
    )

    with pytest.raises(ArtifactProviderConflictError, match="conflicting revisions.*ev:1"):
        store.freeze()


def test_snapshot_uses_typed_keys_and_missing_require_fails_closed():
    key = ArtifactKey("example.payload", "1.0", dict)
    missing = ArtifactKey("example.missing", "1.0", dict)
    catalog = ArtifactCatalog()
    catalog.register(ArtifactDefinition(key=key, mode=ArtifactMode.EXCLUSIVE))
    catalog.register(ArtifactDefinition(key=missing, mode=ArtifactMode.EXCLUSIVE))
    store = ArtifactStore(catalog)
    store.write(ArtifactWrite(key=key, value={"value": 1}, producer_id="producer:a"))
    snapshot = store.freeze()

    assert snapshot.get(key) == {"value": 1}
    assert snapshot.get(missing) is None
    with pytest.raises(ArtifactNotFoundError, match="example.missing"):
        snapshot.require(missing)
    with pytest.raises(AttributeError, match="immutable"):
        snapshot._envelopes = {}  # type: ignore[misc]


class _FingerprintStatus(StrEnum):
    PASS = "PASS"


def _fingerprint_for(value: dict) -> str:
    key = ArtifactKey("example.fingerprint", "1.0", dict)
    catalog = ArtifactCatalog()
    catalog.register(ArtifactDefinition(key=key, mode=ArtifactMode.EXCLUSIVE))
    store = ArtifactStore(catalog)
    store.write(ArtifactWrite(key=key, value=value, producer_id="producer:a"))
    envelope = store.freeze().envelope(key)
    assert envelope is not None
    return envelope.value_fingerprint


def test_artifact_value_fingerprint_uses_a_deterministic_canonical_projection():
    instant = datetime(2026, 9, 1, 8, 30, tzinfo=timezone.utc)
    equivalent_instant = instant.astimezone(timezone(timedelta(hours=8)))

    forward = {
        "decimal": Decimal("123.4500"),
        "instant": instant,
        "items": frozenset(("beta", "alpha")),
        "status": _FingerprintStatus.PASS,
    }
    reordered = {
        "status": _FingerprintStatus.PASS,
        "items": frozenset(("alpha", "beta")),
        "instant": equivalent_instant,
        "decimal": Decimal("123.4500"),
    }

    fingerprint = _fingerprint_for(forward)

    assert fingerprint == _fingerprint_for(reordered)
    assert len(fingerprint) == 64
    assert set(fingerprint) <= set("0123456789abcdef")


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), float("-inf")])
def test_artifact_value_fingerprint_rejects_non_finite_floats(invalid: float):
    with pytest.raises(ArtifactTypeMismatchError, match="finite"):
        _fingerprint_for({"value": invalid})


def test_artifact_value_fingerprint_rejects_naive_datetimes_and_unknown_values():
    with pytest.raises(ArtifactTypeMismatchError, match="timezone-aware"):
        _fingerprint_for({"value": datetime(2026, 9, 1)})

    with pytest.raises(ArtifactTypeMismatchError, match="canonical artifact value"):
        _fingerprint_for({"value": object()})


def test_artifact_value_fingerprint_rejects_invalid_mappings_and_cycles():
    with pytest.raises(ArtifactTypeMismatchError, match="string mapping keys"):
        _fingerprint_for({"value": {1: "not a JSON object key"}})

    cyclic: dict[str, object] = {}
    cyclic["self"] = cyclic
    with pytest.raises(ArtifactTypeMismatchError, match="canonical artifact value"):
        _fingerprint_for(cyclic)
