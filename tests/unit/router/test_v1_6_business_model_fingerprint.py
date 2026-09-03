from research_os.contracts.artifacts import artifact_value_fingerprint
from research_os.router.models import BusinessModelProfile
from research_os.snapshots.codec import SnapshotCodecV2


def test_business_model_defaults_are_canonical_before_snapshot_round_trip() -> None:
    profile = BusinessModelProfile(
        company_id="synthetic:fingerprint",
        primary_model="unknown",
        classification_status="INSUFFICIENT_EVIDENCE",
        classification_reason="NO_USABLE_BUSINESS_MODEL_EVIDENCE",
        router_version="router@2.0.0",
    )

    assert type(profile.rule_match_score) is float
    assert type(profile.usable_evidence_coverage) is float
    assert type(profile.ambiguity) is float

    codec = SnapshotCodecV2()
    decoded = codec.decode_value(codec.encode_value(profile))
    restored = BusinessModelProfile.model_validate(decoded)

    assert restored == profile
    assert artifact_value_fingerprint(restored) == artifact_value_fingerprint(profile)
