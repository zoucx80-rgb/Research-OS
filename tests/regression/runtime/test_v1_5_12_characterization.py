"""Validate frozen v1.5.12 reference evidence without importing v1 code."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


BASELINE_SHA = "72ab06c619678b35c31cf7edef7547849e803d16"
REFERENCE_ROOT = Path(__file__).parents[2] / "fixtures" / "historical_replay" / "v1_5_12"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_v1_5_12_reference_files_match_the_verified_historical_manifest() -> None:
    manifest = _json(REFERENCE_ROOT / "reference-manifest.json")

    assert manifest["behavior_baseline_sha"] == BASELINE_SHA
    assert manifest["verification_mode"] == ("detached_worktree_with_explicit_historical_src")
    for relative_path, expected_digest in manifest["files"].items():
        content = (REFERENCE_ROOT / relative_path).read_bytes()
        assert hashlib.sha256(content).hexdigest() == expected_digest


def test_runtime_reference_retains_kpi_missingness_lineage_and_completion() -> None:
    manufacturer = _json(REFERENCE_ROOT / "runtime_reference" / "anonymous_manufacturer.json")
    distributor = _json(REFERENCE_ROOT / "runtime_reference" / "anonymous_distributor.json")

    for payload in (manufacturer, distributor):
        assert payload["behavior_baseline_sha"] == BASELINE_SHA
        metrics = payload["expected"]["kpi_metrics"]
        assert any(item["status"] == "valid" for item in metrics.values())
        assert any(item["status"] == "missing" for item in metrics.values())
        assert all(item["evidence_ids"] for item in metrics.values() if item["status"] == "valid")

    assert distributor["expected"]["completion"]["final_status"] == "INCOMPLETE"
    assert distributor["expected"]["financial_fact_snapshot"]["facts"]
