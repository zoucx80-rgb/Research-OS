from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from research_os.release.historical_executor import (
    HistoricalReplayError,
    HistoricalReplayExecutor,
)
from research_os.release.replays import REPLAY_REGISTRY, ReplayProfile


_EXPECTED = {
    "field-v1.5.08": ("f7863e0b0aeb657ac19b0a63761788d40118e6bf", "1.5.8"),
    "field-v1.5.09": ("a3e82b3cc80b871b559ac9f5cd29e18e97b8e98d", "1.5.9"),
    "field-v1.5.10": ("05a3ba99edc02ac93ee9fdf1130485da7e6fa8ab", "1.5.10"),
    "field-v1.5.11": ("5067e4decb673a39cb96085e34a3a555fe24d58e", "1.5.11"),
    "field-v1.5.12": ("72ab06c619678b35c31cf7edef7547849e803d16", "1.5.12"),
}


def test_historical_replay_profiles_are_frozen_and_commit_addressed() -> None:
    assert set(REPLAY_REGISTRY) == set(_EXPECTED)
    for profile_id, profile in REPLAY_REGISTRY.items():
        sha, version = _EXPECTED[profile_id]
        assert profile.frozen is True
        assert profile.source_commit_sha == sha
        assert re.fullmatch(r"[0-9a-f]{40}", profile.source_commit_sha)
        assert profile.expected_product_version == version
        assert profile.expected_core_api_version == "1.0"
        assert profile.runner_script.startswith("scripts/render_field_acceptance_v1_5_")
        assert profile.fixture_dir.startswith("tests/fixtures/field_acceptance/v1_5_")


def test_v1_5_08_declares_only_the_bounded_cleanup_compatibility() -> None:
    assert (
        REPLAY_REGISTRY["field-v1.5.08"].compatibility_profile
        == "playwright-cleanup-v1.5.08"
    )
    assert all(
        profile.compatibility_profile is None
        for profile_id, profile in REPLAY_REGISTRY.items()
        if profile_id != "field-v1.5.08"
    )


def test_v1_5_08_cleanup_compatibility_requires_exact_historical_blob() -> None:
    profile = REPLAY_REGISTRY["field-v1.5.08"]
    executor = HistoricalReplayExecutor(Path.cwd())

    assert executor._resolve_compatibility_action(
        profile,
        source_blob_sha="4ba9ba1fefacb9776f46ad6d442480e6221594bd",
    ) == "playwright-cleanup-v1.5.08"

    with pytest.raises(HistoricalReplayError, match="source fingerprint mismatch"):
        executor._resolve_compatibility_action(profile, source_blob_sha="0" * 40)


def test_executor_source_requires_detached_worktree_venv_and_sanitized_pythonpath() -> None:
    source = inspect.getsource(HistoricalReplayExecutor)

    assert '"worktree",\n                "add",\n                "--detach"' in source
    assert '"-m", "venv"' in source
    assert 'environment.pop("PYTHONPATH", None)' in source
    assert '"PYTHONNOUSERSITE": "1"' in source
    assert '"GITHUB_SHA": source_commit_sha' in source
    assert "profile.source_commit_sha" in source
    assert "_verify_import_identity" in source
    assert "research_os.runtime" not in source
    assert "research_os.reporting" not in source


def test_executor_stages_historical_outputs_before_publishing() -> None:
    source = inspect.getsource(HistoricalReplayExecutor.execute)

    assert 'staging_output = temporary_root / "output"' in source
    assert "_publish_staged_output" in source
    assert "str(staging_output)" in source


def test_isolated_environment_binds_historical_sha_and_blocks_user_imports(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/current/source")
    environment = HistoricalReplayExecutor._isolated_environment(
        python="/isolated/bin/python",
        venv=tmp_path / "venv",
        source_commit_sha="a" * 40,
    )

    assert "PYTHONPATH" not in environment
    assert environment["GITHUB_SHA"] == "a" * 40
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert environment["VIRTUAL_ENV"] == str(tmp_path / "venv")
    assert environment["PATH"].startswith("/isolated/bin")


def test_executor_fails_closed_for_unfrozen_profile(tmp_path: Path) -> None:
    profile = ReplayProfile(
        profile_id="mutable",
        source_commit_sha="0" * 40,
        expected_product_version="1.5.12",
        expected_core_api_version="1.0",
        runner_script="scripts/x.py",
        fixture_dir="tests/x",
        output_dir="build/x",
        artifact_name="x",
        frozen=False,
    )

    with pytest.raises(HistoricalReplayError, match="must be frozen"):
        HistoricalReplayExecutor(tmp_path).execute(profile)
