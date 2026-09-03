from datetime import datetime, timezone
import json
from types import MappingProxyType

from hypothesis import given, strategies as st
import rfc8785

from research_os.application.result import RunVersionSet
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.snapshots.codec import SnapshotCodecV2
from research_os.snapshots.models import ResearchSnapshotPayloadV2, SnapshotArtifactV2


_TEXT = st.text(
    alphabet=st.characters(exclude_categories=("Cs",)),
    max_size=12,
)
_JSON_VALUES = st.recursive(
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | _TEXT,
    lambda children: (
        st.lists(children, max_size=4)
        | st.dictionaries(
            st.sampled_from(("$type", "$ros_type", "value", "items", "ordinary")),
            children,
            max_size=5,
        )
    ),
    max_leaves=20,
)


def _payload(items: tuple[tuple[str, int], ...]) -> ResearchSnapshotPayloadV2:
    return ResearchSnapshotPayloadV2(
        company=CompanyRef(company_id="001287.SZ"),
        decision_ts=datetime(2026, 9, 1, tzinfo=timezone.utc),
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
        artifacts=(
            SnapshotArtifactV2(
                artifact_id="decision.record",
                schema_version="2.0",
                type_id="decision-record-v2",
                producer_ids=("decision",),
                payload=MappingProxyType(dict(items)),
            ),
        ),
    )


@given(
    st.dictionaries(st.text(min_size=1, max_size=8), st.integers()).map(
        lambda value: tuple(value.items())
    )
)
def test_research_projection_is_deterministic_across_input_mapping_order(
    items: tuple[tuple[str, int], ...],
) -> None:
    """A mapping-order-sensitive JCS projection would make equivalent snapshots non-reproducible."""
    codec = SnapshotCodecV2()
    forward = _payload(items)
    backward = _payload(tuple(reversed(items)))

    assert codec.encode_research_projection(forward) == codec.encode_research_projection(backward)
    assert codec.research_digest(forward) == codec.research_digest(backward)


@given(
    st.dictionaries(st.text(min_size=1, max_size=8), st.integers()).map(
        lambda value: tuple(value.items())
    )
)
def test_research_projection_round_trips_to_the_same_jcs_bytes(
    items: tuple[tuple[str, int], ...],
) -> None:
    """A noncanonical encoder would change bytes after JSON parse and JCS re-encoding."""
    encoded = SnapshotCodecV2().encode_research_projection(_payload(items))

    assert rfc8785.dumps(json.loads(encoded)) == encoded


@given(_JSON_VALUES)
def test_structured_value_codec_round_trips_arbitrary_nested_json_without_tag_collisions(
    value: object,
) -> None:
    codec = SnapshotCodecV2()

    encoded = codec.encode_value(value)

    assert codec.decode_value(encoded) == value
    assert codec.encode_value(codec.decode_value(encoded)) == encoded
