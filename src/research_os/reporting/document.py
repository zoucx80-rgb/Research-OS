from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from research_os.reporting.semantics import SemanticValue


class NarrativeBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["narrative"] = "narrative"
    title: str | None = None
    text: str


class FinancialOperatingBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["financial_operating"] = "financial_operating"
    financial_sanity: dict[str, Any] | None = None
    kpi_metrics: list[dict[str, Any]] = Field(default_factory=list)


class CapitalFundingBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["capital_funding"] = "capital_funding"
    capital_efficiency: dict[str, Any] | None = None
    funding_loop: dict[str, Any] | None = None


class CausalBridgeBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["causal_bridge"] = "causal_bridge"
    steps: list[str] = Field(default_factory=list)


class ThesisDebateBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["thesis_debate"] = "thesis_debate"
    theses: list[dict[str, Any]] = Field(default_factory=list)
    signal_assessment: dict[str, Any] | None = None


class ExpectationForecastBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["expectation_forecast"] = "expectation_forecast"
    expectation_quality: dict[str, Any] | None = None
    forecast_discipline: dict[str, Any] | None = None


class ExpectationGapBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["expectation_gap"] = "expectation_gap"
    payload: dict[str, Any] = Field(default_factory=dict)


class ValuationRationaleBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["valuation_rationale"] = "valuation_rationale"
    valuation_models: list[dict[str, Any]] = Field(default_factory=list)
    valuation_execution: dict[str, Any] | None = None


class ValuationBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["valuation"] = "valuation"
    payload: dict[str, Any] = Field(default_factory=dict)


class MonitoringBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["monitoring"] = "monitoring"
    next_verification_event: str = ""
    conviction_up_conditions: list[str] = Field(default_factory=list)
    thesis_broken_conditions: list[str] = Field(default_factory=list)
    key_metrics: list[str] = Field(default_factory=list)


class StateProvenanceBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["state_provenance"] = "state_provenance"
    items: list[dict[str, Any]] = Field(default_factory=list)


class LimitationBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["limitation"] = "limitation"
    items: list[str] = Field(default_factory=list)


class EvidenceNoteBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["evidence_note"] = "evidence_note"
    text: str
    evidence_ids: list[str] = Field(default_factory=list)


class GapClassificationBlock(BaseModel):
    model_config = ConfigDict(frozen=True)
    block_type: Literal["gap_classification"] = "gap_classification"
    evidence_missing: list[str] = Field(default_factory=list)
    capability_missing: list[str] = Field(default_factory=list)
    not_applicable: list[str] = Field(default_factory=list)
    presentation_or_deferred: list[str] = Field(default_factory=list)


ReportBlock = (
    NarrativeBlock
    | FinancialOperatingBlock
    | CapitalFundingBlock
    | CausalBridgeBlock
    | ThesisDebateBlock
    | ExpectationForecastBlock
    | ExpectationGapBlock
    | ValuationRationaleBlock
    | ValuationBlock
    | MonitoringBlock
    | StateProvenanceBlock
    | LimitationBlock
    | EvidenceNoteBlock
    | GapClassificationBlock
)


class ReportSection(BaseModel):
    model_config = ConfigDict(frozen=True)
    section_id: str
    title: str
    blocks: list[ReportBlock] = Field(default_factory=list)


class InvestmentDecisionSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)
    company_id: str
    decision_ts: datetime
    business_model: SemanticValue
    decision_state: SemanticValue | None = None
    fundamental_state: SemanticValue
    thesis_state: SemanticValue
    expectation_state: SemanticValue
    valuation_state: SemanticValue
    primary_thesis: str
    material_drivers: list[str] = Field(default_factory=list)
    material_risks: list[SemanticValue] = Field(default_factory=list)
    evidence_confidence: str | float
    next_verification_event: str = ""
    material_limitation_count: int = 0
    top_limitation: str | None = None


class AuditAppendix(BaseModel):
    model_config = ConfigDict(frozen=True)
    repository: str
    repository_commit: str
    research_os_version: str
    core_api_version: str
    presentation_version: str
    industry_plugins: list[dict[str, Any]] = Field(default_factory=list)
    methodology_plugins: list[dict[str, Any]] = Field(default_factory=list)
    module_statuses: dict[str, dict[str, Any]] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    assumption_ids: list[str] = Field(default_factory=list)


class ResearchReportDocument(BaseModel):
    model_config = ConfigDict(frozen=True)
    metadata: dict[str, Any] = Field(default_factory=dict)
    decision_snapshot: InvestmentDecisionSnapshot
    sections: list[ReportSection] = Field(default_factory=list)
    audit_appendix: AuditAppendix
    composition_version: str = "research-report-composer@1.1.0"
