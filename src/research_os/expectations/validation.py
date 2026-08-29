from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .models import ExpectationEvidence


class ExpectationAssessment(BaseModel):
    status: Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE"]
    errors: list[str] = Field(default_factory=list)
    surprise: float | None = None


_MARKET_EXPECTATION_TERMS = (
    "beat expectations",
    "miss expectations",
    "fully priced",
    "priced in",
    "expectation gap",
    "surprise",
    "超预期",
    "低于预期",
    "充分预期",
    "已经预期",
    "预期差",
)


class ExpectationEvidenceValidator:
    @staticmethod
    def _requires_baseline(conclusion: str | None) -> bool:
        if not conclusion:
            return False
        text = conclusion.lower()
        return any(term in text for term in _MARKET_EXPECTATION_TERMS)

    def assess(
        self,
        *,
        conclusion: str | None,
        evidence: ExpectationEvidence | None,
        decision_ts: datetime,
    ) -> ExpectationAssessment:
        requires_baseline = self._requires_baseline(conclusion)
        if evidence is None:
            if requires_baseline:
                return ExpectationAssessment(status="FAIL", errors=["expectation conclusion lacks traceable baseline"])
            return ExpectationAssessment(status="INSUFFICIENT_EVIDENCE")

        errors: list[str] = []
        if evidence.expectation_publish_ts > decision_ts:
            errors.append("expectation evidence violates PIT: publish_ts > decision_ts")
        if not evidence.expectation_source.strip() or not evidence.expectation_period.strip() or not evidence.metric.strip() or not evidence.vintage.strip():
            errors.append("expectation evidence is missing required lineage fields")
        computed = evidence.actual_value - evidence.expected_value
        if not math.isclose(computed, evidence.surprise, rel_tol=1e-9, abs_tol=1e-9):
            errors.append("expectation surprise does not match actual - expected")

        text = (conclusion or "").lower()
        if "beat" in text or "超预期" in text:
            if evidence.surprise <= 0:
                errors.append("beat conclusion is inconsistent with surprise sign")
        if "miss" in text or "低于预期" in text:
            if evidence.surprise >= 0:
                errors.append("miss conclusion is inconsistent with surprise sign")

        return ExpectationAssessment(status="FAIL" if errors else "PASS", errors=errors, surprise=evidence.surprise)
