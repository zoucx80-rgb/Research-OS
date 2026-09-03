from __future__ import annotations

import subprocess
from datetime import datetime, timezone

from research_os.application import ResearchApplication, ResearchRunCommand
from research_os.application.bootstrap import RepositoryAttestation
from research_os.application.command import ResearchRunOptions
from research_os.contracts.artifact_values import (
    AssumptionRef,
    MonitoringPlan,
    MonitoringPlanItem,
    ScenarioAssumption,
    SensitivityCase,
    SensitivitySet,
)
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
from research_os.period.models import ReportingPeriod
from research_os.reporting import ResearchReportComposer, ResearchViewPresenter
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.semantics.fingerprint import semantic_fingerprint
from research_os.semantics.preservation import SemanticPreservationValidator
from research_os.snapshots.codec import SnapshotCodecV2
from research_os.snapshots.service import SnapshotService


DECISION_TS = datetime(2026, 9, 3, 8, 0, tzinfo=timezone.utc)
COMPANY_ID = "synthetic:semantic-fingerprint"


def _head() -> str:
    return subprocess.check_output(("git", "rev-parse", "HEAD"), text=True).strip()


class _Attestor:
    def attest(self) -> RepositoryAttestation:
        return RepositoryAttestation(
            repository_host="github.com",
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            head_sha=_head(),
        )


def _run(run_id: str):
    evidence_item = Evidence(
        evidence_id="ev:semantic-business",
        revision_no=2,
        company_id=COMPANY_ID,
        evidence_type="filing_fact",
        publish_ts=DECISION_TS,
        ingested_at=DECISION_TS,
        source_table="business_description",
        value="precision manufacturing",
        confidence_grade="A",
        verification_status="PRIMARY_VERIFIED",
    )
    evidence = EvidenceView(
        (evidence_item,), company_id=COMPANY_ID, decision_ts=DECISION_TS
    )
    ref = evidence.refs()[0]
    command = ResearchRunCommand(
        context=ResearchContext(
            run_id=run_id,
            company=CompanyRef(company_id=COMPANY_ID),
            decision_ts=DECISION_TS,
            baseline=BaselineFingerprint(
                repository_full_name="zoucx80-rgb/Research-OS",
                repository_id=1350382205,
                branch="main",
                commit_sha=_head(),
                research_os_version="1.6.0",
                core_api_version="2.0",
            ),
            evidence=evidence,
            facts=FactView(
                company_id=COMPANY_ID,
                decision_ts=DECISION_TS,
                values={"business_description": evidence_item.value},
                evidence_refs_by_fact={"business_description": (ref,)},
                reporting_period=ReportingPeriod(period_type="FY"),
                accounting_scope=AccountingScope(),
            ),
        ),
        options=ResearchRunOptions(persist_snapshot=False),
    )
    result = ResearchApplication.build(repository_attestor=_Attestor()).run(command)
    return command, result


def test_result_view_document_share_one_semantic_fingerprint() -> None:
    _, result = _run("run:semantic-a")
    view = ResearchViewPresenter().present(result)
    document = ResearchReportComposer().compose(view)

    validation = SemanticPreservationValidator.validate_reporting_chain(
        result=result,
        view=view,
        document=document,
    )

    assert validation.status == "PASS"
    assert validation.violations == ()
    assert validation.research_fingerprint == semantic_fingerprint(result.artifacts)
    assert view.semantic_fingerprint == validation.research_fingerprint
    assert document.semantic_fingerprint == validation.research_fingerprint


def test_semantic_fingerprint_excludes_run_snapshot_and_display_identity() -> None:
    command, result = _run("run:semantic-a")
    other = result.model_copy(update={"run_id": "run:semantic-b", "snapshot": None})

    assert semantic_fingerprint(result.artifacts) == semantic_fingerprint(other.artifacts)

    first_service = SnapshotService(
        clock=lambda: DECISION_TS,
        snapshot_id_factory=lambda: "snapshot:semantic-a",
    )
    second_service = SnapshotService(
        clock=lambda: DECISION_TS,
        snapshot_id_factory=lambda: "snapshot:semantic-b",
    )
    first = first_service.build(command=command, result=result)
    second = second_service.build(command=command, result=other)
    codec = SnapshotCodecV2()

    assert first.payload_hash == second.payload_hash
    assert codec.integrity_digest(first) != codec.integrity_digest(second)

    view = ResearchViewPresenter().present(result)
    document = ResearchReportComposer().compose(view)
    altered_document = document.model_copy(
        update={"semantic_fingerprint": "0" * 64}
    )
    assert SemanticPreservationValidator.validate_reporting_chain(
        result=result,
        view=view,
        document=altered_document,
    ).status == "FAIL"


def test_v2_sensitivity_and_monitoring_keep_typed_qualifiers_and_lineage() -> None:
    assumption = AssumptionRef(
        assumption_key="assumption:volume",
        assumption_version="1",
        content_fingerprint="a" * 64,
    )
    sensitivities = SensitivitySet(
        domain_status="SUPPORTED",
        cases=(
            SensitivityCase(
                case_key="case:margin",
                driver_key="raw_material_price",
                shock_label="+5%",
                affected_metric="gross_margin",
                formula_version="sensitivity@2",
                result=-0.02,
                material_assumptions=(
                    ScenarioAssumption(
                        reference=assumption,
                        label="volume unchanged",
                        value=True,
                    ),
                ),
                model_boundary="mechanical sensitivity; not a forecast",
                assumption_refs=(assumption,),
            ),
        ),
    )
    monitoring = MonitoringPlan(
        domain_status="SUPPORTED",
        items=(
            MonitoringPlanItem(
                item_key="monitor:margin",
                metric_id="gross_margin",
                condition="gross_margin < policy threshold",
                assumption_refs=(assumption,),
            ),
        ),
    )

    validation = SemanticPreservationValidator.validate_v2_qualifiers(
        sensitivities=sensitivities,
        monitoring_plan=monitoring,
    )

    assert validation.status == "PASS"
    assert validation.sensitivity_fingerprint is not None
    assert validation.monitoring_fingerprint is not None

    invalid = SemanticPreservationValidator.validate_v2_qualifiers(
        sensitivities=SensitivitySet(
            domain_status="SUPPORTED",
            cases=(
                SensitivityCase(
                    case_key="case:invalid",
                    driver_key="price",
                    shock_label="+5%",
                    affected_metric="margin",
                    formula_version="sensitivity@2",
                    result=-0.01,
                ),
            ),
        ),
        monitoring_plan=MonitoringPlan(
            domain_status="SUPPORTED",
            items=(
                MonitoringPlanItem(
                    item_key="monitor:invalid",
                    metric_id="margin",
                    condition="margin < threshold",
                ),
            ),
        ),
    )
    assert invalid.status == "FAIL"
    assert {item.code for item in invalid.violations} >= {
        "SENSITIVITY_ASSUMPTIONS_MISSING",
        "SENSITIVITY_MODEL_BOUNDARY_MISSING",
        "SENSITIVITY_LINEAGE_MISSING",
        "MONITORING_LINEAGE_MISSING",
    }
