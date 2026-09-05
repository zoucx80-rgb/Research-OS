from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from research_os.application.command import FinancialResearchInput, ResearchRunCommand
from research_os.application.professional_modules import FinancialResearchModule
from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ModulePlanCompiler,
    ResearchContext,
    ResearchEngine,
)
from research_os.runtime.core_artifacts import (
    FINANCIAL_TEMPORAL_ANALYSIS,
    build_core_artifact_catalog,
)
from research_os.temporal.models import FinancialPeriodObservation


DECISION_TS = datetime(2026, 9, 4, tzinfo=timezone.utc)
COMPANY_ID = "synthetic:temporal-sufficiency"


def _period_observation(year: int, value: str, fingerprint: str) -> FinancialPeriodObservation:
    return FinancialPeriodObservation(
        metric_id="revenue",
        reporting_period=ReportingPeriod(
            period_type="FY",
            period_start=date(year, 1, 1),
            period_end=date(year, 12, 31),
            period_days=366 if year % 4 == 0 else 365,
            is_cumulative=True,
        ),
        period_kind="FLOW",
        value=Decimal(value),
        unit="CNY",
        accounting_scope=AccountingScope(consolidation="consolidated"),
        value_kind="reported",
        comparison_basis="YOY_PERIOD",
        available_ts=datetime(year + 1, 3, 31, tzinfo=timezone.utc),
        evidence_refs=(
            EvidenceRef(
                evidence_id=f"ev:revenue:{year}",
                revision=1,
                content_fingerprint=fingerprint * 64,
            ),
        ),
    )


def _command() -> ResearchRunCommand:
    evidence = EvidenceView((), company_id=COMPANY_ID, decision_ts=DECISION_TS)
    return ResearchRunCommand(
        context=ResearchContext(
            run_id="run:temporal-sufficiency",
            company=CompanyRef(company_id=COMPANY_ID),
            decision_ts=DECISION_TS,
            baseline=BaselineFingerprint(
                repository_full_name="zoucx80-rgb/Research-OS",
                repository_id=1350382205,
                branch="main",
                commit_sha="a" * 40,
                research_os_version="1.6.02",
                core_api_version="2.0",
            ),
            evidence=evidence,
            facts=FactView(
                company_id=COMPANY_ID,
                decision_ts=DECISION_TS,
                values={},
                evidence_refs_by_fact={},
                reporting_period=ReportingPeriod(period_type="FY"),
                accounting_scope=AccountingScope(),
            ),
        ),
        financial=FinancialResearchInput(
            period_observations=(
                _period_observation(2024, "100", "a"),
                _period_observation(2025, "110", "b"),
            )
        ),
    )


def test_financial_module_publishes_temporal_analysis_through_engine() -> None:
    command = _command()
    catalog = build_core_artifact_catalog()
    plan = ModulePlanCompiler(catalog).compile((FinancialResearchModule(command),))

    execution = ResearchEngine().execute(plan, command.context, catalog)

    temporal = execution.snapshot.require(FINANCIAL_TEMPORAL_ANALYSIS)
    assert temporal.temporal_coverage == "SUFFICIENT"
    assert temporal.assessments[0].yoy_change == Decimal("0.1")
    assert tuple(ref.evidence_id for ref in temporal.evidence_refs) == (
        "ev:revenue:2024",
        "ev:revenue:2025",
    )
    assert execution.snapshot.envelope(FINANCIAL_TEMPORAL_ANALYSIS).producer_ids == (
        "core:professional-financial",
    )
    assert execution.module_results[0].status == "PASS"
