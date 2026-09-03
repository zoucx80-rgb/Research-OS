from __future__ import annotations

import json
from pathlib import Path

from scripts.render_field_acceptance_v1_6_0 import _acceptance_statuses


FIXTURE_ROOT = Path("tests/fixtures/field_acceptance/v1_6_0")
EXPECTED_FIXTURES = {
    "manufacturing_typed_architecture.json",
    "distributor_funding_and_valuation.json",
    "coverage_limited_no_plugin.json",
}


def test_v1_6_field_acceptance_uses_the_three_named_contract_fixtures() -> None:
    assert {path.name for path in FIXTURE_ROOT.glob("*.json")} == EXPECTED_FIXTURES


def test_acceptance_statuses_keep_machine_depth_and_presentation_separate() -> None:
    case = {
        "case_id": "coverage_limited_no_plugin",
        "expected_machine_semantics": "PASS",
        "expected_research_depth": "LIMITED",
        "expected_presentation": "PASS",
    }

    assert _acceptance_statuses(case) == {
        "machine_semantics": "PASS",
        "research_depth": "LIMITED",
        "presentation": "PASS",
    }


def test_every_v1_6_fixture_declares_all_three_acceptance_states() -> None:
    for path in sorted(FIXTURE_ROOT.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        assert set(_acceptance_statuses(case)) == {
            "machine_semantics",
            "research_depth",
            "presentation",
        }
