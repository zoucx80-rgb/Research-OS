from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from research_os.completion.models import ExecutionCompletionResult
from research_os.contracts.artifacts import (
    ArtifactCatalog,
    ArtifactDefinition,
    ArtifactKey,
    ArtifactMode,
    ArtifactStore,
    ArtifactWrite,
)
from research_os.contracts.artifact_values import (
    AssumptionRef,
    CashFlowQualityBridge,
    ConsensusDistribution,
    ConsensusObservation,
    FinancialSeriesPoint,
    FinancialTimeSeries,
    FinancialTimeSeriesSet,
    MethodologyDisclosure,
    PriorRunReview,
    SensitivityCase,
    SensitivitySet,
)
from research_os.contracts.evidence import EvidenceRef
from research_os.readiness import (
    ReadinessRequirement,
    ResearchReadinessAssessment,
    ResearchReadinessEvaluator,
)
from research_os.runtime.core_artifacts import (
    CASH_FLOW_QUALITY_BRIDGE,
    EXPECTATION_CONSENSUS_DISTRIBUTION,
    FINANCIAL_TEMPORAL_ANALYSIS,
    FINANCIAL_TIME_SERIES,
    MONITORING_PRIOR_RUN_REVIEW,
    build_core_artifact_catalog,
)
from research_os.temporal.models import FinancialTemporalAnalysis, MetricTemporalAssessment


EVIDENCE = ArtifactKey("synthetic.readiness", "2.0", tuple)


def _evidence_ref() -> EvidenceRef:
    return EvidenceRef(
        evidence_id="ev:readiness",
        revision=1,
        content_fingerprint="a" * 64,
    )


def _snapshot(*, present: bool, lineage: bool = True):
    catalog = ArtifactCatalog()
    catalog.register(ArtifactDefinition(EVIDENCE, ArtifactMode.EXCLUSIVE))
    store = ArtifactStore(catalog)
    if present:
        store.write(
            ArtifactWrite(
                EVIDENCE,
                ("supported",),
                "synthetic:provider",
                evidence_refs=(_evidence_ref(),) if lineage else (),
            )
        )
    return store.freeze()


def _completion(status: str = "COMPLETE") -> ExecutionCompletionResult:
    return ExecutionCompletionResult(
        final_status=status,
        blocking_capabilities=() if status == "COMPLETE" else ("core:pit",),
        module_statuses={"core:pit": "PASS" if status == "COMPLETE" else "INSUFFICIENT_EVIDENCE"},
    )


def _evaluator() -> ResearchReadinessEvaluator:
    return ResearchReadinessEvaluator(
        requirements=(
            ReadinessRequirement(
                dimension_id="time_series",
                artifact_keys=(EVIDENCE,),
            ),
        )
    )


def test_readiness_is_independent_and_cannot_override_incomplete_execution():
    completion = _completion("INCOMPLETE")
    assessment = _evaluator().evaluate(completion, _snapshot(present=True))

    assert completion.final_status == "INCOMPLETE"
    assert assessment.final_status == "NOT_READY"
    assert assessment.blocking_dimensions == ("execution_completion",)


def test_missing_evidence_blocks_without_a_typed_not_applicable_artifact():
    evaluator = _evaluator()

    missing = evaluator.evaluate(_completion(), _snapshot(present=False))

    assert missing.final_status == "NOT_READY"
    assert missing.blocking_dimensions == ("time_series",)


def test_substantive_artifact_without_lineage_cannot_be_ready():
    assessment = _evaluator().evaluate(
        _completion(),
        _snapshot(present=True, lineage=False),
    )

    assert assessment.final_status == "NOT_READY"
    assert assessment.blocking_dimensions == ("time_series",)


