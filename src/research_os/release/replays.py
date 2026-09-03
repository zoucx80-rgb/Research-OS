from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .manifest import ReleaseManifest


@dataclass(frozen=True, slots=True)
class ReplayProfile:
    profile_id: str
    source_commit_sha: str
    expected_product_version: str
    expected_core_api_version: str
    runner_script: str
    fixture_dir: str
    output_dir: str
    artifact_name: str
    frozen: bool = True
    compatibility_profile: str | None = None


# Compatibility name for release-governance code that predates the M4 executor.
# It does not represent a v1 runtime adapter; profiles are immutable metadata only.
FieldReplayProfile = ReplayProfile


REPLAY_REGISTRY: Mapping[str, ReplayProfile] = MappingProxyType(
    {
        "field-v1.5.08": ReplayProfile(
            profile_id="field-v1.5.08",
            source_commit_sha="f7863e0b0aeb657ac19b0a63761788d40118e6bf",
            expected_product_version="1.5.8",
            expected_core_api_version="1.0",
            runner_script="scripts/render_field_acceptance_v1_5_08.py",
            fixture_dir="tests/fixtures/field_acceptance/v1_5_08",
            output_dir="build/historical-replay/v1.5.08",
            artifact_name="v1.5.08-historical-replay",
            compatibility_profile="playwright-cleanup-v1.5.08",
        ),
        "field-v1.5.09": ReplayProfile(
            profile_id="field-v1.5.09",
            source_commit_sha="a3e82b3cc80b871b559ac9f5cd29e18e97b8e98d",
            expected_product_version="1.5.9",
            expected_core_api_version="1.0",
            runner_script="scripts/render_field_acceptance_v1_5_09.py",
            fixture_dir="tests/fixtures/field_acceptance/v1_5_09",
            output_dir="build/historical-replay/v1.5.09",
            artifact_name="v1.5.09-historical-replay",
        ),
        "field-v1.5.10": ReplayProfile(
            profile_id="field-v1.5.10",
            source_commit_sha="05a3ba99edc02ac93ee9fdf1130485da7e6fa8ab",
            expected_product_version="1.5.10",
            expected_core_api_version="1.0",
            runner_script="scripts/render_field_acceptance_v1_5_10.py",
            fixture_dir="tests/fixtures/field_acceptance/v1_5_10",
            output_dir="build/historical-replay/v1.5.10",
            artifact_name="v1.5.10-historical-replay",
        ),
        "field-v1.5.11": ReplayProfile(
            profile_id="field-v1.5.11",
            source_commit_sha="5067e4decb673a39cb96085e34a3a555fe24d58e",
            expected_product_version="1.5.11",
            expected_core_api_version="1.0",
            runner_script="scripts/render_field_acceptance_v1_5_11.py",
            fixture_dir="tests/fixtures/field_acceptance/v1_5_11",
            output_dir="build/historical-replay/v1.5.11",
            artifact_name="v1.5.11-historical-replay",
        ),
        "field-v1.5.12": ReplayProfile(
            profile_id="field-v1.5.12",
            source_commit_sha="72ab06c619678b35c31cf7edef7547849e803d16",
            expected_product_version="1.5.12",
            expected_core_api_version="1.0",
            runner_script="scripts/render_field_acceptance_v1_5_12.py",
            fixture_dir="tests/fixtures/field_acceptance/v1_5_12",
            output_dir="build/historical-replay/v1.5.12",
            artifact_name="v1.5.12-historical-replay",
        ),
    }
)


def resolve_replay_profiles(manifest: ReleaseManifest) -> tuple[ReplayProfile, ...]:
    profiles: list[ReplayProfile] = []
    seen: set[str] = set()
    for profile_id in manifest.field_replay_profiles:
        if profile_id in seen:
            raise ValueError(f"duplicate field replay profile: {profile_id}")
        seen.add(profile_id)
        try:
            profile = REPLAY_REGISTRY[profile_id]
        except KeyError as exc:
            raise ValueError(f"unknown field replay profile: {profile_id}") from exc
        if not profile.frozen:
            raise ValueError(f"historical replay profile is not frozen: {profile_id}")
        profiles.append(profile)
    return tuple(profiles)
