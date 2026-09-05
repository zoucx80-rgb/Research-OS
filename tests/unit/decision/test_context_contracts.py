from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from research_os.contracts.artifact_values import ThesisPortfolio
from research_os.decision.models import (
    DecisionContext,
    DecisionDimensionAssessment,
    DecisionInputAssessment,
)


def _dimension(name: str) -> DecisionDimensionAssessment:
    return DecisionDimensionAssessment(
        dimension=name,
        state="INSUFFICIENT_EVIDENCE",
        availability="INSUFFICIENT_EVIDENCE",
        reason_codes=("MISSING",),
    )


def test_decision_assessment_rejects_duplicate_dimensions() -> None:
    item = _dimension("forecast")

    with pytest.raises(ValidationError, match="unique"):
        DecisionInputAssessment(
            dimensions=(item, item),
            evidence_confidence=Decimal("0.5"),
        )


def test_context_defaults_keep_existing_constructor_valid() -> None:
    context = DecisionContext(
        company_id="synthetic:decision",
        fundamental_state="UNCERTAIN",
        valuation_state="UNRELIABLE",
        expectation_state="UNKNOWN",
        thesis_portfolio=ThesisPortfolio(),
        evidence_confidence=0,
        decision_ts=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

    assert context.forecast_state == "UNKNOWN"
    assert context.sufficiency_state == "INSUFFICIENT_EVIDENCE"
    assert context.scenario_state == "UNAVAILABLE"


def test_assessment_requires_a_named_dimension() -> None:
    assessment = DecisionInputAssessment(
        dimensions=(_dimension("forecast"),),
        evidence_confidence=Decimal("0"),
    )

    assert assessment.require_dimension("forecast").dimension == "forecast"
    with pytest.raises(KeyError, match="missing decision dimension: valuation"):
        assessment.require_dimension("valuation")
