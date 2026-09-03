from datetime import datetime, timezone

from research_os.application.command import ResearchRunCommand
from research_os.application.result import ResearchRunResult, RunVersionSet
from research_os.completion import ExecutionCompletionResult
from research_os.contracts.artifacts import ArtifactSnapshot
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.plugins.resolver import StrategyResolution
from research_os.readiness import ResearchReadinessAssessment
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.snapshots.service import SnapshotService


DECISION_TS = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _baseline() -> BaselineFingerprint:
    return BaselineFingerprint(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        commit_sha="a" * 40,
        research_os_version="1.6.0",
        core_api_version="2.0",
    )


def _command(run_id: str) -> ResearchRunCommand:
    return ResearchRunCommand(
        context=ResearchContext(
            run_id=run_id,
            company=CompanyRef(company_id="000001.SZ"),
            decision_ts=DECISION_TS,
            baseline=_baseline(),
            evidence=EvidenceView((), company_id="000001.SZ", decision_ts=DECISION_TS),
            facts=FactView(
                company_id="000001.SZ",
                decision_ts=DECISION_TS,
                values={},
                evidence_refs_by_fact={},
                reporting_period=ReportingPeriod(period_type="FY"),
                accounting_scope=AccountingScope(),
            ),
        )
    )


def _result(run_id: str) -> ResearchRunResult:
    completion = ExecutionCompletionResult(final_status="COMPLETE", module_statuses={})
    readiness = ResearchReadinessAssessment(
        final_status="READY",
        dimensions=(),
        execution_status="COMPLETE",
    )
    return ResearchRunResult(
        run_id=run_id,
        company=CompanyRef(company_id="000001.SZ"),
        decision_ts=DECISION_TS,
        baseline=_baseline(),
        strategy_resolution=StrategyResolution(),
        artifacts=ArtifactSnapshot({}),
        module_results=(),
        execution_completion=completion,
        research_readiness=readiness,
        versions=RunVersionSet(
            research_os_version="1.6.0",
            core_api_version="2.0",
            plugin_api_version="2.0",
            snapshot_schema_version="2.0",
            http_api_version="v1",
        ),
        component_fingerprints=(),
    )


def test_research_digest_ignores_run_identity_but_integrity_digest_does_not() -> None:
    snapshot_ids = iter(("snapshot-a", "snapshot-b"))
    service = SnapshotService(
        clock=lambda: DECISION_TS,
        snapshot_id_factory=lambda: next(snapshot_ids),
    )

    first = service.build(command=_command("run-a"), result=_result("run-a"))
    second = service.build(command=_command("run-b"), result=_result("run-b"))
    first_descriptor = service.describe(first)
    second_descriptor = service.describe(second)

    assert first_descriptor.research_digest == second_descriptor.research_digest
    assert first_descriptor.integrity_digest != second_descriptor.integrity_digest
    assert first.payload_hash == first_descriptor.research_digest


def test_verify_reports_research_and_integrity_mismatches() -> None:
    service = SnapshotService(
        clock=lambda: DECISION_TS,
        snapshot_id_factory=lambda: "snapshot-a",
    )
    snapshot = service.build(command=_command("run-a"), result=_result("run-a"))
    descriptor = service.describe(snapshot)

    assert service.verify(snapshot, integrity_digest=descriptor.integrity_digest).valid
    assert (
        service.verify(
            snapshot.model_copy(update={"payload_hash": "0" * 64}),
            integrity_digest=descriptor.integrity_digest,
        ).reason
        == "research digest mismatch"
    )
    assert service.verify(snapshot, integrity_digest="0" * 64).reason == "integrity digest mismatch"
