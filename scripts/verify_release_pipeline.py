#!/usr/bin/env python
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_os.release.gate import evaluate_release_gate
from research_os.release.historical_executor import HistoricalReplayExecutor
from research_os.release.manifest import CURRENT_RELEASE
from research_os.release.replays import resolve_replay_profiles
from research_os.release.verification import resolve_release_checks


def _run(stage: str, command: list[str]) -> None:
    print(f"\n=== {stage} ===", flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def _verify_metadata() -> None:
    expected = CURRENT_RELEASE.to_public_metadata()
    actual = json.loads((ROOT / "research_os_version.json").read_text(encoding="utf-8"))
    if actual != expected:
        print("release metadata does not match CURRENT_RELEASE", file=sys.stderr)
        raise SystemExit(1)
    print("release metadata: PASS")


def _run_release_checks() -> dict[str, bool]:
    checks = resolve_release_checks(CURRENT_RELEASE)
    _run(
        "release verification packs",
        [sys.executable, "-m", "pytest", "-q", *checks.values()],
    )
    return {check_id: True for check_id in checks}


def _run_current_field_acceptance() -> None:
    commit_sha = os.environ.get("GITHUB_SHA") or subprocess.check_output(
        ("git", "-C", str(ROOT), "rev-parse", "HEAD"), text=True
    ).strip()
    _run(
        "current v1.6.0 field acceptance",
        [
            sys.executable,
            "scripts/render_field_acceptance_v1_6_0.py",
            "--input-dir",
            "tests/fixtures/field_acceptance/v1_6_0",
            "--output-dir",
            "build/field-acceptance-v1.6.0",
            "--repository-root",
            ".",
            "--commit-sha",
            commit_sha,
        ],
    )


def _run_field_replays() -> None:
    executor = HistoricalReplayExecutor(ROOT)
    for profile in resolve_replay_profiles(CURRENT_RELEASE):
        print(f"\n=== historical replay {profile.profile_id} ===", flush=True)
        result = executor.execute(profile)
        print(
            f"{profile.profile_id}: {result.source_commit_sha} "
            f"v{result.product_version} -> {result.output_dir}",
            flush=True,
        )


def main() -> None:
    print(
        f"Research OS v{CURRENT_RELEASE.version} release verification pipeline",
        flush=True,
    )
    _verify_metadata()
    status = _run_release_checks()
    _run_current_field_acceptance()
    _run_field_replays()
    _run("full pytest suite", [sys.executable, "-m", "pytest", "-q"])
    _run("mypy", [sys.executable, "-m", "mypy", "src"])

    gate = evaluate_release_gate(status)
    if not gate.ready:
        print("release gate failed:", ", ".join(gate.failed), file=sys.stderr)
        raise SystemExit(1)
    if CURRENT_RELEASE.status == "stable":
        print(f"READY: v{CURRENT_RELEASE.version} stable")
    else:
        print(f"VERIFIED: v{CURRENT_RELEASE.version} development milestone")


if __name__ == "__main__":
    main()
