from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from hypothesis import given, strategies as st

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


TIMESTAMP = datetime(2026, 8, 30, tzinfo=timezone.utc)
REFERENCE = EvidenceRef(
    evidence_id="ev:decision:determinism",
    revision=1,
    content_fingerprint="a" * 64,
)


def _context() -> ResearchContext:
    company_id = "synthetic:decision-determinism"
    return ResearchContext(
        run_id="run:decision-determinism",
        company=CompanyRef(company_id=company_id),
        decision_ts=TIMESTAMP,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.6.02",
            core_api_version="2.0",
        ),
        evidence=EvidenceView((), company_id=company_id, decision_ts=TIMESTAMP),
        facts=FactView(
            company_id=company_id,
            decision_ts=TIMESTAMP,
            values={},
            evidence_refs_by_fact={},
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        ),
    )


def _build(order: tuple[int, ...]):
    values = (
        (
            CAPITAL_FUNDING_LOOP,
            FundingLoop(
                domain_status="SUPPORTED",
                funding_state="self_funded",
                evidence_refs=(REFERENCE,),
            ),
        ),
        (
            VALUATION_MARKET_GAP,
            ValuationMarketGap(
                domain_status="SUPPORTED",
                reconciliation_key="INTERSECTION:mathematical_intersection",
                market_anchor_security_id="security:test",
                market_anchor_observed_ts=TIMESTAMP,
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
            ),
        ),
    )
    store = ArtifactStore(build_core_artifact_catalog())
    for index in order:
        key, value = values[index]
        store.write(
            ArtifactWrite(
                key=key,
                value=value,
                producer_id="test:decision-determinism",
                evidence_refs=value.evidence_refs,
            )
        )
    return DecisionContextBuilder().build(_context(), ResearchStateView(store.freeze()))


@given(st.permutations((0, 1)))
def test_context_is_order_independent(order: tuple[int, ...]) -> None:
    assert _build(order) == _build((0, 1))
