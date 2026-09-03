from __future__ import annotations

from datetime import date, datetime, timezone

from research_os.contracts.artifact_values import Thesis, ThesisPortfolio
from research_os.application.plan import PortfolioDecisionModule
from research_os.contracts.artifacts import ArtifactStore, ArtifactWrite
from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.values import AccountingScope
from research_os.period.models import ReportingPeriod
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.runtime.core_artifacts import (
    DECISION_RECORD,
    THESIS_PORTFOLIO,
    build_core_artifact_catalog,
)
from research_os.runtime.state import ResearchStateView


def test_portfolio_decision_module_uses_every_thesis_and_revision_bound_reference() -> None:
    timestamp = datetime(2026, 9, 3, tzinfo=timezone.utc)
    reference = EvidenceRef(evidence_id="ev:primary", revision=1, content_fingerprint="a" * 64)
    thesis = Thesis(
        thesis_key="thesis:primary",
        company_id="synthetic:decision-module",
        title="Primary",
        statement="Primary",
        mechanism="Primary",
        anti_thesis="Not primary",
        status="strengthening",
        falsifier_statements=("break",),
        next_check_date=date(2026, 12, 1),
        confidence=0.9,
        claim_strength="STRONG",
        evidence_refs=(reference,),
    )
    portfolio = ThesisPortfolio(
        primary=thesis, domain_status="SUPPORTED", evidence_refs=(reference,)
    )
    catalog = build_core_artifact_catalog()
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            key=THESIS_PORTFOLIO,
            value=portfolio,
            producer_id="test:portfolio",
            evidence_refs=(reference,),
        )
    )
    context = ResearchContext(
        run_id="run:decision-module",
        company=CompanyRef(company_id="synthetic:decision-module"),
        decision_ts=timestamp,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.6.0",
            core_api_version="2.0",
        ),
        evidence=EvidenceView((), company_id="synthetic:decision-module", decision_ts=timestamp),
        facts=FactView(
            company_id="synthetic:decision-module",
            decision_ts=timestamp,
            values={},
            evidence_refs_by_fact={},
            reporting_period=ReportingPeriod(),
            accounting_scope=AccountingScope(),
        ),
    )
    module = PortfolioDecisionModule(
        fundamental_state="IMPROVING",
        valuation_state="CHEAP",
        expectation_state="OVER_EXPECTED",
        evidence_confidence=0.9,
        claim_ids=("claim:a",),
    )

    result = module.run(context, ResearchStateView(store.freeze()))
    record = next(write.value for write in result.writes if write.key == DECISION_RECORD)

    assert record.state == "HIGH_CONVICTION_WATCH"
    assert record.thesis_keys == ("thesis:primary",)
    assert record.claim_keys == ("claim:a",)
    assert record.evidence_refs == (reference,)
