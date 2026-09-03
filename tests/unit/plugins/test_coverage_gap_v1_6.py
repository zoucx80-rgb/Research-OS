from research_os.plugins.models import CoverageGap


def test_business_model_ambiguity_is_a_first_class_coverage_gap() -> None:
    gap = CoverageGap(
        gap_type="business_model_ambiguity",
        business_model="unknown",
        reason="top business-model candidates are inside the policy gap",
        reason_code="BUSINESS_MODEL_UNRESOLVED",
        affected_capabilities=("industry_strategy",),
        fallback_available=True,
    )

    assert gap.gap_type == "business_model_ambiguity"
