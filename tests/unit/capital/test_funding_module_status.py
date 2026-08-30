from datetime import datetime, timezone

from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.runtime.builtin_modules import FundingLoopModule
from research_os.runtime.state import ResearchStateView


def _context(facts):
    return ResearchContext(
        run_id="run:funding-status",
        company=CompanyRef(company_id="synthetic:funding"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version="1.4.0",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView([]),
        facts=LegacyFactView(values=facts, evidence_by_fact={}),
        options=ResearchOptions(),
    )


def test_unknown_funding_loop_is_insufficient_evidence():
    result = FundingLoopModule().run(_context({}), ResearchStateView({"kpi.metrics": []}))
    assert result.artifacts["capital.funding_loop"].funding_state == "unknown"
    assert result.status == "INSUFFICIENT_EVIDENCE"


def test_classified_funding_loop_is_pass():
    result = FundingLoopModule().run(
        _context({
            "delta_nwc": 10.0,
            "delta_revenue": 20.0,
                "delta_debt": 8.0,
                "delta_equity": 0.0,
                "external_equity_financing": 0.0,
                "delta_nwc_comparison_basis": "2026_vs_2025",
                "delta_revenue_comparison_basis": "2026_vs_2025",
                "delta_debt_comparison_basis": "2026_vs_2025",
                "external_equity_financing_comparison_basis": "2026_vs_2025",
                "operating_cash_flow": 2.0,
        }),
        ResearchStateView({"kpi.metrics": []}),
    )
    assert result.artifacts["capital.funding_loop"].funding_state == "debt_funded"
    assert result.status == "PASS"
