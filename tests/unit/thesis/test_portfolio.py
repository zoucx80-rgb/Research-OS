from __future__ import annotations

from datetime import date
import hashlib

from research_os.contracts.artifact_values import Thesis
from research_os.contracts.evidence import EvidenceRef
from research_os.thesis.portfolio import ThesisPortfolioBuilder


def _thesis(
    thesis_key: str,
    status: str,
    *,
    confidence: float = 0.8,
    evidence: bool = True,
) -> Thesis:
    references = (
        (
            EvidenceRef(
                evidence_id=f"ev:{thesis_key}",
                revision=1,
                content_fingerprint=hashlib.sha256(thesis_key.encode()).hexdigest(),
            ),
        )
        if evidence
        else ()
    )
    return Thesis(
        thesis_key=thesis_key,
        company_id="synthetic:portfolio",
        title=thesis_key,
        statement=f"statement {thesis_key}",
        mechanism=f"mechanism {thesis_key}",
        anti_thesis=f"anti {thesis_key}",
        status=status,
        falsifier_statements=("falsifier",),
        next_check_date=date(2026, 12, 1),
        confidence=confidence,
        claim_strength="STRONG" if evidence else "OBSERVED",
        evidence_refs=references,
    )


def test_portfolio_classifies_every_thesis_lifecycle_state() -> None:
    portfolio = ThesisPortfolioBuilder().build(
        (
            _thesis("a-primary", "strengthening", confidence=0.9),
            _thesis("b-support", "active", confidence=0.8),
            _thesis("c-conflict", "weakening"),
            _thesis("d-unresolved", "unresolved"),
            _thesis("e-falsified", "falsified"),
        )
    )

    assert portfolio.primary.thesis_key == "a-primary"
    assert tuple(item.thesis_key for item in portfolio.supporting) == ("b-support",)
    assert tuple(item.thesis_key for item in portfolio.conflicting) == ("c-conflict",)
    assert tuple(item.thesis_key for item in portfolio.unresolved) == ("d-unresolved",)
    assert tuple(item.thesis_key for item in portfolio.falsified) == ("e-falsified",)


def test_primary_selection_is_independent_of_input_order() -> None:
    theses = (
        _thesis("a", "active", confidence=0.8),
        _thesis("b", "strengthening", confidence=0.8),
        _thesis("c", "strengthening", confidence=0.9),
    )

    forward = ThesisPortfolioBuilder().build(theses)
    reverse = ThesisPortfolioBuilder().build(tuple(reversed(theses)))

    assert forward == reverse
    assert forward.primary.thesis_key == "c"


def test_primary_is_none_when_candidate_has_insufficient_evidence() -> None:
    portfolio = ThesisPortfolioBuilder().build(
        (_thesis("a", "active", confidence=0.95, evidence=False),)
    )

    assert portfolio.primary is None
    assert tuple(item.thesis_key for item in portfolio.supporting) == ("a",)
    assert portfolio.domain_status == "INSUFFICIENT_EVIDENCE"
