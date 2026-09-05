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


def _runner() -> ModuleType:
    path = Path("scripts/render_field_acceptance_v1_6_01.py")
    spec = importlib.util.spec_from_file_location("decision_context_regression_runner", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _results() -> dict[str, object]:
    runner = _runner()
    manifest = json.loads(
        Path("tests/fixtures/field_acceptance/v1_6_01/cases.json").read_text(
            encoding="utf-8"
        )
    )
    return {
        spec["case_id"]: ResearchApplication.build(
            repository_attestor=runner._Attestor("a" * 40)
        ).run(runner._command(runner._merge_case(Path.cwd(), spec), commit_sha="a" * 40))
        for spec in manifest["cases"]
    }


def test_three_company_decisions_use_complete_context_and_remain_fail_closed() -> None:
    results = _results()
    manufacturing = results["300034.SZ"]
    manufacturing_inputs = manufacturing.artifacts.require(DECISION_INPUT_ASSESSMENT)
    assert manufacturing_inputs.require_dimension("semantic_signals").state == "SUPPORTED"
    assert (
        manufacturing_inputs.require_dimension("valuation_reconciliation").state
        == "MODEL_DISAGREEMENT"
    )
    assert (
        manufacturing_inputs.require_dimension("valuation_market_gap").availability
        == "INSUFFICIENT_EVIDENCE"
    )

    distributor = results["001287.SZ"]
    distributor_record = distributor.artifacts.require(DECISION_RECORD)
    distributor_inputs = distributor.artifacts.require(DECISION_INPUT_ASSESSMENT)
    funding = distributor_inputs.require_dimension("funding_loop")
    assert distributor_record.state == "RISK_REVIEW"
    assert distributor_record.reason_codes == ("MATERIAL_FUNDING_RISK",)
    assert funding.state == "debt_funded"
    assert funding.evidence_refs

    hospitality = results["301073.SZ"]
    assert hospitality.artifacts.require(DECISION_RECORD).state == "INSUFFICIENT_EVIDENCE"
    assert (
        hospitality.artifacts.require(DECISION_INPUT_ASSESSMENT)
        .require_dimension("scenario")
        .availability
        == "INSUFFICIENT_EVIDENCE"
    )

    for result in results.values():
        derivation = result.artifacts.require(DECISION_DERIVATION)
        assert derivation.output_state == result.artifacts.require(DECISION_RECORD).state
        assert not any(
            term in str(derivation.model_dump())
            for term in ("BUY", "SELL", "ORDER", "POSITION")
        )
