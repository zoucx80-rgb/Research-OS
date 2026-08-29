from datetime import datetime, timezone

from research_os.completion.models import ResearchCompletionResult
from research_os.plugins.resolver import StrategyResolution
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import BaselineFingerprint, CompanyRef
from research_os.runtime.modules import ModuleResult
from research_os.runtime.result import ComponentFingerprint, ResearchRunResult
from research_os.snapshots.service import SnapshotService


VERSIONS = {
    "research_os_version": "1.3.0",
    "dataset_version": "dataset@test",
    "parser_version": "parser@test",
    "formula_version": "formula@test",
    "router_version": "router@test",
    "kpi_pack_version": "kpi@test",
    "driver_model_version": "driver@test",
    "forecast_version": "forecast@test",
    "valuation_version": "valuation@test",
    "report_version": "report@test",
    "core_api_version": "1.0",
}


def test_research_run_result_is_canonical_and_serializable():
    decision_ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    fingerprints = [
        ComponentFingerprint(
            component_id="core:research-engine",
            component_type="core",
            component_version="1.0.0",
            api_version="1.0",
        )
    ]
    strategy = StrategyResolution()
    snapshot = SnapshotService().freeze(
        "synthetic:result",
        decision_ts,
        VERSIONS,
        payload={"kind": "runtime"},
        component_fingerprints=fingerprints,
        strategy_resolution=strategy,
    )
    result = ResearchRunResult(
        run_id="run:result",
        company=CompanyRef(company_id="synthetic:result"),
        decision_ts=decision_ts,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version="1.3.0",
            core_api_version="1.0",
        ),
        business_model=BusinessModelProfile(
            company_id="synthetic:result",
            primary_model="manufacturing",
            confidence=0.9,
            evidence_ids=["ev:model"],
            router_version="router@test",
        ),
        strategy_resolution=strategy,
        module_results={
            "core:test": ModuleResult(module_id="core:test", status="PASS", artifacts={"test.ready": True})
        },
        artifacts={"test.ready": True},
        completion=ResearchCompletionResult(
            final_status="COMPLETE",
            blocking_modules=[],
            module_statuses={"Test": "PASS"},
        ),
        component_fingerprints=fingerprints,
        snapshot=snapshot,
    )
    payload = result.model_dump(mode="json")
    assert payload["run_id"] == "run:result"
    assert payload["component_fingerprints"][0]["component_id"] == "core:research-engine"
    assert payload["snapshot"]["payload"]["component_fingerprints"][0]["component_id"] == "core:research-engine"
