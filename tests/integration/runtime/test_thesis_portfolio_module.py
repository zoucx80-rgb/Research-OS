from __future__ import annotations

from datetime import date, datetime, timezone

from research_os.contracts.artifact_values import Thesis
from research_os.application.plan import ThesisPortfolioModule
from research_os.contracts.artifacts import ArtifactStore
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
from research_os.runtime.core_artifacts import THESIS_PORTFOLIO, build_core_artifact_catalog
from research_os.runtime.state import ResearchStateView


def _context() -> ResearchContext:
    timestamp = datetime(2026, 9, 3, tzinfo=timezone.utc)
    return ResearchContext(
        run_id="run:thesis-portfolio",
        company=CompanyRef(company_id="synthetic:portfolio"),
        decision_ts=timestamp,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="a" * 40,
            research_os_version="1.6.0",
            core_api_version="2.0",
        ),
        evidence=EvidenceView((), company_id="synthetic:portfolio", decision_ts=timestamp),
        facts=FactView(
            company_id="synthetic:portfolio",
            decision_ts=timestamp,
            values={},
            evidence_refs_by_fact={},
            reporting_period=ReportingPeriod(),
            accounting_scope=AccountingScope(),
        ),
    )


def test_module_outputs_only_typed_thesis_portfolio_artifact() -> None:
    thesis = Thesis(
        thesis_key="thesis:a",
        company_id="synthetic:portfolio",
        title="A",
        statement="A",
        mechanism="A",
        anti_thesis="not A",
        status="active",
        falsifier_statements=("break",),
        next_check_date=date(2026, 12, 1),
        confidence=0.9,
        claim_strength="STRONG",
        evidence_refs=(EvidenceRef(evidence_id="ev:a", revision=1, content_fingerprint="a" * 64),),
    )
    module = ThesisPortfolioModule((thesis,))
    result = module.run(
        _context(), ResearchStateView(ArtifactStore(build_core_artifact_catalog()).freeze())
    )

    assert result.writes[0].key == THESIS_PORTFOLIO
    assert result.writes[0].value.primary == thesis
    assert all(write.key.artifact_id != "thesis.items" for write in result.writes)
