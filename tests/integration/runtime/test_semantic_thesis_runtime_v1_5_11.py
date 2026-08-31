from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.professional_modules import ProfessionalDriverThesisModule
from research_os.thesis.semantic_service_v1_5_11 import SemanticThesisService
from research_os.thesis.semantic_signals import GrowthComparisonRule


def test_professional_driver_thesis_module_uses_current_semantic_service():
    rule = GrowthComparisonRule(
        rule_id="explicit-working-capital-spread",
        left_metric="ar_growth",
        right_metric="revenue_growth",
        spread_threshold=0.10,
        adverse_label="应收增速显著快于收入",
    )
    inputs = ResearchInputs(thesis_comparison_rules=(rule,))
    module = ProfessionalDriverThesisModule(inputs=inputs)

    assert module.spec.module_version == "1.4.0"
    assert isinstance(module.theses, SemanticThesisService)
    assert module.theses.comparison_rules == (rule,)
    assert module.theses.prior_theses == ()
    assert "thesis.semantic_signal_assessment" in module.spec.provides


def test_prior_theses_are_explicit_runtime_inputs_not_inferred_from_current_evidence():
    inputs = ResearchInputs()
    module = ProfessionalDriverThesisModule(inputs=inputs)
    assert module.theses.prior_theses == ()
