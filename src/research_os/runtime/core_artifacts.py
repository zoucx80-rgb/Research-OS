"""Central registrations for current durable Core API 2.0 artifacts."""

from __future__ import annotations

from typing import cast

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
    ForecastEvaluation,
    FinancialValidation,
    FinancialTimeSeriesSet,
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
from research_os.contracts.artifacts import (
    ArtifactCatalog,
    ArtifactDefinition,
    ArtifactKey,
    ArtifactMode,
)
from research_os.contracts.metrics import MetricSet
from research_os.decision.models import DecisionDerivation, DecisionInputAssessment
from research_os.forecasting.contracts import ForecastBenchmarkEvidence
from research_os.valuation.market import PitMarketAnchor, ValuationMarketGap
from research_os.plugins.models import StrategyResolution
from research_os.readiness.models import ResearchReadinessAssessment
from research_os.router.models import BusinessModelProfile
from research_os.runtime.context import BaselineFingerprint
from research_os.runtime.financial_snapshot import EVIDENCE_PIT, FINANCIAL_FACT_SNAPSHOT
from research_os.sufficiency.models import ResearchSufficiencyAssessment
from research_os.temporal.models import FinancialTemporalAnalysis


_SCHEMA_VERSION = "2.0"

REPOSITORY_PREFLIGHT = ArtifactKey(
    artifact_id="validation.repository_preflight",
    schema_version=_SCHEMA_VERSION,
    value_type=BaselineFingerprint,
)
BUSINESS_MODEL_PROFILE = ArtifactKey(
    artifact_id="business_model.profile",
    schema_version=_SCHEMA_VERSION,
    value_type=BusinessModelProfile,
)
STRATEGY_RESOLUTION = ArtifactKey(
    artifact_id="strategy.resolution",
    schema_version=_SCHEMA_VERSION,
    value_type=StrategyResolution,
)
KPI_METRICS = ArtifactKey(
    artifact_id="kpi.metrics",
    schema_version=_SCHEMA_VERSION,
    value_type=MetricSet,
)
FINANCIAL_TIME_SERIES = ArtifactKey(
    artifact_id="financial.time_series",
    schema_version=_SCHEMA_VERSION,
    value_type=FinancialTimeSeriesSet,
)
FINANCIAL_TEMPORAL_ANALYSIS = ArtifactKey(
    artifact_id="financial.temporal_analysis",
    schema_version=_SCHEMA_VERSION,
    value_type=FinancialTemporalAnalysis,
)
RESEARCH_OPERATING_EVIDENCE = ArtifactKey(
    artifact_id="research.operating_evidence",
    schema_version=_SCHEMA_VERSION,
    value_type=OperatingEvidenceSet,
)
RESEARCH_SUFFICIENCY = ArtifactKey(
    artifact_id="research.sufficiency",
    schema_version=_SCHEMA_VERSION,
    value_type=ResearchSufficiencyAssessment,
)
EXPECTATION_CONSENSUS_DISTRIBUTION = ArtifactKey(
    artifact_id="expectation.consensus_distribution",
    schema_version=_SCHEMA_VERSION,
    value_type=ConsensusDistribution,
)
SCENARIO_SENSITIVITIES = ArtifactKey(
    artifact_id="scenario.sensitivities",
    schema_version=_SCHEMA_VERSION,
    value_type=SensitivitySet,
)
METHODOLOGY_DISCLOSURE = ArtifactKey(
    artifact_id="methodology.disclosure",
    schema_version=_SCHEMA_VERSION,
    value_type=MethodologyDisclosure,
)
VALIDATION_LINEAGE = ArtifactKey(
    artifact_id="validation.lineage",
    schema_version=_SCHEMA_VERSION,
    value_type=LineageValidation,
)
DRIVERS_GRAPH = ArtifactKey(
    artifact_id="drivers.graph",
    schema_version=_SCHEMA_VERSION,
    value_type=DriverGraph,
)
THESIS_PORTFOLIO = ArtifactKey(
    artifact_id="thesis.portfolio",
    schema_version=_SCHEMA_VERSION,
    value_type=ThesisPortfolio,
)
THESIS_SEMANTIC_SIGNAL_ASSESSMENT = ArtifactKey(
    artifact_id="thesis.semantic_signal_assessment",
    schema_version=_SCHEMA_VERSION,
    value_type=SemanticSignalAssessment,
)
SEMANTIC_CLAIMS = ArtifactKey(
    artifact_id="semantic.claims",
    schema_version=_SCHEMA_VERSION,
    value_type=SemanticClaims,
)
EXPECTATION_SNAPSHOT = ArtifactKey(
    artifact_id="expectation.snapshot",
    schema_version=_SCHEMA_VERSION,
    value_type=ExpectationSnapshot,
)
EXPECTATION_GAP = ArtifactKey(
    artifact_id="expectation.gap",
    schema_version=_SCHEMA_VERSION,
    value_type=ExpectationGap,
)
FORECAST_EVALUATION = ArtifactKey(
    artifact_id="forecast.evaluation",
    schema_version=_SCHEMA_VERSION,
    value_type=ForecastEvaluation,
)
FORECAST_BENCHMARK_EVIDENCE = ArtifactKey(
    artifact_id="forecast.benchmark_evidence",
    schema_version=_SCHEMA_VERSION,
    value_type=ForecastBenchmarkEvidence,
)
PEERS_NORMALIZED = ArtifactKey(
    artifact_id="peers.normalized",
    schema_version=_SCHEMA_VERSION,
    value_type=NormalizedPeerSet,
)
VALUATION_ROUTING = ArtifactKey(
    artifact_id="valuation.routing",
    schema_version=_SCHEMA_VERSION,
    value_type=ValuationRouting,
)
VALUATION_EXECUTION = ArtifactKey(
    artifact_id="valuation.execution",
    schema_version=_SCHEMA_VERSION,
    value_type=ValuationExecution,
)
VALUATION_RESULT = ArtifactKey(
    artifact_id="valuation.result",
    schema_version=_SCHEMA_VERSION,
    value_type=ValuationResult,
)
VALUATION_RECONCILIATION = ArtifactKey(
    artifact_id="valuation.reconciliation",
    schema_version=_SCHEMA_VERSION,
    value_type=ValuationReconciliation,
)
VALUATION_MARKET_ANCHOR = ArtifactKey(
    artifact_id="valuation.market_anchor",
    schema_version=_SCHEMA_VERSION,
    value_type=PitMarketAnchor,
)
VALUATION_MARKET_GAP = ArtifactKey(
    artifact_id="valuation.market_gap",
    schema_version=_SCHEMA_VERSION,
    value_type=ValuationMarketGap,
)
DECISION_RECORD = ArtifactKey(
    artifact_id="decision.record",
    schema_version=_SCHEMA_VERSION,
    value_type=DecisionStateRecord,
)
DECISION_STATE_PROVENANCE = ArtifactKey(
    artifact_id="decision.state_provenance",
    schema_version=_SCHEMA_VERSION,
    value_type=DecisionStateProvenance,
)
DECISION_INPUT_ASSESSMENT = ArtifactKey(
    artifact_id="decision.input_assessment",
    schema_version=_SCHEMA_VERSION,
    value_type=DecisionInputAssessment,
)
DECISION_DERIVATION = ArtifactKey(
    artifact_id="decision.derivation",
    schema_version=_SCHEMA_VERSION,
    value_type=DecisionDerivation,
)
MONITORING_PLAN = ArtifactKey(
    artifact_id="monitoring.plan",
    schema_version=_SCHEMA_VERSION,
    value_type=MonitoringPlan,
)
RESEARCH_READINESS = ArtifactKey(
    artifact_id="research.readiness",
    schema_version=_SCHEMA_VERSION,
    value_type=ResearchReadinessAssessment,
)
VALIDATION_FINANCIAL = ArtifactKey(
    artifact_id="validation.financial",
    schema_version=_SCHEMA_VERSION,
    value_type=FinancialValidation,
)
CAPITAL_EFFICIENCY = ArtifactKey(
    artifact_id="capital.efficiency",
    schema_version=_SCHEMA_VERSION,
    value_type=CapitalEfficiency,
)
CAPITAL_FUNDING_LOOP = ArtifactKey(
    artifact_id="capital.funding_loop",
    schema_version=_SCHEMA_VERSION,
    value_type=FundingLoop,
)
EXPECTATION_QUALITY = ArtifactKey(
    artifact_id="expectation.quality",
    schema_version=_SCHEMA_VERSION,
    value_type=ExpectationQualityAssessment,
)
CASH_FLOW_QUALITY_BRIDGE = ArtifactKey(
    artifact_id="cash_flow.quality_bridge",
    schema_version=_SCHEMA_VERSION,
    value_type=CashFlowQualityBridge,
)
MONITORING_PRIOR_RUN_REVIEW = ArtifactKey(
    artifact_id="monitoring.prior_run_review",
    schema_version=_SCHEMA_VERSION,
    value_type=PriorRunReview,
)
SEMANTIC_PRESERVATION = ArtifactKey(
    artifact_id="semantic.preservation",
    schema_version=_SCHEMA_VERSION,
    value_type=SemanticPreservation,
)
VALIDATION_SEMANTIC_PRESERVATION = ArtifactKey(
    artifact_id="validation.semantic_preservation",
    schema_version=_SCHEMA_VERSION,
    value_type=SemanticPreservation,
)

