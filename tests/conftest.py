from datetime import date, datetime, timezone

import pytest

from research_os.completion.gate import REQUIRED_MODULES, ResearchCompletionGate
from research_os.completion.models import ResearchCompletionInput, ResearchCompletionResult
from research_os.decision.models import DecisionStateRecord
from research_os.plugins.resolver import StrategyResolution
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.runtime.result import ResearchRunResult
from research_os.snapshots.service import SnapshotService
from research_os.thesis.models import Falsifier, Thesis
from research_os.version import RESEARCH_OS_VERSION


@pytest.fixture
def canonical_report_result_factory():
    def make(
        *,
        completion: ResearchCompletionResult | None = None,
        baseline_version: str = RESEARCH_OS_VERSION,
        artifacts: dict | None = None,
    ) -> ResearchRunResult:
        decision_ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
        if completion is None:
            statuses = {name: "PASS" for name in REQUIRED_MODULES}
            statuses["Forecast Discipline"] = "NOT_APPLICABLE"
            completion = ResearchCompletionGate().evaluate(
                ResearchCompletionInput(module_statuses=statuses)
            )

        baseline = BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version=baseline_version,
            core_api_version="1.0",
        )
        profile = BusinessModelProfile(
            company_id="synthetic:report",
            primary_model="distributor",
            confidence=.9,
            evidence_ids=["ev:1"],
            router_version="router@1.0.0",
        )
        decision = DecisionStateRecord(
            company_id="synthetic:report",
            state="WAIT_FOR_CONFIRMATION",
            decision_ts=decision_ts,
            evidence_ids=["ev:1"],
            research_os_version=baseline_version,
            fundamental_state="IMPROVING",
            valuation_state="FAIR",
            expectation_state="UNDER_EXPECTED",
            thesis_state="ACTIVE",
            evidence_confidence=.85,
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
        payload = {
            "decision.record": decision,
            "thesis.items": [thesis],
            "claims.items": [],
            "temporal.event": {"event_name": "synthetic next disclosure"},
        }
        payload.update(artifacts or {})
        snapshot = SnapshotService().freeze(
            "synthetic:report",
            decision_ts,
            {
                "research_os_version": baseline_version,
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
            artifacts=payload,
            completion=completion,
            component_fingerprints=[],
            snapshot=snapshot,
        )

    return make
