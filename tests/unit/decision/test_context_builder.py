from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from research_os.contracts.artifact_values import FundingLoop
from research_os.contracts.artifacts import ArtifactStore, ArtifactWrite
from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.decision.context import DecisionContextBuilder
from research_os.period.models import ReportingPeriod
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.runtime.core_artifacts import (
    CAPITAL_FUNDING_LOOP,
    VALUATION_MARKET_GAP,
    build_core_artifact_catalog,
)
from research_os.runtime.state import ResearchStateView
from research_os.valuation.market import ValuationMarketGap


DECISION_TS = datetime(2026, 8, 30, tzinfo=timezone.utc)
REFERENCE = EvidenceRef(
    evidence_id="ev:decision-context",
    revision=1,
    content_fingerprint="a" * 64,
)


def _context() -> ResearchContext:
    return ResearchContext(
        run_id="run:decision-context",
        company=CompanyRef(company_id="synthetic:decision-context"),
        decision_ts=DECISION_TS,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.6.02",
            core_api_version="2.0",
        ),
        evidence=EvidenceView((), company_id="synthetic:decision-context", decision_ts=DECISION_TS),
        facts=FactView(
            company_id="synthetic:decision-context",
            decision_ts=DECISION_TS,
            values={},
            evidence_refs_by_fact={},
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        ),
    )


def _state(*writes: tuple[object, object]) -> ResearchStateView:
    store = ArtifactStore(build_core_artifact_catalog())
    for key, value in writes:
        store.write(
            ArtifactWrite(
                key=key,
                value=value,
                producer_id="test:decision-context",
                evidence_refs=getattr(value, "evidence_refs", ()),
            )
        )
    return ResearchStateView(store.freeze())


def test_market_gap_drives_valuation_state() -> None:
    gap = ValuationMarketGap(
        domain_status="SUPPORTED",
        reconciliation_key="INTERSECTION:mathematical_intersection",
        market_anchor_security_id="300034.SZ",
        market_anchor_observed_ts=DECISION_TS,
        market_value=Decimal("10"),
        model_low=Decimal("12"),
        model_high=Decimal("15"),
        gap_low=Decimal("2"),
        gap_high=Decimal("5"),
        currency="CNY",
        valuation_basis="per_share",
        state="UNDERVALUED",
        comparison_status="PASS",
        evidence_refs=(REFERENCE,),
    )

    context, assessment = DecisionContextBuilder().build(
        _context(),
        _state((VALUATION_MARKET_GAP, gap)),
    )

    assert context.valuation_state == "CHEAP"
    assert assessment.require_dimension("valuation_market_gap").state == "UNDERVALUED"


def test_material_funding_risk_is_preserved() -> None:
    funding = FundingLoop(
        domain_status="SUPPORTED",
        funding_state="debt_funded",
        reason_codes=("NEGATIVE_OCF",),
        evidence_refs=(REFERENCE,),
    )

    context, _ = DecisionContextBuilder().build(
        _context(),
        _state((CAPITAL_FUNDING_LOOP, funding)),
    )

    assert context.material_funding_risk is True


def test_missing_scenario_is_explicit() -> None:
    context, assessment = DecisionContextBuilder().build(_context(), _state())

    assert context.scenario_state == "UNAVAILABLE"
    assert assessment.require_dimension("scenario").availability == "INSUFFICIENT_EVIDENCE"
