from __future__ import annotations

from hypothesis import given, strategies as st

from research_os.contracts.artifacts import (
    ArtifactCatalog,
    ArtifactDefinition,
    ArtifactKey,
    ArtifactMode,
    ArtifactStore,
    ArtifactWrite,
)


@given(st.lists(st.integers(), max_size=20))
def test_snapshot_is_unchanged_when_input_or_returned_values_are_mutated(values):
    key = ArtifactKey("example.mutable", "1.0", dict)
    catalog = ArtifactCatalog()
    catalog.register(ArtifactDefinition(key=key, mode=ArtifactMode.EXCLUSIVE))
    source = {"nested": list(values)}
    store = ArtifactStore(catalog)
    store.write(ArtifactWrite(key=key, value=source, producer_id="producer:a"))
    snapshot = store.freeze()

    source["nested"].append(3)
    returned = snapshot.require(key)
    returned["nested"].append(4)

    assert snapshot.require(key) == {"nested": values}


@given(st.permutations(("a", "b", "c", "d")))
def test_collection_snapshot_is_stable_for_every_registration_order(provider_order):
    key = ArtifactKey("example.ordered", "1.0", tuple)
    catalog = ArtifactCatalog()
    catalog.register(
        ArtifactDefinition(
            key=key,
            mode=ArtifactMode.COLLECTION,
            reducer_id="tuple.concat.v1",
        ),
        reducer=lambda values: tuple(item for value in values for item in value),
    )
    writes = {
        provider_id: ArtifactWrite(
            key=key,
            value=(provider_id,),
            producer_id=f"producer:{provider_id}",
        )
        for provider_id in provider_order
    }
    store = ArtifactStore(catalog)
    for provider_id in provider_order:
        store.write(writes[provider_id])

    assert store.freeze().require(key) == ("a", "b", "c", "d")


@given(st.dictionaries(st.text(min_size=1), st.integers(), max_size=20))
def test_value_fingerprint_is_stable_for_mapping_insertion_order(values):
    key = ArtifactKey("example.mapping", "1.0", dict)
    catalog = ArtifactCatalog()
    catalog.register(ArtifactDefinition(key=key, mode=ArtifactMode.EXCLUSIVE))

    def fingerprint(items):
        store = ArtifactStore(catalog)
        store.write(
            ArtifactWrite(
                key=key,
                value=dict(items),
                producer_id="producer:a",
            )
        )
        envelope = store.freeze().envelope(key)
        assert envelope is not None
        return envelope.value_fingerprint

    items = list(values.items())
    assert fingerprint(items) == fingerprint(reversed(items))
