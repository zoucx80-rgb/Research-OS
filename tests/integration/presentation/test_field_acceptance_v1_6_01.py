from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path
from types import ModuleType

from research_os.application import ResearchApplication
from research_os.reporting import (
    MarkdownArtifactRenderer,
    ResearchReportComposer,
    ResearchViewPresenter,
)
from research_os.runtime.core_artifacts import (
    DECISION_RECORD,
    KPI_METRICS,
    MONITORING_PLAN,
    RESEARCH_READINESS,
    SCENARIO_SENSITIVITIES,
    THESIS_PORTFOLIO,
)
from research_os.semantics.preservation import SemanticPreservationValidator
from research_os.snapshots.service import SnapshotService


SCRIPT = Path("scripts/render_field_acceptance_v1_6_01.py")
CASES = Path("tests/fixtures/field_acceptance/v1_6_01/cases.json")

EXPECTED_ARTIFACT_IDS = {
    "business_model.profile",
    "capital.efficiency",
    "capital.funding_loop",
    "cash_flow.quality_bridge",
    "decision.record",
    "decision.state_provenance",
    "drivers.graph",
    "evidence.pit",
    "expectation.consensus_distribution",
    "expectation.gap",
    "expectation.quality",
    "expectation.snapshot",
    "financial.fact_snapshot",
    "financial.temporal_analysis",
    "financial.time_series",
    "forecast.evaluation",
    "kpi.metrics",
    "methodology.disclosure",
    "monitoring.plan",
    "monitoring.prior_run_review",
    "peers.normalized",
    "research.operating_evidence",
    "research.readiness",
    "research.sufficiency",
    "scenario.sensitivities",
    "semantic.claims",
    "strategy.resolution",
    "thesis.portfolio",
    "thesis.semantic_signal_assessment",
    "validation.financial",
    "validation.repository_preflight",
    "valuation.execution",
    "valuation.reconciliation",
    "valuation.result",
    "valuation.routing",
}


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


def test_manufacturing_fixture_sensitivity_reaches_final_result_and_report() -> None:
    runner = _runner()
    manifest = json.loads(CASES.read_text(encoding="utf-8"))
    case_spec = next(item for item in manifest["cases"] if item["case_id"] == "300034.SZ")
    case = runner._merge_case(Path.cwd(), case_spec)
    command = runner._command(case, commit_sha="a" * 40)
    result = ResearchApplication.build(repository_attestor=runner._Attestor("a" * 40)).run(command)

    sensitivities = result.artifacts.require(SCENARIO_SENSITIVITIES)
    assert sensitivities.domain_status == "SUPPORTED"
    assert tuple(item.case_key for item in sensitivities.cases) == ("raw-material-up",)
    sensitivity = sensitivities.cases[0]
    assert tuple(item.label for item in sensitivity.material_assumptions) == (
        "售价不变",
        "产品结构不变",
    )
    assert sensitivity.model_boundary == "机械敏感性，不是公司盈利预测"
    assert sensitivity.applicability == "销量与产品结构不变的单一报告期"
    assert sensitivity.caveats == ("未模拟存货计价和价格传导时滞",)

    view = ResearchViewPresenter().present(result)
    document = ResearchReportComposer().compose(view)
    markdown = MarkdownArtifactRenderer().render(document).content
    assert "### 敏感性与情景" in markdown
    assert "原材料价格 +5%" in markdown
    assert "售价不变" in markdown
    assert "机械敏感性，不是公司盈利预测" in markdown
    assert "销量与产品结构不变的单一报告期" in markdown
    assert "未模拟存货计价和价格传导时滞" in markdown


def test_pdf_first_page_contract_requires_decision_and_risk_or_limitation() -> None:
    runner = _runner()

    assert (
        runner._first_page_errors("投资决策快照\n研究决策\n状态：风险审查\n核心原因：融资压力")
        == ()
    )
    assert runner._first_page_errors("投资决策快照\n研究决策\n状态：证据不足") == ()
    assert (
        runner._first_page_errors("投资决策快照\n研究决策\n状态：证据不⾜\n核⼼原因：融资压力")
        == ()
    )
    assert runner._first_page_errors("普通封面") == (
        "PDF first page is missing the decision snapshot",
        "PDF first page is missing the research decision",
        "PDF first page is missing a key risk or limitation",
    )


