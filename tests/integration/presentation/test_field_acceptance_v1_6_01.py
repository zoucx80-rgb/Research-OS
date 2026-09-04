from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
from types import ModuleType

from research_os.application import ResearchApplication
from research_os.reporting import ResearchReportComposer, ResearchViewPresenter
from research_os.runtime.core_artifacts import (
    DECISION_RECORD,
    RESEARCH_READINESS,
    THESIS_PORTFOLIO,
)
from research_os.semantics.preservation import SemanticPreservationValidator
from research_os.snapshots.service import SnapshotService


SCRIPT = Path("scripts/render_field_acceptance_v1_6_01.py")
CASES = Path("tests/fixtures/field_acceptance/v1_6_01/cases.json")


def _runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("field_acceptance_v1_6_01", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v1_6_01_acceptance_uses_exactly_three_real_companies() -> None:
    manifest = json.loads(CASES.read_text(encoding="utf-8"))
    assert {item["case_id"] for item in manifest["cases"]} == {
        "300034.SZ",
        "001287.SZ",
        "301073.SZ",
    }
    assert manifest["decision_ts"] == "2026-08-30T00:00:00Z"
    assert manifest["body_max_lines"] == 350


def test_v1_6_01_research_depth_oracle_does_not_side_channel_valuation() -> None:
    runner = _runner()
    source = inspect.getsource(runner._research_depth)
    assert "ValuationReconciler" not in source
    assert "_valuation_reconciliation" not in source
    assert "result.artifacts.require" in source
    assert "VALUATION_RECONCILIATION" in source
    assert "VALUATION_ROUTING" in source


def _machine_checks(command, result, view, document) -> dict[str, bool]:
    semantic = SemanticPreservationValidator.validate_reporting_chain(
        result=result,
        view=view,
        document=document,
    )
    snapshot_service = SnapshotService()
    snapshot = snapshot_service.build(command=command, result=result)
    descriptor = snapshot_service.describe(snapshot)
    valid = snapshot_service.verify(
        snapshot,
        integrity_digest=descriptor.integrity_digest,
    ).valid
    portfolio = result.artifacts.require(THESIS_PORTFOLIO)
    return {
        "core_api": result.versions.core_api_version == "2.0",
        "plugin_api": result.versions.plugin_api_version == "2.0",
        "snapshot_version": result.versions.snapshot_schema_version == "2.0",
        "semantic_preservation": semantic.status == "PASS",
        "snapshot_schema": snapshot.schema_version == "2.0",
        "snapshot_integrity": valid,
        "thesis_schema": (
            portfolio.schema_version == "2.0" if hasattr(portfolio, "schema_version") else True
        ),
        "readiness_identity": (
            result.artifacts.require(RESEARCH_READINESS) == result.research_readiness
        ),
    }


def test_real_company_machine_semantics_and_depth_come_from_final_result() -> None:
    runner = _runner()
    manifest = json.loads(CASES.read_text(encoding="utf-8"))
    commit_sha = "a" * 40

    for case_spec in manifest["cases"]:
        case = runner._merge_case(Path.cwd(), case_spec)
        command = runner._command(case, commit_sha=commit_sha)
        result = ResearchApplication.build(repository_attestor=runner._Attestor(commit_sha)).run(
            command
        )
        view = ResearchViewPresenter().present(result)
        document = ResearchReportComposer().compose(view)

        checks = _machine_checks(command, result, view, document)
        semantic = SemanticPreservationValidator.validate_reporting_chain(
            result=result,
            view=view,
            document=document,
        )
        assert all(checks.values()), (
            case_spec["case_id"],
            checks,
            tuple(
                (violation.code, violation.item_id, violation.field)
                for violation in semantic.violations
            ),
        )
        assert runner._machine_semantics(command, result, view, document) == "PASS"
        assert runner._research_depth(result) == case_spec["expected_research_depth"]
        expected_decision = case_spec.get("expected_decision_state")
        if expected_decision:
            assert result.artifacts.require(DECISION_RECORD).state == expected_decision
