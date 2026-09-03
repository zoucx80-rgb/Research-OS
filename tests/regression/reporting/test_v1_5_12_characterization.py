"""Validate frozen v1.5.12 report reference evidence as data only."""

from __future__ import annotations

import json
from pathlib import Path


BASELINE_SHA = "72ab06c619678b35c31cf7edef7547849e803d16"
REFERENCE_ROOT = Path(__file__).parents[2] / "fixtures" / "historical_replay" / "v1_5_12"


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_report_reference_retains_sensitivity_monitoring_and_semantic_fingerprints() -> None:
    payload = _json(REFERENCE_ROOT / "report_reference" / "anonymous_manufacturer.json")
    expected = payload["expected"]

    assert payload["behavior_baseline_sha"] == BASELINE_SHA
    assert expected["sensitivity_view_payload"]
    assert expected["monitoring_view_payload"]
    assert len(expected["semantic_preservation"]["sensitivity_fingerprint"]) == 64
    assert len(expected["semantic_preservation"]["monitoring_fingerprint"]) == 64


def test_report_reference_retains_valuation_reconciliation_semantics() -> None:
    payload = _json(REFERENCE_ROOT / "report_reference" / "valuation_reconciliation.json")

    assert payload["behavior_baseline_sha"] == BASELINE_SHA
    assert payload["expected"] == {
        "status": "INTERSECTION",
        "method": "mathematical_intersection",
        "low": 15.0,
        "high": 18.0,
        "basis": "equity_per_share",
        "currency": "CNY",
        "included_range_ids": ["pe", "ev-ebitda"],
    }