def test_distributor_next_verification_event_reaches_final_result_and_report() -> None:
    runner = _runner()
    manifest = json.loads(CASES.read_text(encoding="utf-8"))
    case_spec = next(item for item in manifest["cases"] if item["case_id"] == "001287.SZ")
    case = runner._merge_case(Path.cwd(), case_spec)
    command = runner._command(case, commit_sha="a" * 40)
    result = ResearchApplication.build(repository_attestor=runner._Attestor("a" * 40)).run(command)

    monitoring = result.artifacts.require(MONITORING_PLAN)
    assert monitoring.domain_status == "SUPPORTED"
    assert monitoring.next_verification_event is not None
    assert (
        monitoring.next_verification_event.label
        == "下一次定期报告中的营运资金、融资成本与现金流验证"
    )
    assert monitoring.next_verification_event.due_ts.isoformat() == "2026-10-31T00:00:00+00:00"

    view = ResearchViewPresenter().present(result)
    document = ResearchReportComposer().compose(view)
    markdown = MarkdownArtifactRenderer().render(document).content
    assert "下一次定期报告中的营运资金、融资成本与现金流验证" in markdown
    assert "2026-10-31" in markdown
    assert "类型**：定期报告" in markdown
    assert "状态**：已计划" in markdown
    assert "periodic_report" not in markdown.split("## 审计附录", maxsplit=1)[0]
    assert "Scheduled" not in markdown.split("## 审计附录", maxsplit=1)[0]


def test_real_company_artifact_sets_and_fail_closed_states_are_exact() -> None:
    runner = _runner()
    manifest = json.loads(CASES.read_text(encoding="utf-8"))
    expected_supported = {
        "300034.SZ": {
            "cash_flow.quality_bridge",
            "financial.time_series",
            "methodology.disclosure",
            "monitoring.plan",
            "scenario.sensitivities",
            "semantic.claims",
            "thesis.semantic_signal_assessment",
            "validation.financial",
            "valuation.reconciliation",
            "valuation.routing",
        },
        "001287.SZ": {
            "capital.funding_loop",
            "cash_flow.quality_bridge",
            "decision.record",
            "decision.state_provenance",
            "financial.time_series",
            "methodology.disclosure",
            "monitoring.plan",
            "research.operating_evidence",
            "semantic.claims",
            "thesis.portfolio",
            "validation.financial",
            "valuation.routing",
        },
        "301073.SZ": {
            "cash_flow.quality_bridge",
            "financial.time_series",
            "methodology.disclosure",
            "monitoring.plan",
            "research.operating_evidence",
            "validation.financial",
            "valuation.routing",
        },
    }
    hospitality_fail_closed = {
        "decision.record",
        "decision.state_provenance",
        "scenario.sensitivities",
        "semantic.claims",
        "thesis.portfolio",
        "thesis.semantic_signal_assessment",
        "valuation.execution",
        "valuation.reconciliation",
    }

    for case_spec in manifest["cases"]:
        case = runner._merge_case(Path.cwd(), case_spec)
        command = runner._command(case, commit_sha="a" * 40)
        result = ResearchApplication.build(repository_attestor=runner._Attestor("a" * 40)).run(
            command
        )
        envelopes = {item.key.artifact_id: item for item in result.artifacts.envelopes()}
        assert set(envelopes) == EXPECTED_ARTIFACT_IDS
        statuses = {
            artifact_id: getattr(envelope.value, "domain_status", None)
            for artifact_id, envelope in envelopes.items()
        }
        for artifact_id in expected_supported[case_spec["case_id"]]:
            assert statuses[artifact_id] == "SUPPORTED", (case_spec["case_id"], artifact_id)

        if case_spec["case_id"] == "301073.SZ":
            for artifact_id in hospitality_fail_closed:
                assert statuses[artifact_id] == "INSUFFICIENT_EVIDENCE", artifact_id
            assert envelopes["valuation.result"].value.status == "INSUFFICIENT_EVIDENCE"
            metric_ids = {item.metric_id for item in result.artifacts.require(KPI_METRICS).metrics}
            assert metric_ids.isdisjoint(
                {"revpar", "adr", "occ", "occupancy", "same_store_growth", "lease_adjusted_roic"}
            )
