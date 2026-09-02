from __future__ import annotations

from typing import get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

from research_os.contracts import AssumptionRef
from research_os.contracts.artifact_values import (
    CapitalEfficiency,
    CashFlowQualityBridge,
    ConsensusDistribution,
    DecisionStateRecord,
    DecisionStateProvenance,
    DriverGraph,
    ExpectationGap,
    ExpectationQualityAssessment,
    ExpectationSnapshot,
    FinancialTimeSeriesSet,
    ForecastEvaluation,
    FinancialValidation,
    FundingLoop,
    LineageValidation,
    MonitoringPlan,
    MethodologyDisclosure,
    NormalizedPeerSet,
    OperatingEvidenceSet,
    PriorRunReview,
    SemanticPreservation,
    SemanticSignalAssessment,
    SemanticClaims,
    SensitivitySet,
    ThesisPortfolio,
    ValuationExecution,
    ValuationReconciliation,
    ValuationResult,
    ValuationRouting,
)
from research_os.contracts.artifacts import ArtifactWrite
from research_os.contracts.errors import ArtifactTypeMismatchError
from research_os.contracts.metrics import MetricSet
from research_os.contracts.evidence import EvidenceRef, EvidenceSet
from research_os.domain.evidence import Evidence
from research_os.readiness.models import ResearchReadinessAssessment
from research_os.runtime.core_artifacts import (
    CORE_ARTIFACT_KEYS,
    FINANCIAL_FACT_SNAPSHOT,
    build_core_artifact_catalog,
)
from research_os.runtime.financial_snapshot import FinancialFactSnapshot
from research_os.plugins.resolver import StrategyResolution
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import BaselineFingerprint


def test_core_catalog_registers_every_strictly_typed_durable_artifact() -> None:
    catalog = build_core_artifact_catalog()

    expected_types = {
        "evidence.pit": EvidenceSet,
        "validation.lineage": LineageValidation,
        "financial.fact_snapshot": FinancialFactSnapshot,
        "business_model.profile": BusinessModelProfile,
        "strategy.resolution": StrategyResolution,
        "kpi.metrics": MetricSet,
        "financial.time_series": FinancialTimeSeriesSet,
        "research.operating_evidence": OperatingEvidenceSet,
        "expectation.consensus_distribution": ConsensusDistribution,
        "scenario.sensitivities": SensitivitySet,
        "methodology.disclosure": MethodologyDisclosure,
        "capital.efficiency": CapitalEfficiency,
        "capital.funding_loop": FundingLoop,
        "drivers.graph": DriverGraph,
        "thesis.portfolio": ThesisPortfolio,
        "thesis.semantic_signal_assessment": SemanticSignalAssessment,
        "semantic.claims": SemanticClaims,
        "expectation.snapshot": ExpectationSnapshot,
        "expectation.quality": ExpectationQualityAssessment,
        "expectation.gap": ExpectationGap,
        "forecast.evaluation": ForecastEvaluation,
        "peers.normalized": NormalizedPeerSet,
        "valuation.routing": ValuationRouting,
        "valuation.execution": ValuationExecution,
        "valuation.result": ValuationResult,
        "valuation.reconciliation": ValuationReconciliation,
        "decision.record": DecisionStateRecord,
        "decision.state_provenance": DecisionStateProvenance,
        "monitoring.plan": MonitoringPlan,
        "research.readiness": ResearchReadinessAssessment,
        "validation.repository_preflight": BaselineFingerprint,
        "validation.financial": FinancialValidation,
        "cash_flow.quality_bridge": CashFlowQualityBridge,
        "monitoring.prior_run_review": PriorRunReview,
        "semantic.preservation": SemanticPreservation,
        "validation.semantic_preservation": SemanticPreservation,
    }
    actual_types = {key.artifact_id: key.value_type for key in CORE_ARTIFACT_KEYS}

    assert len(actual_types) == len(CORE_ARTIFACT_KEYS)
    assert actual_types == expected_types
    for key in CORE_ARTIFACT_KEYS:
        value_type = expected_types[key.artifact_id]
        assert key.schema_version == "2.0"
        assert key.value_type is value_type
        assert key.value_type is not object
        assert catalog.definition(key).key is key


def test_core_catalog_keys_reject_a_value_outside_their_runtime_type() -> None:
    catalog = build_core_artifact_catalog()

    with pytest.raises(ArtifactTypeMismatchError):
        ArtifactWrite(
            key=FINANCIAL_FACT_SNAPSHOT,
            value=FinancialValidation(validation_status="PASS"),
            producer_id="test:producer",
        )

    assert catalog.definition(FINANCIAL_FACT_SNAPSHOT).key.value_type is FinancialFactSnapshot

    evidence_key = next(
        key for key in CORE_ARTIFACT_KEYS if key.artifact_id == "evidence.pit"
    )
    with pytest.raises(ArtifactTypeMismatchError):
        ArtifactWrite(
            key=evidence_key,
            value=("not-evidence", 42),
            producer_id="test:producer",
        )


def _lineage_field_names(
    model: type[BaseModel], seen: set[type[BaseModel]] | None = None
) -> set[str]:
    seen = set() if seen is None else seen
    if model in seen:
        return set()
    seen.add(model)
    names = set(model.model_fields)
    for field in model.model_fields.values():
        candidates = (field.annotation, *get_args(field.annotation))
        for candidate in candidates:
            origin = get_origin(candidate)
            nested_candidates = get_args(candidate) if origin is not None else (candidate,)
            for nested in nested_candidates:
                if isinstance(nested, type) and issubclass(nested, BaseModel):
                    if nested in {Evidence, EvidenceRef, AssumptionRef}:
                        continue
                    names.update(_lineage_field_names(nested, seen.copy()))
    return names


def test_registered_v2_artifact_types_have_no_id_only_lineage_fields() -> None:
    forbidden = {"evidence_id", "evidence_ids", "assumption_id", "assumption_ids"}
    offenders = {
        key.artifact_id: sorted(forbidden & _lineage_field_names(key.value_type))
        for key in CORE_ARTIFACT_KEYS
        if isinstance(key.value_type, type)
        and issubclass(key.value_type, BaseModel)
        and forbidden & _lineage_field_names(key.value_type)
    }

    assert offenders == {}


def test_assumption_ref_is_versioned_and_content_bound() -> None:
    reference = AssumptionRef(
        assumption_key="assumption:revenue-growth",
        assumption_version="1.0.0",
        content_fingerprint="a" * 64,
    )

    assert reference.assumption_key == "assumption:revenue-growth"
    with pytest.raises(ValidationError, match="content_fingerprint"):
        AssumptionRef(
            assumption_key="assumption:revenue-growth",
            assumption_version="1.0.0",
            content_fingerprint="not-a-fingerprint",
        )
