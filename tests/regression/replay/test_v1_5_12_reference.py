from __future__ import annotations

import json
from pathlib import Path


BEHAVIOR_BASELINE_SHA = "72ab06c619678b35c31cf7edef7547849e803d16"
REFERENCE_ROOT = (
    Path(__file__).parents[2]
    / "fixtures"
    / "historical_replay"
    / "v1_5_12"
    / "report_reference"
)


def _load(name: str) -> dict[str, object]:
    return json.loads((REFERENCE_ROOT / name).read_text(encoding="utf-8"))


def test_m1_report_reference_remains_bound_to_behavior_baseline() -> None:
    manufacturer = _load("anonymous_manufacturer.json")
    valuation = _load("valuation_reconciliation.json")

    assert manufacturer["behavior_baseline_sha"] == BEHAVIOR_BASELINE_SHA
    assert valuation["behavior_baseline_sha"] == BEHAVIOR_BASELINE_SHA
    assert manufacturer["fixture_kind"] == "v1_5_12_report_characterization"


def test_historical_reference_preserves_diagnostic_semantics_without_v2_equality_gate() -> None:
    manufacturer = _load("anonymous_manufacturer.json")
    expected = manufacturer["expected"]
    assert isinstance(expected, dict)

    preservation = expected["semantic_preservation"]
    assert preservation["status"] == "PASS"
    assert len(preservation["sensitivity_fingerprint"]) == 64
    assert len(preservation["monitoring_fingerprint"]) == 64
    assert expected["sensitivity_view_payload"]
    assert expected["monitoring_view_payload"]
    assert expected["sensitivity_document_payload"]
    assert expected["monitoring_document_payload"]

    valuation = _load("valuation_reconciliation.json")["expected"]
    assert valuation["status"] == "INTERSECTION"
    assert valuation["method"] == "mathematical_intersection"

    # These frozen 1.5.12 shapes explain historical replay differences. M4 must
    # never import them into or compare them for equality with the current v2 path.
    assert expected["presentation_version"] == "professional-research-view@1.7.0"
