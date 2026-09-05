from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from research_os.contracts.artifact_values import Thesis, ThesisPortfolio
from research_os.contracts.evidence import EvidenceRef
from research_os.decision.engine import DecisionEngine
from research_os.decision.models import (
    DecisionContext,
    DecisionDimensionAssessment,
    DecisionInputAssessment,
)


REFERENCE = EvidenceRef(evidence_id="ev:decision", revision=1, content_fingerprint="a" * 64)


def _assessment() -> DecisionInputAssessment:
    return DecisionInputAssessment(
        domain_status="SUPPORTED",
        dimensions=(
            DecisionDimensionAssessment(
                dimension="research_sufficiency",
                state="INSUFFICIENT_EVIDENCE",
                availability="AVAILABLE",
                artifact_ids=("research.sufficiency",),
                reason_codes=("FORECAST_GAP",),
                evidence_refs=(REFERENCE,),
            ),
        ),
        evidence_confidence=Decimal("0.9"),
        blocking_reason_codes=("forecast:FORECAST_GAP",),
        evidence_refs=(REFERENCE,),
    )


def _context(**updates: object) -> DecisionContext:
    thesis = Thesis(
        thesis_key="thesis:decision",
        company_id="synthetic:decision",
        title="Decision thesis",
        statement="Evidence supports the mechanism.",
        mechanism="Operating gains improve cash economics.",
        anti_thesis="Operating gains reverse.",
        status="strengthening",
        falsifier_statements=("Cash economics deteriorate.",),
        next_check_date=date(2026, 12, 31),
        confidence=0.9,
        claim_strength="STRONG",
        evidence_refs=(REFERENCE,),
    )
    values = {
        "company_id": "synthetic:decision",
        "fundamental_state": "IMPROVING",
        "valuation_state": "CHEAP",
        "expectation_state": "OVER_EXPECTED",
        "thesis_portfolio": ThesisPortfolio(primary=thesis, evidence_refs=(REFERENCE,)),
        "evidence_confidence": 0.9,
        "decision_ts": datetime(2026, 9, 5, tzinfo=timezone.utc),
        "forecast_state": "PASS",
        "sufficiency_state": "SUFFICIENT",
        "scenario_state": "AVAILABLE",
    }
    values.update(updates)
    return DecisionContext(**values)


def test_insufficient_sufficiency_blocks_conviction() -> None:
    record, derivation = DecisionEngine().evaluate_with_derivation(
        _context(sufficiency_state="INSUFFICIENT_EVIDENCE"),
        _assessment(),
    )

    assert record.state == "INSUFFICIENT_EVIDENCE"
    assert "RESEARCH_SUFFICIENCY_BLOCKED" in derivation.blocking_reason_codes
    assert derivation.output_state == record.state


def test_failed_forecast_cannot_produce_high_conviction() -> None:
    record, _ = DecisionEngine().evaluate_with_derivation(
        _context(forecast_state="FAIL"),
        _assessment(),
    )

    assert record.state not in {"HIGH_CONVICTION_WATCH", "ACCUMULATION_CANDIDATE"}
