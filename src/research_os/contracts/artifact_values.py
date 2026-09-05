"""Frozen public value types for Core API 2.0 commands and artifacts."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.contracts.evidence import EvidenceRef


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
Scalar = Decimal | float | int | str | bool | None
DomainStatus = Literal["SUPPORTED", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"]


class V2Value(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class AssumptionRef(V2Value):
    assumption_key: str
    assumption_version: str
    content_fingerprint: str

    @field_validator("assumption_key", "assumption_version")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("assumption reference fields must be non-empty")
        return value

    @field_validator("content_fingerprint")
    @classmethod
    def _sha256(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("content_fingerprint must be lowercase SHA-256 hex")
        return value


class LineageValue(V2Value):
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    assumption_refs: tuple[AssumptionRef, ...] = Field(default_factory=tuple)


class DomainArtifact(LineageValue):
    domain_status: DomainStatus = "INSUFFICIENT_EVIDENCE"


class LineageValidation(V2Value):
    status: Literal["PASS", "FAIL"]
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)
    errors: tuple[str, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _status_matches_errors(self) -> LineageValidation:
        if self.status == "PASS" and self.errors:
            raise ValueError("passing lineage validation cannot contain errors")
        if self.status == "FAIL" and not self.errors:
            raise ValueError("failed lineage validation requires errors")
        return self


class FinancialObservation(LineageValue):
    metric_id: str
    period: str
    value: Decimal | float
    unit: str
    scope: str = "consolidated"
    version: str = "reported"


class OperatingObservation(LineageValue):
    category: str
    metric_id: str
    value: Scalar = None
    unit: str | None = None
    period: str | None = None
    as_of: datetime | None = None
    entity_label: str | None = None
    segment_label: str | None = None


class FinancialSeriesPoint(LineageValue):
    period: str
    period_end: datetime
    value: Decimal | float | None = None


class FinancialTimeSeries(V2Value):
    metric_id: str
    unit: str | None = None
    points: tuple[FinancialSeriesPoint, ...] = Field(default_factory=tuple)


class FinancialTimeSeriesSet(DomainArtifact):
    series: tuple[FinancialTimeSeries, ...] = Field(default_factory=tuple)


class OperatingEvidenceSet(DomainArtifact):
    observations: tuple[OperatingObservation, ...] = Field(default_factory=tuple)


class CashFlowQualityInput(LineageValue):
    net_profit: Decimal | float | None = None
    operating_cash_flow: Decimal | float | None = None
    working_capital_contribution: Decimal | float | None = None
    other_adjustments: Decimal | float | None = None
    capex_cash: Decimal | float | None = None
    unit: str = "CNY"


class CashFlowQualityBridge(DomainArtifact):
    net_profit: Decimal | float | None = None
    operating_cash_flow: Decimal | float | None = None
    working_capital_contribution: Decimal | float | None = None
    other_adjustments: Decimal | float | None = None
    capex_cash: Decimal | float | None = None
    simplified_fcf: Decimal | float | None = None
    unit: str = "CNY"


class ConsensusVintage(LineageValue):
    company_id: str
    as_of: datetime
    forecast_period: str
    revenue: Decimal | float | None = None
    net_profit: Decimal | float | None = None
    eps: Decimal | float | None = None
    gross_margin: Decimal | float | None = None
    source_count: int | None = None
    source_quality: float | None = Field(default=None, ge=0, le=1)


class ConsensusObservation(LineageValue):
    source_key: str
    publish_ts: datetime
    forecast_period: str
    metric_id: str
    value: Decimal | float


class ConsensusDistribution(DomainArtifact):
    metric_id: str | None = None
    forecast_period: str | None = None
    observations: tuple[ConsensusObservation, ...] = Field(default_factory=tuple)
    source_count: int = 0
    low: Decimal | float | None = None
    median: Decimal | float | None = None
    high: Decimal | float | None = None


class ExpectationEvidence(LineageValue):
    expectation_source: str
    expectation_publish_ts: datetime
    expectation_period: str
    metric_id: str
    expected_value: Decimal | float
    actual_value: Decimal | float
    surprise: Decimal | float


class ExpectationSnapshot(DomainArtifact):
    company_id: str | None = None
    decision_ts: datetime | None = None
    vintage: ConsensusVintage | None = None


class ExpectationQualityAssessment(DomainArtifact):
    quality_status: Literal["ADEQUATE", "LOW", "UNKNOWN"] = "UNKNOWN"
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)
    age_days: int | None = None
    source_count: int | None = None


class ExpectationGap(DomainArtifact):
    metric_id: str | None = None
    market_value: Decimal | float | None = None
    os_value: Decimal | float | None = None
    direction: str = "MIXED"
    magnitude: Decimal | float | None = None
    comparison_basis: str | None = None


class PeerComparableObservation(LineageValue):
    peer_key: str
    peer_role: str
    metric_id: str
    period: str
    value: Decimal | float | None = None
    unit: str | None = None
    accounting_scope: str | None = None


class NormalizedPeer(LineageValue):
    company_id: str
    metric_id: str
    status: Literal["COMPARABLE", "ADJUSTMENT_REQUIRED", "NOT_COMPARABLE", "INSUFFICIENT_EVIDENCE"]
    value: Decimal | None = None
    unit: str | None = None
    period: str | None = None
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)


class NormalizedPeerSet(DomainArtifact):
    peers: tuple[NormalizedPeer, ...] = Field(default_factory=tuple)


class ScenarioAssumption(V2Value):
    reference: AssumptionRef
    label: str
    value: Scalar = None
    unit: str | None = None


class SensitivityCase(LineageValue):
    case_key: str
    driver_key: str
    shock_label: str
    affected_metric: str
    formula_version: str
    base_value: Decimal | float | None = None
    shock_value: Decimal | float | None = None
    result: Decimal | float | None = None
    probability: float | None = Field(default=None, ge=0, le=1)
    material_assumptions: tuple[ScenarioAssumption, ...] = Field(default_factory=tuple)
    model_boundary: str | None = None
    applicability: str | None = None
    caveats: tuple[str, ...] = Field(default_factory=tuple)


class SensitivitySet(DomainArtifact):
    cases: tuple[SensitivityCase, ...] = Field(default_factory=tuple)


class ResearchAssertion(LineageValue):
    assertion_key: str
    statement: str
    status: Literal["SUPPORTED", "REFUTED", "UNRESOLVED"] = "UNRESOLVED"


class ComparisonRule(V2Value):
    rule_key: str
    left_metric: str
    right_metric: str
    spread_threshold: Decimal | float
    adverse_label: str
    assumption_refs: tuple[AssumptionRef, ...] = Field(default_factory=tuple)


class Thesis(LineageValue):
    thesis_key: str
    company_id: str
    title: str
    statement: str
    mechanism: str
    anti_thesis: str
    status: Literal[
        "new", "unresolved", "active", "strengthening", "weakening", "falsified", "expired"
    ] = "new"
    supporting_driver_keys: tuple[str, ...] = Field(default_factory=tuple)
    falsifier_statements: tuple[str, ...] = Field(default_factory=tuple)
    next_check_date: date | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    claim_strength: Literal["OBSERVED", "SUGGESTIVE", "SUPPORTED", "STRONG", "CONFIRMED"] = (
        "OBSERVED"
    )


class ThesisPortfolio(DomainArtifact):
    primary: Thesis | None = None
    supporting: tuple[Thesis, ...] = Field(default_factory=tuple)
    conflicting: tuple[Thesis, ...] = Field(default_factory=tuple)
    unresolved: tuple[Thesis, ...] = Field(default_factory=tuple)
    falsified: tuple[Thesis, ...] = Field(default_factory=tuple)


class DirectionalSignal(LineageValue):
    metric_id: str
    direction: Literal["POSITIVE", "NEGATIVE", "NEUTRAL", "UNKNOWN"]
    semantic_label: str
    value: Decimal | float | None = None


class SemanticSignalAssessment(DomainArtifact):
    assessment_status: Literal["SUPPORTED", "MIXED", "INSUFFICIENT"] = "INSUFFICIENT"
    signals: tuple[DirectionalSignal, ...] = Field(default_factory=tuple)


class SemanticClaim(LineageValue):
    claim_key: str
    claim_type: Literal["FACT", "CALCULATION", "STATISTICAL_EVIDENCE", "ASSUMPTION", "CONCLUSION"]
    statement: str
    dependency_claim_keys: tuple[str, ...] = Field(default_factory=tuple)


class SemanticClaims(DomainArtifact):
    claims: tuple[SemanticClaim, ...] = Field(default_factory=tuple)


class DriverNode(LineageValue):
    driver_key: str
    name: str
    driver_type: str
    observable_metric: str | None = None
    critical: bool = False


class DriverEdge(LineageValue):
    from_driver: str
    to_driver: str
    relation: Literal["positive", "negative", "nonlinear", "conditional"]
    mechanism_description: str | None = None


class DriverGraph(DomainArtifact):
    company_id: str | None = None
    nodes: tuple[DriverNode, ...] = Field(default_factory=tuple)
    edges: tuple[DriverEdge, ...] = Field(default_factory=tuple)


class ForecastHypothesis(LineageValue):
    hypothesis_key: str
    statement: str
    target_metric: str
    horizon: str


class ForecastFoldEvaluation(V2Value):
    fold_key: str
    feature_available_ts: datetime
    label_mature_ts: datetime
    evaluation_ts: datetime
    model_error: Decimal
    benchmark_error: Decimal


class ForecastEvaluation(DomainArtifact):
    model_key: str | None = None
    benchmark_key: str | None = None
    evaluation_status: Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"
    train_cutoff: datetime | None = None
    evaluation_ts: datetime | None = None
    folds: tuple[ForecastFoldEvaluation, ...] = Field(default_factory=tuple)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)

    @field_validator("reason_codes")
    @classmethod
    def _canonical_reason_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("forecast evaluation reason codes must be non-empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("forecast evaluation reason codes must be unique")
        return tuple(sorted(normalized))


class ModelFitnessInputs(V2Value):
    data_quality: float = Field(ge=0, le=1)
    earnings_stability: float = Field(ge=0, le=1)
    cash_flow_visibility: float = Field(ge=0, le=1)
    capital_structure_fit: float = Field(ge=0, le=1)
    business_model_fit: float = Field(ge=0, le=1)
    forecast_stability: float = Field(ge=0, le=1)


class ValuationRouting(DomainArtifact):
    primary_model_keys: tuple[str, ...] = Field(default_factory=tuple)
    secondary_model_keys: tuple[str, ...] = Field(default_factory=tuple)


class ValuationResult(LineageValue):
    model_key: str
    status: DomainStatus
    formula_version: str
    value: Decimal | float | None = None
    unit: str | None = None


class ValuationExecution(DomainArtifact):
    execution_source: Literal["CONTROLLED", "EXTERNAL", "NONE"] = "NONE"
    validation_status: Literal[
        "PASS", "VALUATION_GATE_FAIL", "INSUFFICIENT_EVIDENCE"
    ] = "INSUFFICIENT_EVIDENCE"
    validation_errors: tuple[str, ...] = Field(default_factory=tuple)
    selected_model: str | None = None
    results: tuple[ValuationResult, ...] = Field(default_factory=tuple)


class ValuationRange(LineageValue):
    range_key: str
    low: Decimal | float
    high: Decimal | float
    basis: str
    currency: str
    unit: str | None = None
    share_class: str | None = None
    corporate_action_basis: str | None = None
    role: Literal["model_implied", "cross_check", "scenario", "market_anchor"]


class ValuationRationale(LineageValue):
    model_key: str
    rationale: str


class ValuationReconciliation(DomainArtifact):
    reconciliation_status: str = "INSUFFICIENT_EVIDENCE"
    method: str = "none"
    low: Decimal | float | None = None
    high: Decimal | float | None = None
    included_range_keys: tuple[str, ...] = Field(default_factory=tuple)


class DecisionStateRecord(DomainArtifact):
    company_id: str | None = None
    state: str = "INSUFFICIENT_EVIDENCE"
    decision_ts: datetime | None = None
    thesis_keys: tuple[str, ...] = Field(default_factory=tuple)
    claim_keys: tuple[str, ...] = Field(default_factory=tuple)
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)


class DecisionStateInput(LineageValue):
    dimension: str
    state: str
    thesis_keys: tuple[str, ...] = Field(default_factory=tuple)
    claim_keys: tuple[str, ...] = Field(default_factory=tuple)


class DecisionStateProvenance(DomainArtifact):
    inputs: tuple[DecisionStateInput, ...] = Field(default_factory=tuple)


class MonitoringRule(LineageValue):
    rule_key: str
    metric_id: str
    operator: Literal["lt", "lte", "gt", "gte", "eq"]
    threshold: Decimal | float
    frequency: str
    rationale: str


class VerificationEvent(LineageValue):
    event_key: str
    label: str
    event_type: str
    due_ts: datetime | None = None
    status: Literal["scheduled", "pending_date", "completed"] = "pending_date"


class MonitoringPlanItem(LineageValue):
    item_key: str
    metric_id: str
    condition: str
    next_check_ts: datetime | None = None


class MonitoringPlan(DomainArtifact):
    items: tuple[MonitoringPlanItem, ...] = Field(default_factory=tuple)
    next_verification_event: VerificationEvent | None = None


class PriorRunReviewInput(LineageValue):
    item_key: str
    prior_statement: str
    metric_id: str | None = None
    predicted_value: Decimal | float | None = None
    actual_value: Decimal | float | None = None
    tolerance: Decimal | float | None = Field(default=None, ge=0)


class PriorRunReviewItem(LineageValue):
    item_key: str
    prior_statement: str
    status: Literal["HIT", "MISS", "UNKNOWN"] = "UNKNOWN"
    error: Decimal | float | None = None


class PriorRunReview(DomainArtifact):
    items: tuple[PriorRunReviewItem, ...] = Field(default_factory=tuple)
    scored_count: int = 0
    hit_count: int = 0
    miss_count: int = 0


class FinancialValidation(DomainArtifact):
    validation_status: Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"
    errors: tuple[str, ...] = Field(default_factory=tuple)


class CapitalEfficiency(DomainArtifact):
    roic: Decimal | float | None = None
    incremental_roic: Decimal | float | None = None
    iwcr: Decimal | float | None = None


class FundingLoop(DomainArtifact):
    funding_state: str = "unknown"
    reason_codes: tuple[str, ...] = Field(default_factory=tuple)


class SemanticPreservation(DomainArtifact):
    validation_status: Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"
    violations: tuple[str, ...] = Field(default_factory=tuple)


class MethodologyDisclosure(DomainArtifact):
    policy_keys: tuple[str, ...] = Field(default_factory=tuple)
    plugin_keys: tuple[str, ...] = Field(default_factory=tuple)
    limitations: tuple[str, ...] = Field(default_factory=tuple)
