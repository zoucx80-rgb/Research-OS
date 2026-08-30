from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .models import ConsensusVintage, ExpectationEvidence


class ExpectationAssessment(BaseModel):
    status: Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE"]
    errors: list[str] = Field(default_factory=list)
    surprise: float | None = None


class ExpectationQualityAssessment(BaseModel):
    status: Literal["ADEQUATE", "LOW", "UNKNOWN"]
    reason_codes: list[str] = Field(default_factory=list)
    age_days: int | None = None
    source_count: int | None = None
    source_quality: float | None = None


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

    def assess_consensus_quality(
        self,
        *,
        vintage: ConsensusVintage | None,
        decision_ts: datetime,
    ) -> ExpectationQualityAssessment:
        if vintage is None:
            return ExpectationQualityAssessment(
                status="UNKNOWN",
                reason_codes=["NO_CONSENSUS_VINTAGE"],
            )

        reasons: list[str] = []
        age_days = max(0, (decision_ts.date() - vintage.as_of.date()).days)
        if vintage.source_count is not None and vintage.source_count < 3:
            reasons.append("THIN_CONSENSUS")
        if vintage.source_quality is not None and vintage.source_quality < 0.5:
            reasons.append("LOW_SOURCE_QUALITY")
        if age_days > 90:
            reasons.append("STALE_CONSENSUS")
        if vintage.source_count is None and vintage.source_quality is None:
            reasons.append("CONSENSUS_METADATA_MISSING")

        status: Literal["ADEQUATE", "LOW", "UNKNOWN"]
        if any(code in reasons for code in ("THIN_CONSENSUS", "LOW_SOURCE_QUALITY", "STALE_CONSENSUS")):
            status = "LOW"
        elif "CONSENSUS_METADATA_MISSING" in reasons:
            status = "UNKNOWN"
        else:
            status = "ADEQUATE"
        return ExpectationQualityAssessment(
            status=status,
            reason_codes=reasons,
            age_days=age_days,
            source_count=vintage.source_count,
            source_quality=vintage.source_quality,
        )

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
