from research_os.completeness.models import (
    MonitoringRule,
    ScenarioAssumption,
    SensitivityCase,
)
from research_os.semantics.preservation import SemanticPreservationValidator


def test_result_bearing_sensitivity_requires_material_assumptions_and_boundary():
    case = SensitivityCase(
        case_id="raw-material-up",
        driver_id="raw_material_price",
        shock_label="raw material +5%",
        shock_value=0.05,
        affected_metric="gross_margin",
        result=-0.02,
        formula_version="sensitivity@1",
    )

    validation = SemanticPreservationValidator.validate(
        sensitivities=(case,),
        monitoring_rules=(),
    )

    assert validation.status == "FAIL"
    assert {item.code for item in validation.violations} == {
        "SENSITIVITY_APPLICABILITY_MISSING",
        "SENSITIVITY_ASSUMPTIONS_MISSING",
        "SENSITIVITY_MODEL_BOUNDARY_MISSING",
    }


def test_complete_sensitivity_preserves_material_assumptions():
    case = SensitivityCase(
        case_id="raw-material-up",
        driver_id="raw_material_price",
        shock_label="raw material +5%",
        shock_value=0.05,
        affected_metric="gross_margin",
        result=-0.02,
        formula_version="sensitivity@1",
        material_assumptions=(
            ScenarioAssumption(
                assumption_id="assumption:price-constant",
                label="selling price remains constant",
                value=True,
                source_type="analyst_assumption",
            ),
            ScenarioAssumption(
                assumption_id="assumption:pass-through",
                label="cost pass-through ratio",
                value=0.60,
                unit="ratio",
                source_type="analyst_assumption",
            ),
        ),
        model_boundary="mechanical sensitivity, not a forecast",
        applicability="applies only to the stated cost shock with unchanged volume and mix",
        caveats=("inventory accounting timing is unchanged",),
    )

    validation = SemanticPreservationValidator.validate(
        sensitivities=(case,),
        monitoring_rules=(),
    )

    assert validation.status == "PASS"
    assert validation.sensitivity_fingerprint


def test_monitoring_threshold_requires_type_source_basis_and_applicability():
    rule = MonitoringRule(
        rule_id="margin-watch",
        metric="gross_margin",
        operator="gte",
        threshold=0.25,
        frequency="quarterly",
        rationale="monitor product-mix economics",
        source_type="analyst_assumption",
    )

    validation = SemanticPreservationValidator.validate(
        sensitivities=(),
        monitoring_rules=(rule,),
    )

    assert validation.status == "FAIL"
    assert {item.code for item in validation.violations} == {
        "THRESHOLD_APPLICABILITY_MISSING",
        "THRESHOLD_COMPARISON_BASIS_MISSING",
        "THRESHOLD_SOURCE_MISSING",
        "THRESHOLD_TYPE_MISSING",
    }


def test_analyst_threshold_is_typed_as_research_monitoring_line():
    rule = MonitoringRule(
        rule_id="margin-watch",
        metric="gross_margin",
        operator="gte",
        threshold=0.25,
        frequency="quarterly",
        rationale="warn when recovery no longer supports the operating thesis",
        source_type="analyst_assumption",
        threshold_type="analyst_defined_monitoring",
        threshold_source="analyst monitoring policy",
        comparison_basis="quarterly reported gross margin",
        applicability="consolidated manufacturing operations",
        assumption_ids=("assumption:margin-watch",),
    )

    validation = SemanticPreservationValidator.validate(
        sensitivities=(),
        monitoring_rules=(rule,),
    )

    assert validation.status == "PASS"
    assert validation.monitoring_fingerprint


def test_semantic_fingerprint_is_stable_across_model_and_projected_dict():
    case = SensitivityCase(
        case_id="utilization-down",
        driver_id="capacity_utilization",
        shock_label="utilization -8pct",
        shock_value=-0.08,
        affected_metric="operating_margin",
        result_low=0.08,
        result_high=0.10,
        formula_version="sensitivity@1",
        material_assumptions=(
            ScenarioAssumption(
                assumption_id="assumption:fixed-cost",
                label="fixed cost remains unchanged",
                value=True,
                source_type="analyst_assumption",
            ),
        ),
        model_boundary="static operating-leverage scenario",
        applicability="one reporting period",
    )

    from_model = SemanticPreservationValidator.fingerprint((case,))
    from_projection = SemanticPreservationValidator.fingerprint(
        [case.model_dump(mode="python")]
    )

    assert from_model == from_projection