CORE_ARTIFACT_KEYS = (
    REPOSITORY_PREFLIGHT,
    EVIDENCE_PIT,
    VALIDATION_LINEAGE,
    FINANCIAL_FACT_SNAPSHOT,
    BUSINESS_MODEL_PROFILE,
    STRATEGY_RESOLUTION,
    KPI_METRICS,
    FINANCIAL_TIME_SERIES,
    FINANCIAL_TEMPORAL_ANALYSIS,
    RESEARCH_OPERATING_EVIDENCE,
    RESEARCH_SUFFICIENCY,
    EXPECTATION_CONSENSUS_DISTRIBUTION,
    SCENARIO_SENSITIVITIES,
    METHODOLOGY_DISCLOSURE,
    DRIVERS_GRAPH,
    THESIS_PORTFOLIO,
    THESIS_SEMANTIC_SIGNAL_ASSESSMENT,
    SEMANTIC_CLAIMS,
    EXPECTATION_SNAPSHOT,
    EXPECTATION_GAP,
    FORECAST_EVALUATION,
    FORECAST_BENCHMARK_EVIDENCE,
    PEERS_NORMALIZED,
    VALUATION_ROUTING,
    VALUATION_EXECUTION,
    VALUATION_RESULT,
    VALUATION_RECONCILIATION,
    VALUATION_MARKET_ANCHOR,
    VALUATION_MARKET_GAP,
    DECISION_RECORD,
    DECISION_STATE_PROVENANCE,
    DECISION_INPUT_ASSESSMENT,
    DECISION_DERIVATION,
    MONITORING_PLAN,
    RESEARCH_READINESS,
    VALIDATION_FINANCIAL,
    CAPITAL_EFFICIENCY,
    CAPITAL_FUNDING_LOOP,
    EXPECTATION_QUALITY,
    CASH_FLOW_QUALITY_BRIDGE,
    MONITORING_PRIOR_RUN_REVIEW,
    SEMANTIC_PRESERVATION,
    VALIDATION_SEMANTIC_PRESERVATION,
)


def build_core_artifact_catalog() -> ArtifactCatalog:
    """Build a catalog containing every currently strict durable registration."""

    catalog = ArtifactCatalog()
    for key in CORE_ARTIFACT_KEYS:
        catalog.register(
            ArtifactDefinition(
                key=cast(ArtifactKey[object], key),
                mode=ArtifactMode.EXCLUSIVE,
            )
        )
    return catalog