def test_explicit_assumption_ref_can_support_readiness_without_evidence():
    assumption = AssumptionRef(
        assumption_key="assumption:sensitivity",
        assumption_version="1.0.0",
        content_fingerprint="b" * 64,
    )
    case = SensitivityCase(
        case_key="case:downside",
        driver_key="revenue-growth",
        shock_label="revenue -10%",
        affected_metric="equity_value",
        formula_version="sensitivity@2.0.0",
        result=-0.2,
        assumption_refs=(assumption,),
    )
    catalog = ArtifactCatalog()
    sensitivity_key = ArtifactKey("scenario.sensitivities", "2.0", SensitivitySet)
    catalog.register(ArtifactDefinition(sensitivity_key, ArtifactMode.EXCLUSIVE))
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            sensitivity_key,
            SensitivitySet(domain_status="SUPPORTED", cases=(case,)),
            "core:sensitivity",
        )
    )
    evaluator = ResearchReadinessEvaluator(
        requirements=(
            ReadinessRequirement(
                dimension_id="sensitivity",
                artifact_keys=(sensitivity_key,),
            ),
        )
    )

    assessment = evaluator.evaluate(_completion(), store.freeze())

    assert assessment.final_status == "READY"


def test_value_embedded_evidence_ref_does_not_replace_envelope_lineage():
    case = SensitivityCase(
        case_key="case:downside",
        driver_key="revenue-growth",
        shock_label="revenue -10%",
        affected_metric="equity_value",
        formula_version="sensitivity@2.0.0",
        result=-0.2,
        evidence_refs=(_evidence_ref(),),
    )
    key = ArtifactKey("scenario.sensitivities", "2.0", SensitivitySet)
    catalog = ArtifactCatalog()
    catalog.register(ArtifactDefinition(key, ArtifactMode.EXCLUSIVE))
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            key,
            SensitivitySet(domain_status="SUPPORTED", cases=(case,)),
            "core:sensitivity",
        )
    )
    evaluator = ResearchReadinessEvaluator(
        requirements=(ReadinessRequirement("sensitivity", (key,)),)
    )

    assessment = evaluator.evaluate(_completion(), store.freeze())

    assert assessment.final_status == "NOT_READY"


def test_insufficient_domain_status_cannot_pass_readiness_even_with_content_and_lineage():
    from datetime import datetime, timezone

    catalog = build_core_artifact_catalog()
    store = ArtifactStore(catalog)
    observation = ConsensusObservation(
        source_key="consensus:single",
        publish_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        forecast_period="2026FY",
        metric_id="net_profit",
        value=100.0,
        evidence_refs=(_evidence_ref(),),
    )
    store.write(
        ArtifactWrite(
            EXPECTATION_CONSENSUS_DISTRIBUTION,
            ConsensusDistribution(
                domain_status="INSUFFICIENT_EVIDENCE",
                metric_id="net_profit",
                forecast_period="2026FY",
                observations=(observation,),
                source_count=1,
            ),
            "core:expectation",
            evidence_refs=(_evidence_ref(),),
        )
    )
    evaluator = ResearchReadinessEvaluator(
        requirements=(
            ReadinessRequirement(
                "consensus",
                (EXPECTATION_CONSENSUS_DISTRIBUTION,),
            ),
        )
    )

    assessment = evaluator.evaluate(_completion(), store.freeze())

    assert assessment.final_status == "NOT_READY"
    assert assessment.dimensions[0].status == "INCOMPLETE"


def test_explicit_not_applicable_domain_status_needs_no_lineage():
    key = ArtifactKey("methodology.disclosure", "2.0", MethodologyDisclosure)
    catalog = ArtifactCatalog()
    catalog.register(ArtifactDefinition(key, ArtifactMode.EXCLUSIVE))
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            key,
            MethodologyDisclosure(domain_status="NOT_APPLICABLE"),
            "core:methodology",
        )
    )
    evaluator = ResearchReadinessEvaluator(
        requirements=(ReadinessRequirement("methodology", (key,)),)
    )

    assessment = evaluator.evaluate(_completion(), store.freeze())

    assert assessment.final_status == "READY"
    assert assessment.dimensions[0].status == "NOT_APPLICABLE"


