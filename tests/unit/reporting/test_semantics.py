from datetime import datetime, timezone

import pytest

from research_os.completion.models import ResearchCompletionResult
from research_os.decision.models import DecisionContext, DecisionStateRecord
from research_os.domain.versions import VersionBundle
from research_os.plugins.resolver import StrategyResolution
from research_os.reporting.semantics import DecisionSummaryPresenter
from research_os.reporting.summary import DecisionSummary, DecisionSummaryBuilder
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.runtime.result import ResearchRunResult
from research_os.snapshots.service import ResearchSnapshot


def _summary():
    return DecisionSummary(
        company_id="synthetic:report",
        business_model="distributor",
        primary_thesis="Growth can convert to cash if working capital normalizes.",
        thesis_state="ACTIVE",
        fundamental_state="IMPROVING",
        expectation_state="MIXED",
        valuation_state="UNRELIABLE",
        evidence_confidence=0.72,
        top_drivers=["working capital"],
        top_risks=["NEGATIVE_OCF", "SOME_INTERNAL_CODE"],
        next_verification_event="next results",
        research_os_version="1.5.1",
        decision_state="WAIT_FOR_CONFIRMATION",
        final_status="INCOMPLETE",
        blocking_modules=["Expectation Evidence"],
        module_statuses={
            "Financial Sanity": "PASS",
            "Expectation Evidence": "INSUFFICIENT_EVIDENCE",
            "Valuation Execution": "NOT_APPLICABLE",
        },
        expectation_evidence_status="INSUFFICIENT_EVIDENCE",
        valuation_execution_status="NOT_APPLICABLE",
        sections=["Decision", "FinancialCapital", "Evidence"],
    )


def _result():
    decision_ts = datetime(2026, 8, 30, tzinfo=timezone.utc)
    completion = ResearchCompletionResult(
        final_status="INCOMPLETE",
        blocking_modules=["Financial Sanity"],
        module_statuses={
            "Financial Sanity": "FAIL",
            "Expectation Evidence": "INSUFFICIENT_EVIDENCE",
            "Valuation Execution": "NOT_APPLICABLE",
        },
    )
    baseline = BaselineFingerprint(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="v1.5.01-research-semantics",
        commit_sha="1" * 40,
        research_os_version="1.5.1",
        core_api_version="1.0",
    )
    context = DecisionContext(
        company_id="synthetic:report",
        fundamental_state="IMPROVING",
        valuation_state="UNRELIABLE",
        expectation_state="MIXED",
        thesis_state="ACTIVE",
        evidence_confidence=0.72,
        evidence_ids=["ev:1"],
        decision_ts=decision_ts,
        research_os_version="1.5.1",
    )
    record = DecisionStateRecord(
        company_id="synthetic:report",
        state="WAIT_FOR_CONFIRMATION",
        decision_ts=decision_ts,
        evidence_ids=["ev:1"],
        reason_codes=["NEGATIVE_OCF"],
        research_os_version="1.5.1",
    )
    versions = VersionBundle(
        research_os_version="1.5.1",
        dataset_version="synthetic@1",
        parser_version="synthetic@1",
        formula_version="synthetic@1",
        router_version="router@1.1.0",
        kpi_pack_version="industry:distributor@1.0.0",
        driver_model_version="driver@1",
        forecast_version="none",
        valuation_version="valuation@1",
        report_version="semantic-report@1.0.0",
        core_api_version="1.0",
    )
    snapshot = ResearchSnapshot(
        snapshot_id="snapshot:semantic",
        company_id="synthetic:report",
        decision_ts=decision_ts,
        versions=versions,
        payload={},
        payload_hash="0" * 64,
    )
    return ResearchRunResult(
        run_id="run:semantic",
        company=CompanyRef(company_id="synthetic:report"),
        decision_ts=decision_ts,
        baseline=baseline,
        business_model=BusinessModelProfile(
            company_id="synthetic:report",
            primary_model="distributor",
            confidence=0.9,
            evidence_ids=["ev:1"],
            router_version="router@1.1.0",
        ),
        strategy_resolution=StrategyResolution(),
        module_results={},
        artifacts={
            "decision.context": context,
            "decision.record": record,
            "capital.funding_loop": {"reason_codes": ["NEGATIVE_OCF"]},
        },
        completion=completion,
        component_fingerprints=[],
        snapshot=snapshot,
    )


def test_presenter_keeps_machine_code_secondary_and_chinese_label_primary():
    view = DecisionSummaryPresenter().present(_summary())

    assert view.final_status.label == "研究流程未完成"
    assert view.final_status.code == "INCOMPLETE"
    assert view.expectation_evidence_status.label == "证据不足"
    assert view.business_model.label == "分销业务"
    assert view.decision_state.label == "等待进一步确认"
    assert view.top_risks[0].label == "经营现金流为负"
    assert view.blocking_modules == ["市场预期证据"]


def test_presenter_does_not_recompute_completion_or_decision_state():
    result = _result()
    canonical = DecisionSummaryBuilder().build(result)
    view = DecisionSummaryPresenter().build(result)

    assert view.final_status.code == result.completion.final_status
    assert view.final_status.code == canonical.final_status
    assert view.decision_state.code == canonical.decision_state
    assert view.fundamental_state.code == canonical.fundamental_state


def test_unknown_reason_code_has_readable_fallback():
    value = DecisionSummaryPresenter().semantic(
        "SOME_INTERNAL_CODE",
        category="reason",
    )

    assert value.label != "SOME_INTERNAL_CODE"
    assert value.code == "SOME_INTERNAL_CODE"
    assert "尚未" in value.explanation
    assert "中文解释" in value.explanation
    assert "技术元数据" in value.explanation


def test_common_funding_loop_reason_codes_are_translated():
    presenter = DecisionSummaryPresenter()

    assert presenter.semantic("HIGH_IWCR", category="reason").label == "营运资金占用增速偏高"
    assert presenter.semantic("DEBT_FUNDS_NWC", category="reason").label == "新增债务主要支持营运资金"
    assert presenter.semantic("EQUITY_DILUTION", category="reason").label == "存在股权融资稀释"


def test_module_statuses_and_sections_are_human_readable():
    view = DecisionSummaryPresenter().present(_summary())

    assert view.module_statuses["财务一致性检查"].label == "通过"
    assert view.module_statuses["市场预期证据"].label == "证据不足"
    assert view.sections == ["研究决策", "财务与资本", "证据"]


def test_unsupported_locale_fails_explicitly():
    with pytest.raises(ValueError, match="unsupported presentation locale"):
        DecisionSummaryPresenter().present(_summary(), locale="en-US")
