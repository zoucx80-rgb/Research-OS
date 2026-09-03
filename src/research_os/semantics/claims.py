from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field


ClaimStrength = Literal[
    "OBSERVED",
    "SUGGESTIVE",
    "SUPPORTED",
    "STRONG",
    "CONFIRMED",
]
CycleState = Literal[
    "RECOVERY_NOT_OBSERVED",
    "RECOVERY_OBSERVED",
    "TROUGH_UNCONFIRMED",
    "TROUGH_CONFIRMED",
]
MoatState = Literal[
    "INSUFFICIENT_MOAT_EVIDENCE",
    "OTHER_BARRIER_EVIDENCED",
    "TECHNICAL_BARRIER_EVIDENCED",
    "ECONOMIC_MOAT_UNREALIZED",
    "ECONOMIC_MOAT_REALIZED",
]


class ClaimSupport(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_count: int = Field(ge=0)
    evidence_quality: float = Field(ge=0, le=1)
    comparable: bool
    material_missingness: bool = False
    independent_confirmation: bool = False


class ClaimStrengthPolicy:
    """Fail-closed language ceiling derived from evidence support."""

    @staticmethod
    def assess(support: ClaimSupport) -> ClaimStrength:
        if support.evidence_count == 0 or support.material_missingness:
            return "OBSERVED"
        if not support.comparable:
            return "SUGGESTIVE"
        if support.evidence_quality < 0.5:
            return "SUGGESTIVE"
        if support.evidence_count == 1 or support.evidence_quality < 0.75:
            return "SUPPORTED"
        if support.independent_confirmation and support.evidence_quality >= 0.8:
            return "CONFIRMED"
        return "STRONG"


class CycleAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: CycleState
    claim_strength: ClaimStrength
    recovery_observed: bool

    @classmethod
    def assess(
        cls,
        *,
        recovery_observed: bool,
        turning_point_support: ClaimSupport,
    ) -> Self:
        strength = ClaimStrengthPolicy.assess(turning_point_support)
        state: CycleState
        if not recovery_observed:
            state = "RECOVERY_NOT_OBSERVED"
        elif strength == "CONFIRMED":
            state = "TROUGH_CONFIRMED"
        elif strength in {"SUPPORTED", "STRONG"}:
            state = "TROUGH_UNCONFIRMED"
        else:
            state = "RECOVERY_OBSERVED"
        return cls(
            state=state,
            claim_strength=strength,
            recovery_observed=recovery_observed,
        )


MoatEvidenceType = Literal[
    "technical_barrier",
    "qualification_barrier",
    "customer_switching_cost",
    "commercial_advantage",
    "economic_outcome",
]


class MoatEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_type: MoatEvidenceType
    evidence_ids: tuple[str, ...] = Field(default_factory=tuple)


class MoatAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: MoatState
    economic_realization: bool
    evidence: tuple[MoatEvidence, ...] = Field(default_factory=tuple)

    @classmethod
    def assess(cls, evidence: tuple[MoatEvidence, ...]) -> Self:
        evidence_types = {item.evidence_type for item in evidence}
        has_technical_barrier = "technical_barrier" in evidence_types
        has_other_barrier = bool(
            evidence_types & {"qualification_barrier", "customer_switching_cost"}
        )
        has_barrier = has_technical_barrier or has_other_barrier
        has_commercial = bool(
            evidence_types & {"customer_switching_cost", "commercial_advantage"}
        )
        has_economic_outcome = "economic_outcome" in evidence_types

        state: MoatState
        if has_barrier and has_commercial and has_economic_outcome:
            state = "ECONOMIC_MOAT_REALIZED"
            realized = True
        elif has_commercial:
            state = (
                "ECONOMIC_MOAT_UNREALIZED"
                if has_barrier
                else "INSUFFICIENT_MOAT_EVIDENCE"
            )
            realized = False
        elif has_technical_barrier:
            state = "TECHNICAL_BARRIER_EVIDENCED"
            realized = False
        elif has_other_barrier:
            state = "OTHER_BARRIER_EVIDENCED"
            realized = False
        else:
            state = "INSUFFICIENT_MOAT_EVIDENCE"
            realized = False
        return cls(
            state=state,
            economic_realization=realized,
            evidence=evidence,
        )
