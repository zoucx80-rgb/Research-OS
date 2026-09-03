from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib

from research_os.contracts.artifact_values import Thesis, ThesisPortfolio
from research_os.contracts.evidence import EvidenceRef
from research_os.decision.aggregation import DecisionAggregationPolicy
from research_os.decision.engine import DecisionEngine
from research_os.decision.models import DecisionContext


def _thesis(key: str, status: str) -> Thesis:
    return Thesis(
        thesis_key=key,
        company_id="synthetic:decision",
        title=key,
        statement=key,
        mechanism=key,
        anti_thesis=f"anti {key}",
        status=status,
        falsifier_statements=("falsifier",),
        next_check_date=date(2026, 12, 1),
        confidence=0.9,
        claim_strength="STRONG",
        evidence_refs=(
            EvidenceRef(
                evidence_id=f"ev:{key}",
                revision=1,
                content_fingerprint=hashlib.sha256(key.encode()).hexdigest(),
            ),
        ),
    )


def _context(portfolio: ThesisPortfolio, **updates: object) -> DecisionContext:
    values = {
        "company_id": "synthetic:decision",
        "fundamental_state": "IMPROVING",
        "valuation_state": "CHEAP",
        "expectation_state": "OVER_EXPECTED",
        "thesis_portfolio": portfolio,
        "evidence_confidence": 0.9,
        "claim_ids": ("claim:a", "claim:b"),
        "decision_ts": datetime(2026, 9, 3, tzinfo=timezone.utc),
        "material_funding_risk": False,
    }
    values.update(updates)
    return DecisionContext(**values)


def test_falsified_thesis_and_material_funding_risk_veto_high_conviction() -> None:
    primary = _thesis("p", "strengthening")
    falsified = _thesis("f", "falsified")
    broken = DecisionEngine().evaluate(
        _context(ThesisPortfolio(primary=primary, falsified=(falsified,)))
    )
    funding_risk = DecisionEngine().evaluate(
        _context(
            ThesisPortfolio(primary=primary),
            material_funding_risk=True,
        )
    )

    assert broken.state == "THESIS_BROKEN"
    assert funding_risk.state == "RISK_REVIEW"


def test_conflicting_or_unresolved_portfolio_waits_for_confirmation() -> None:
    primary = _thesis("p", "active")
    conflict = _thesis("c", "weakening")
    unresolved = _thesis("u", "unresolved")

    for portfolio in (
        ThesisPortfolio(primary=primary, conflicting=(conflict,)),
        ThesisPortfolio(primary=primary, unresolved=(unresolved,)),
    ):
        record = DecisionEngine().evaluate(_context(portfolio))
        assert record.state == "WAIT_FOR_CONFIRMATION"
        assert "PORTFOLIO_CONFLICT_UNRESOLVED" in record.reason_codes


def test_decision_record_preserves_all_used_thesis_claim_and_evidence_ids() -> None:
    primary = _thesis("p", "active")
    support = _thesis("s", "active")
    conflict = _thesis("c", "weakening")
    portfolio = ThesisPortfolio(
        primary=primary,
        supporting=(support,),
        conflicting=(conflict,),
    )

    record = DecisionEngine(aggregation_policy=DecisionAggregationPolicy()).evaluate(
        _context(portfolio)
    )

    assert record.used_thesis_ids == ("c", "p", "s")
    assert record.used_claim_ids == ("claim:a", "claim:b")
    assert tuple(item.evidence_id for item in record.evidence_refs) == (
        "ev:c",
        "ev:p",
        "ev:s",
    )
