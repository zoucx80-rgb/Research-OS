from __future__ import annotations

import copy
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.contracts.artifact_values import (
    CashFlowQualityInput,
    ConsensusObservation,
    FinancialTimeSeries,
    FinancialObservation,
    ForecastHypothesis,
    MonitoringRule,
    OperatingObservation,
    PeerComparableObservation,
    PriorRunReviewInput,
    ResearchAssertion,
    SensitivityCase,
    ConsensusVintage,
    ExpectationEvidence,
    ExpectationGap,
    Thesis,
    ComparisonRule,
    VerificationEvent,
    ValuationExecution,
    ValuationRange,
    ValuationRationale,
    ModelFitnessInputs,
)
from research_os.runtime.context import ResearchContext


class _FrozenInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    def __getattribute__(self, name: str) -> Any:
        value = super().__getattribute__(name)
        if name in type(self).model_fields:
            return copy.deepcopy(value)
        return value

    def model_post_init(self, __context: object) -> None:
        for field_name in type(self).model_fields:
            object.__setattr__(
                self,
                field_name,
                copy.deepcopy(object.__getattribute__(self, field_name)),
            )


class FinancialResearchInput(_FrozenInput):
    unit: str = "CNY"
    observations: tuple[FinancialObservation, ...] = Field(default_factory=tuple)
    operating_observations: tuple[OperatingObservation, ...] = Field(default_factory=tuple)
    time_series: tuple[FinancialTimeSeries, ...] = Field(default_factory=tuple)
    cash_flow_quality: CashFlowQualityInput | None = None


class ThesisResearchInput(_FrozenInput):
    cycle_recovery_observed: bool | None = None
    cycle_turning_point_support: ResearchAssertion | None = None
    moat_evidence: tuple[ResearchAssertion, ...] = Field(default_factory=tuple)
    prior_theses: tuple[Thesis, ...] = Field(default_factory=tuple)
    comparison_rules: tuple[ComparisonRule, ...] = Field(default_factory=tuple)


class ExpectationResearchInput(_FrozenInput):
    vintage: ConsensusVintage | None = None
    evidence: ExpectationEvidence | None = None
    conclusion: str | None = None
    gap: ExpectationGap | None = None
    consensus_observations: tuple[ConsensusObservation, ...] = Field(default_factory=tuple)
    latest_material_event_ts: datetime | None = None
    latest_material_event_label: str | None = None


class ValuationModelInput(_FrozenInput):
    model_id: str
    fitness: ModelFitnessInputs

    @field_validator("model_id")
    @classmethod
    def _non_empty_model_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("model_id must be non-empty")
        return value


class ValuationResearchInput(_FrozenInput):
    models: tuple[ValuationModelInput, ...] = Field(default_factory=tuple)
    execution: ValuationExecution | None = None
    ranges: tuple[ValuationRange, ...] = Field(default_factory=tuple)
    rationales: tuple[ValuationRationale, ...] = Field(default_factory=tuple)


class MonitoringResearchInput(_FrozenInput):
    monitoring_rules: tuple[MonitoringRule, ...] = Field(default_factory=tuple)
    verification_calendar: tuple[VerificationEvent, ...] = Field(default_factory=tuple)
    prior_run_reviews: tuple[PriorRunReviewInput, ...] = Field(default_factory=tuple)
    next_verification_event: VerificationEvent | None = None


class ForecastResearchInput(_FrozenInput):
    hypotheses: tuple[ForecastHypothesis, ...] = Field(default_factory=tuple)


class PeerResearchInput(_FrozenInput):
    peer_comparables: tuple[PeerComparableObservation, ...] = Field(default_factory=tuple)


class ResearchReadinessInput(_FrozenInput):
    sensitivities: tuple[SensitivityCase, ...] = Field(default_factory=tuple)
    claimed_conclusions: tuple[str, ...] = Field(default_factory=tuple)


class ExternalVersionInputs(_FrozenInput):
    dataset_version: str | None = None
    parser_version: str | None = None
    data_provider_version: str | None = None
    external_model_version: str | None = None

    @field_validator("*", mode="after")
    @classmethod
    def _non_empty_versions(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("external versions must be non-empty when provided")
        return value


class ResearchRunOptions(_FrozenInput):
    industry_plugin_override: str | None = None
    methodology_plugin_overrides: tuple[str, ...] = Field(default_factory=tuple)
    override_rationale: str | None = None
    allow_experimental_plugins: bool = False
    persist_snapshot: bool = True
    external_versions: ExternalVersionInputs = Field(default_factory=ExternalVersionInputs)

    @model_validator(mode="after")
    def _require_override_rationale(self) -> ResearchRunOptions:
        if (self.industry_plugin_override or self.methodology_plugin_overrides) and not (
            self.override_rationale and self.override_rationale.strip()
        ):
            raise ValueError("plugin overrides require override_rationale")
        return self


class ResearchRunCommand(_FrozenInput):
    context: ResearchContext
    financial: FinancialResearchInput = Field(default_factory=FinancialResearchInput)
    thesis: ThesisResearchInput = Field(default_factory=ThesisResearchInput)
    expectations: ExpectationResearchInput = Field(default_factory=ExpectationResearchInput)
    valuation: ValuationResearchInput = Field(default_factory=ValuationResearchInput)
    monitoring: MonitoringResearchInput = Field(default_factory=MonitoringResearchInput)
    forecasting: ForecastResearchInput = Field(default_factory=ForecastResearchInput)
    peers: PeerResearchInput = Field(default_factory=PeerResearchInput)
    readiness: ResearchReadinessInput = Field(default_factory=ResearchReadinessInput)
    options: ResearchRunOptions = Field(default_factory=ResearchRunOptions)
