from datetime import date, datetime, timedelta, timezone

import pytest

from research_os.completion.gate import REQUIRED_MODULES, ResearchCompletionGate
from research_os.completion.models import ResearchCompletionInput
from research_os.decision.models import DecisionContext, DecisionStateRecord
from research_os.plugins.resolver import StrategyResolution
from research_os.reporting.summary import DecisionSummaryBuilder
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.runtime.result import ResearchRunResult
from research_os.snapshots.service import SnapshotService
from research_os.thesis.models import Falsifier, Thesis


def _result():
    decision_ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    statuses = {name: "PASS" for name in REQUIRED_MODULES}
    statuses["Forecast Discipline"] = "NOT_APPLICABLE"
    statuses["Financial Sanity"] = "FAIL"
    completion = ResearchCompletionGate().evaluate(
        ResearchCompletionInput(module_statuses=statuses)
    )
    baseline = BaselineFingerprint(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        commit_sha="1234567890abcdef1234567890abcdef12345678",
        research_os_version="1.4.0",
        core_api_version="1.0",
    )
    profile = BusinessModelProfile(
        company_id="synthetic:report",
        primary_model="distributor",
        confidence=.9,
        evidence_ids=["ev:1"],
        router_version="router@1.0.0",
    )
    decision_context = DecisionContext(
        company_id="synthetic:report",
        fundamental_state="IMPROVING",
        valuation_state="FAIR",
        expectation_state="UNDER_EXPECTED",
        thesis_state="ACTIVE",
        evidence_confidence=.85,
        evidence_ids=["ev:1"],
        decision_ts=decision_ts,
        research_os_version="1.4.0",
    )
    decision_record = DecisionStateRecord(
        company_id="synthetic:report",
        state="WAIT_FOR_CONFIRMATION",
        decision_ts=decision_ts,
        evidence_ids=["ev:1"],
        research_os_version="1.4.0",
    )
    thesis = Thesis(
        thesis_id="synthetic:thesis",
        company_id="synthetic:report",
        title="Synthetic thesis",
        statement="Growth converts to cash.",
        mechanism="Cash conversion improves with working-capital discipline.",
        anti_thesis="Working capital absorbs growth and funding risk rises.",
        status="active",
        falsifiers=[Falsifier(metric="cfo", operator="<", threshold=0)],
        next_check_date=date(2026, 11, 30),
        confidence=.7,
    )
    event = {
        "event_name": "synthetic next disclosure",
        "event_time": (decision_ts + timedelta(days=60)).isoformat(),
    }
    snapshot = SnapshotService().freeze(
        "synthetic:report",
        decision_ts,
        {
            "research_os_version": "1.4.0",
            "dataset_version": "synthetic@1",
            "parser_version": "synthetic@1",
            "formula_version": "synthetic@1",
            "router_version": "router@1.0.0",
            "kpi_pack_version": "industry:distributor@1.0.0",
            "driver_model_version": "driver@1",
            "forecast_version": "none",
            "valuation_version": "valuation@1",
            "report_version": "report@1",
            "core_api_version": "1.0",
        },
        payload={"synthetic": True},
    )
    return ResearchRunResult(
        run_id="run:report",
        company=CompanyRef(company_id="synthetic:report"),
        decision_ts=decision_ts,
        baseline=baseline,
        business_model=profile,
        strategy_resolution=StrategyResolution(),
        module_results={},
        artifacts={
            "decision.context": decision_context,
            "decision.record": decision_record,
            "thesis.items": [thesis],
            "temporal.event": event,
            "report.final_status": "COMPLETE",
        },
        completion=completion,
        component_fingerprints=[],
        snapshot=snapshot,
    )


def test_summary_is_derived_only_from_canonical_research_run_result():
    result = _result()
    summary = DecisionSummaryBuilder().build(result)

    assert summary.company_id == result.company.company_id
    assert summary.business_model == result.business_model.primary_model
    assert summary.primary_thesis == "Growth converts to cash."
    assert summary.fundamental_state == "IMPROVING"
    assert summary.expectation_state == "UNDER_EXPECTED"
    assert summary.valuation_state == "FAIR"
    assert summary.evidence_confidence == .85
    assert summary.decision_state == "WAIT_FOR_CONFIRMATION"
    assert summary.next_verification_event == "synthetic next disclosure"
    assert summary.research_os_version == result.baseline.research_os_version
    assert summary.final_status == result.completion.final_status == "INCOMPLETE"
    assert summary.blocking_modules == result.completion.blocking_modules
    assert summary.module_statuses == result.completion.module_statuses


def test_summary_builder_rejects_parallel_dict_status_surface():
    with pytest.raises(TypeError, match="ResearchRunResult"):
        DecisionSummaryBuilder().build({
            "company_id": "synthetic",
            "final_status": "COMPLETE",
        })
