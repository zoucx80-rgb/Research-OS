from research_os.semantics.claims import (
    ClaimStrengthPolicy,
    ClaimSupport,
    CycleAssessment,
    MoatAssessment,
    MoatEvidence,
)


def test_material_missingness_caps_claim_at_observed():
    support = ClaimSupport(
        evidence_count=3,
        evidence_quality=0.95,
        comparable=True,
        material_missingness=True,
        independent_confirmation=True,
    )

    assert ClaimStrengthPolicy.assess(support) == "OBSERVED"


def test_non_comparable_evidence_cannot_be_confirmed():
    support = ClaimSupport(
        evidence_count=4,
        evidence_quality=0.95,
        comparable=False,
        independent_confirmation=True,
    )

    assert ClaimStrengthPolicy.assess(support) == "SUGGESTIVE"


def test_one_good_source_is_supported_but_not_strong():
    support = ClaimSupport(
        evidence_count=1,
        evidence_quality=0.90,
        comparable=True,
    )

    assert ClaimStrengthPolicy.assess(support) == "SUPPORTED"


def test_observed_recovery_does_not_confirm_cycle_trough():
    assessment = CycleAssessment.assess(
        recovery_observed=True,
        turning_point_support=ClaimSupport(
            evidence_count=1,
            evidence_quality=0.90,
            comparable=True,
        ),
    )

    assert assessment.state == "TROUGH_UNCONFIRMED"
    assert assessment.claim_strength == "SUPPORTED"


def test_cycle_trough_requires_independent_confirmation():
    assessment = CycleAssessment.assess(
        recovery_observed=True,
        turning_point_support=ClaimSupport(
            evidence_count=3,
            evidence_quality=0.90,
            comparable=True,
            independent_confirmation=True,
        ),
    )

    assert assessment.state == "TROUGH_CONFIRMED"
    assert assessment.claim_strength == "CONFIRMED"


def test_absent_recovery_signal_is_not_rendered_as_observed_recovery():
    assessment = CycleAssessment.assess(
        recovery_observed=False,
        turning_point_support=ClaimSupport(
            evidence_count=1,
            evidence_quality=0.90,
            comparable=True,
        ),
    )

    assert assessment.state == "RECOVERY_NOT_OBSERVED"
    assert assessment.recovery_observed is False


def test_technical_and_qualification_barriers_do_not_imply_realized_economic_moat():
    assessment = MoatAssessment.assess(
        (
            MoatEvidence(evidence_type="technical_barrier", evidence_ids=("ev:patent",)),
            MoatEvidence(evidence_type="qualification_barrier", evidence_ids=("ev:qualification",)),
        )
    )

    assert assessment.state == "TECHNICAL_BARRIER_EVIDENCED"
    assert assessment.economic_realization is False


def test_economic_moat_realization_requires_economic_outcome_evidence():
    without_outcomes = MoatAssessment.assess(
        (
            MoatEvidence(evidence_type="technical_barrier", evidence_ids=("ev:technical",)),
            MoatEvidence(evidence_type="customer_switching_cost", evidence_ids=("ev:switching",)),
            MoatEvidence(evidence_type="commercial_advantage", evidence_ids=("ev:commercial",)),
        )
    )
    with_outcomes = MoatAssessment.assess(
        (
            *without_outcomes.evidence,
            MoatEvidence(evidence_type="economic_outcome", evidence_ids=("ev:roic", "ev:margin")),
        )
    )

    assert without_outcomes.state == "ECONOMIC_MOAT_UNREALIZED"
    assert with_outcomes.state == "ECONOMIC_MOAT_REALIZED"
    assert with_outcomes.economic_realization is True


def test_qualification_barrier_is_not_mislabeled_as_technical_evidence():
    assessment = MoatAssessment.assess((MoatEvidence(evidence_type="qualification_barrier"),))

    assert assessment.state == "OTHER_BARRIER_EVIDENCED"


def test_non_barrier_evidence_is_insufficient_for_a_moat_claim():
    for evidence_type in ("economic_outcome", "commercial_advantage"):
        assessment = MoatAssessment.assess((MoatEvidence(evidence_type=evidence_type),))
        assert assessment.state == "INSUFFICIENT_MOAT_EVIDENCE"