def test_assessment_contract_rejects_incomplete_ready_combination():
    with pytest.raises(ValidationError, match="INCOMPLETE.*READY"):
        ResearchReadinessAssessment(
            final_status="READY",
            dimensions=(),
            blocking_dimensions=(),
            execution_status="INCOMPLETE",
        )


def test_standard_dimensions_are_bound_to_typed_artifact_requirements():
    assessment = ResearchReadinessEvaluator().evaluate(
        _completion(),
        _snapshot(present=False),
    )

    assert len(assessment.dimensions) == 9
    assert all(item.required_artifacts for item in assessment.dimensions)
    assert assessment.final_status == "NOT_READY"


def test_default_only_domain_objects_do_not_satisfy_readiness():
    catalog = build_core_artifact_catalog()
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            CASH_FLOW_QUALITY_BRIDGE,
            CashFlowQualityBridge(),
            "core:cash-flow",
        )
    )
    store.write(
        ArtifactWrite(
            MONITORING_PRIOR_RUN_REVIEW,
            PriorRunReview(),
            "core:prior-run-review",
        )
    )

    assessment = ResearchReadinessEvaluator().evaluate(
        _completion(),
        store.freeze(),
    )

    assert assessment.final_status == "NOT_READY"
    assert "cash_flow" in assessment.blocking_dimensions
    assert "prior_run_validation" in assessment.blocking_dimensions


def _temporal_readiness_snapshot(*, temporal_coverage: str):
    reference = _evidence_ref()
    catalog = build_core_artifact_catalog()
    store = ArtifactStore(catalog)
    store.write(
        ArtifactWrite(
            FINANCIAL_TIME_SERIES,
            FinancialTimeSeriesSet(
                domain_status="SUPPORTED",
                series=(
                    FinancialTimeSeries(
                        metric_id="revenue",
                        unit="CNY",
                        points=(
                            FinancialSeriesPoint(
                                period="2025FY",
                                period_end=datetime(2025, 12, 31, tzinfo=timezone.utc),
                                value=110,
                                evidence_refs=(reference,),
                            ),
                        ),
                    ),
                ),
                evidence_refs=(reference,),
            ),
            "core:financial",
            evidence_refs=(reference,),
        )
    )
    sufficient = temporal_coverage == "SUFFICIENT"
    store.write(
        ArtifactWrite(
            FINANCIAL_TEMPORAL_ANALYSIS,
            FinancialTemporalAnalysis(
                domain_status="SUPPORTED",
                assessments=(
                    MetricTemporalAssessment(
                        evidence_refs=(reference,),
                        metric_id="revenue",
                        unit="CNY",
                        point_count=2 if sufficient else 1,
                        comparable_point_count=2 if sufficient else 0,
                        comparison_status="PASS" if sufficient else "INSUFFICIENT_EVIDENCE",
                        reason_codes=() if sufficient else ("INSUFFICIENT_COMPARABLE_POINTS",),
                    ),
                ),
                temporal_coverage=temporal_coverage,
                evidence_refs=(reference,),
            ),
            "core:financial",
            evidence_refs=(reference,),
        )
    )
    return store.freeze()


def test_one_point_series_does_not_pass_time_series_readiness() -> None:
    assessment = ResearchReadinessEvaluator().evaluate(
        _completion(),
        _temporal_readiness_snapshot(temporal_coverage="INSUFFICIENT_EVIDENCE"),
    )

    dimension = next(item for item in assessment.dimensions if item.dimension_id == "time_series")
    assert dimension.status == "INCOMPLETE"
    assert dimension.required_artifacts == (
        "financial.time_series",
        "financial.temporal_analysis",
    )


def test_comparable_series_passes_time_series_dimension() -> None:
    assessment = ResearchReadinessEvaluator().evaluate(
        _completion(),
        _temporal_readiness_snapshot(temporal_coverage="SUFFICIENT"),
    )

    dimension = next(item for item in assessment.dimensions if item.dimension_id == "time_series")
    assert dimension.status == "PASS"
