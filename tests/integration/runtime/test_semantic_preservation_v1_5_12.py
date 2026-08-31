from datetime import datetime, timezone

import pytest

from research_os.completeness.models import (
    MonitoringRule,
    ScenarioAssumption,
    SensitivityCase,
)
from research_os.domain.evidence import Evidence
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchInputs,
    ResearchOptions,
)
from research_os.runtime.factory import ResearchRuntimeFactory
from research_os.reporting.composer_v1_5_12 import ResearchReportComposer
from research_os.reporting.research_view_v1_5_12 import ResearchViewPresenter
from research_os.reporting.markdown_renderer_v1_5_12 import (
    ResearchReportMarkdownRenderer,
)
from research_os.semantics.claims import ClaimSupport, MoatEvidence
from research_os.semantics.preservation import SemanticPreservationValidator


def _context() -> ResearchContext:
    publish_ts = datetime(2026, 8, 1, tzinfo=timezone.utc)
    facts = {"business_description": "precision manufacturing", "revenue": 1000.0}
    evidence = [
        Evidence(
            evidence_id=f"ev:{key}",
            company_id="synthetic:manufacturer",
            evidence_type="filing_fact",
            publish_ts=publish_ts,
            ingested_at=publish_ts,
            value=value,
            source_table=key,
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        )
        for key, value in facts.items()
    ]
    return ResearchContext(
        run_id="run:semantic-preservation",
        company=CompanyRef(company_id="synthetic:manufacturer"),
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version="1.5.12",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(
            values=facts,
            evidence_by_fact={key: [f"ev:{key}"] for key in facts},
        ),
        options=ResearchOptions(),
    )


def _inputs() -> ResearchInputs:
    return ResearchInputs(
        sensitivities=(
            SensitivityCase(
                case_id="raw-material-up",
                driver_id="raw_material_price",
                shock_label="raw material +5%",
                shock_value=0.05,
                affected_metric="gross_margin",
                result=-0.02,
                formula_version="sensitivity@1",
                material_assumptions=(
                    ScenarioAssumption(
                        assumption_id="assumption:price",
                        label="selling price remains constant",
                        value=True,
                        source_type="analyst_assumption",
                    ),
                ),
                model_boundary="mechanical sensitivity, not a forecast",
                applicability="one reporting period with unchanged volume and mix",
            ),
        ),
        monitoring_rules=(
            MonitoringRule(
                rule_id="margin-watch",
                metric="gross_margin",
                operator="gte",
                threshold=0.25,
                frequency="quarterly",
                rationale="research warning line for margin recovery",
                source_type="analyst_assumption",
                threshold_type="analyst_defined_monitoring",
                threshold_source="analyst monitoring policy",
                comparison_basis="quarterly reported gross margin",
                applicability="consolidated manufacturing operations",
            ),
        ),
        versions={
            "dataset_version": "synthetic@1",
            "parser_version": "synthetic@1",
            "formula_version": "synthetic@1",
            "report_version": "semantic-preservation@1",
        },
    )


def test_active_runtime_emits_semantic_preservation_validation_and_fingerprints():
    result = ResearchRuntimeFactory.default().run_context(_context(), _inputs())

    validation = result.artifacts["validation.semantic_preservation"]
    assert validation.status == "PASS"
    assert validation.sensitivity_fingerprint
    assert validation.monitoring_fingerprint
    assert result.module_results["semantic:preservation"].status == "PASS"


def test_historical_v1_5_10_runtime_does_not_gain_v1_5_12_semantic_module():
    result = ResearchRuntimeFactory.historical_v1_5_10().run_context(_context(), _inputs())

    assert "semantic:preservation" not in result.module_results
    assert "validation.semantic_preservation" not in result.artifacts


def test_sensitivity_semantic_fingerprint_survives_result_view_and_document():
    result = ResearchRuntimeFactory.default().run_context(_context(), _inputs())
    validation = result.artifacts["validation.semantic_preservation"]

    view = ResearchViewPresenter().build(result)
    document = ResearchReportComposer().compose(view)
    section = next(item for item in document.sections if item.section_id == "sensitivity-scenarios")
    block = section.blocks[0]

    assert SemanticPreservationValidator.sensitivity_fingerprint(
        view.research_completeness["scenario.sensitivities"]
    ) == validation.sensitivity_fingerprint
    assert block.semantic_fingerprint == validation.sensitivity_fingerprint


def test_document_fingerprints_the_actual_sensitivity_and_monitoring_payloads():
    result = ResearchRuntimeFactory.default().run_context(_context(), _inputs())
    validation = result.artifacts["validation.semantic_preservation"]
    view = ResearchViewPresenter().build(result)
    document = ResearchReportComposer().compose(view)

    sensitivity = next(
        item for item in document.sections if item.section_id == "sensitivity-scenarios"
    ).blocks[0]
    monitoring = next(
        item for item in document.sections if item.section_id == "monitoring-calendar"
    ).blocks[0]

    assert (
        SemanticPreservationValidator.sensitivity_fingerprint(sensitivity.payload)
        == sensitivity.semantic_fingerprint
        == validation.sensitivity_fingerprint
    )
    assert (
        SemanticPreservationValidator.monitoring_fingerprint(monitoring.payload)
        == monitoring.semantic_fingerprint
        == validation.monitoring_fingerprint
    )


