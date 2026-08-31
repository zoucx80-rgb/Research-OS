from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .manifest import ReleaseManifest


@dataclass(frozen=True)
class FieldReplayProfile:
    profile_id: str
    runner_script: str
    fixture_dir: str
    output_dir: str
    artifact_name: str
    frozen: bool


REPLAY_REGISTRY: Mapping[str, FieldReplayProfile] = {
    "field-v1.5.08": FieldReplayProfile(
        profile_id="field-v1.5.08",
        runner_script="scripts/render_field_acceptance_v1_5_08.py",
        fixture_dir="tests/fixtures/field_acceptance/v1_5_08",
        output_dir="build/field-acceptance-v1.5.08",
        artifact_name="v1.5.08-field-acceptance",
        frozen=True,
    ),
    "field-v1.5.09": FieldReplayProfile(
        profile_id="field-v1.5.09",
        runner_script="scripts/render_field_acceptance_v1_5_09.py",
        fixture_dir="tests/fixtures/field_acceptance/v1_5_09",
        output_dir="build/field-acceptance-v1.5.09",
        artifact_name="v1.5.09-field-acceptance",
        frozen=True,
    ),
    "field-v1.5.10": FieldReplayProfile(
        profile_id="field-v1.5.10",
        runner_script="scripts/render_field_acceptance_v1_5_10.py",
        fixture_dir="tests/fixtures/field_acceptance/v1_5_10",
        output_dir="build/field-acceptance-v1.5.10",
        artifact_name="v1.5.10-field-acceptance",
        frozen=True,
    ),
    "field-v1.5.11": FieldReplayProfile(
        profile_id="field-v1.5.11",
        runner_script="scripts/render_field_acceptance_v1_5_11.py",
        fixture_dir="tests/fixtures/field_acceptance/v1_5_11",
        output_dir="build/field-acceptance-v1.5.11",
        artifact_name="v1.5.11-field-acceptance",
        frozen=False,
    ),
}


def resolve_replay_profiles(manifest: ReleaseManifest) -> tuple[FieldReplayProfile, ...]:
    profiles: list[FieldReplayProfile] = []
    seen: set[str] = set()
    for profile_id in manifest.field_replay_profiles:
        if profile_id in seen:
            raise ValueError(f"duplicate field replay profile: {profile_id}")
        seen.add(profile_id)
        try:
            profiles.append(REPLAY_REGISTRY[profile_id])
        except KeyError as exc:
            raise ValueError(f"unknown field replay profile: {profile_id}") from exc
    return tuple(profiles)
