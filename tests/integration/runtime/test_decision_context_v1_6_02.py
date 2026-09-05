from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

from research_os.application import ResearchApplication
from research_os.runtime.core_artifacts import (
    DECISION_DERIVATION,
    DECISION_INPUT_ASSESSMENT,
    DECISION_RECORD,
)


REQUIRED_DECISION_DIMENSIONS = {
    "financial_temporal",
    "capital_efficiency",
    "funding_loop",
    "thesis_portfolio",
    "semantic_signals",
    "expectation_gap",
    "forecast_quality",
    "valuation_reconciliation",
    "valuation_market_gap",
    "scenario",
    "research_sufficiency",
}


def _runner() -> ModuleType:
    path = Path("scripts/render_field_acceptance_v1_6_01.py")
    spec = importlib.util.spec_from_file_location("decision_context_field_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_portfolio_decision_publishes_every_consumed_dimension() -> None:
    runner = _runner()
    manifest = json.loads(
        Path("tests/fixtures/field_acceptance/v1_6_01/cases.json").read_text(
            encoding="utf-8"
        )
    )
    case = runner._merge_case(Path.cwd(), manifest["cases"][0])
    command = runner._command(case, commit_sha="a" * 40)
    result = ResearchApplication.build(
        repository_attestor=runner._Attestor("a" * 40)
    ).run(command)

    assessment = result.artifacts.require(DECISION_INPUT_ASSESSMENT)
    derivation = result.artifacts.require(DECISION_DERIVATION)
    record = result.artifacts.require(DECISION_RECORD)
    assert {item.dimension for item in assessment.dimensions} == REQUIRED_DECISION_DIMENSIONS
    assert derivation.input_states == assessment.dimensions
    assert derivation.output_state == record.state
    assert derivation.rule_version == "2.0.2"