def test_document_composition_fails_closed_if_a_sensitivity_qualifier_is_dropped():
    class DroppingQualifierComposer(ResearchReportComposer):
        @classmethod
        def _display_payload(cls, value):
            payload = super()._display_payload(value)
            if isinstance(payload, dict):
                payload.pop("model_boundary", None)
            return payload

    result = ResearchRuntimeFactory.default().run_context(_context(), _inputs())
    view = ResearchViewPresenter().build(result)

    with pytest.raises(ValueError, match="sensitivity semantic fingerprint mismatch"):
        DroppingQualifierComposer().compose(view)


def test_presenter_requires_semantic_validation_for_protected_payloads():
    result = ResearchRuntimeFactory.default().run_context(_context(), _inputs())
    artifacts = dict(result.artifacts)
    artifacts.pop("validation.semantic_preservation")
    artifacts.pop("semantic.preservation")
    unvalidated = result.model_copy(update={"artifacts": artifacts})

    with pytest.raises(ValueError, match="semantic preservation validation is required"):
        ResearchViewPresenter().build(unvalidated)


@pytest.mark.parametrize(
    "fingerprint_field",
    ("sensitivity_fingerprint", "monitoring_fingerprint"),
)
def test_presenter_requires_every_expected_protected_fingerprint(fingerprint_field):
    result = ResearchRuntimeFactory.default().run_context(_context(), _inputs())
    artifacts = dict(result.artifacts)
    validation = artifacts["validation.semantic_preservation"].model_copy(
        update={fingerprint_field: None}
    )
    artifacts["validation.semantic_preservation"] = validation
    artifacts["semantic.preservation"] = validation
    incomplete = result.model_copy(update={"artifacts": artifacts})

    with pytest.raises(ValueError, match="semantic fingerprint is required"):
        ResearchViewPresenter().build(incomplete)


@pytest.mark.parametrize(
    "fingerprint_field",
    ("sensitivity_fingerprint", "monitoring_fingerprint"),
)
def test_composer_requires_passed_validation_and_every_protected_fingerprint(
    fingerprint_field,
):
    result = ResearchRuntimeFactory.default().run_context(_context(), _inputs())
    view = ResearchViewPresenter().build(result)
    preservation = dict(view.semantic_preservation or {})
    preservation[fingerprint_field] = None
    incomplete = view.model_copy(update={"semantic_preservation": preservation})

    with pytest.raises(ValueError, match="semantic fingerprint is required"):
        ResearchReportComposer().compose(incomplete)

    unvalidated = view.model_copy(update={"semantic_preservation": None})
    with pytest.raises(ValueError, match="semantic preservation validation is required"):
        ResearchReportComposer().compose(unvalidated)


def test_active_view_refuses_invalid_result_bearing_sensitivity():
    invalid = ResearchInputs(
        sensitivities=(
            SensitivityCase(
                case_id="unqualified-result",
                driver_id="raw_material_price",
                shock_label="raw material +5%",
                affected_metric="gross_margin",
                result=-0.02,
                formula_version="sensitivity@1",
            ),
        ),
        versions=_inputs().versions,
    )
    result = ResearchRuntimeFactory.default().run_context(_context(), invalid)

    with pytest.raises(ValueError, match="semantic preservation validation failed"):
        ResearchViewPresenter().build(result)


def test_moat_and_cycle_semantics_survive_into_investor_facing_markdown():
    raw = _inputs().model_dump(mode="python")
    raw.update(
        cycle_recovery_observed=True,
        cycle_turning_point_support=ClaimSupport(
            evidence_count=1,
            evidence_quality=0.90,
            comparable=True,
        ),
        moat_evidence=(
            MoatEvidence(
                evidence_type="technical_barrier",
                evidence_ids=("ev:technical",),
            ),
            MoatEvidence(
                evidence_type="qualification_barrier",
                evidence_ids=("ev:qualification",),
            ),
        ),
    )
    result = ResearchRuntimeFactory.default().run_context(
        _context(), ResearchInputs.model_validate(raw)
    )

    assert result.artifacts["semantic.cycle_assessment"].state == "TROUGH_UNCONFIRMED"
    assert result.artifacts["semantic.moat_assessment"].state == "TECHNICAL_BARRIER_EVIDENCED"

    view = ResearchViewPresenter().build(result)
    document = ResearchReportComposer().compose(view)
    text = ResearchReportMarkdownRenderer().render(document)

    assert "周期底部未确认" in text
    assert "技术壁垒有证据" in text
    assert "不等同于已实现经济护城河" in text


def test_no_recovery_signal_remains_explicit_in_investor_facing_markdown():
    raw = _inputs().model_dump(mode="python")
    raw.update(
        cycle_recovery_observed=False,
        cycle_turning_point_support=ClaimSupport(
            evidence_count=1,
            evidence_quality=0.90,
            comparable=True,
        ),
    )
    result = ResearchRuntimeFactory.default().run_context(
        _context(), ResearchInputs.model_validate(raw)
    )

    assert result.artifacts["semantic.cycle_assessment"].state == "RECOVERY_NOT_OBSERVED"
    view = ResearchViewPresenter().build(result)
    document = ResearchReportComposer().compose(view)
    text = ResearchReportMarkdownRenderer().render(document)

    assert "尚未观察到修复迹象" in text
    assert "修复迹象已观察" not in text
