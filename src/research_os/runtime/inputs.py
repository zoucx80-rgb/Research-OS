from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from research_os.events.validation import NextVerificationEvent
from research_os.expectations.models import ConsensusVintage, ExpectationEvidence
from research_os.preflight.models import RepositoryPreflightEvidence
from research_os.runtime.provenance import StateInput
from research_os.validation.financial import FinancialMetricObservation
from research_os.valuation.execution import ValuationExecution
from research_os.valuation.fitness import ModelFitnessInputs


class ResearchInputs(BaseModel):
    """Immutable run-scoped analytical inputs that are not company facts.

    ResearchContext owns identity, PIT evidence/facts, knowledge and options.
    ResearchInputs owns analyst/runtime inputs required by higher-level modules.
    Keeping the two contracts separate lets storage and plugin systems evolve
    without recreating a monolithic request object.
    """

    model_config = ConfigDict(frozen=True)

    preflight: RepositoryPreflightEvidence | None = None
    financial_unit: str = "元"
    financial_observations: tuple[FinancialMetricObservation, ...] = Field(default_factory=tuple)

    expectation_vintage: ConsensusVintage | None = None
    expectation_evidence: ExpectationEvidence | None = None
    expectation_conclusion: str | None = None
    latest_material_event_ts: datetime | None = None
    latest_material_event_label: str | None = None

    valuation_models: dict[str, ModelFitnessInputs] = Field(default_factory=dict)
    valuation_execution: ValuationExecution | None = None

    # Legacy string inputs remain backward compatible. When provenance-aware
    # inputs are absent, runtime explicitly treats these as analyst assumptions.
    fundamental_state: str = "UNCERTAIN"
    valuation_state: str = "UNRELIABLE"
    expectation_state: str = "MIXED"
    fundamental_state_input: StateInput | None = None
    valuation_state_input: StateInput | None = None
    expectation_state_input: StateInput | None = None

    next_verification_event: NextVerificationEvent | None = None
    claimed_conclusions: tuple[str, ...] = Field(default_factory=tuple)
    versions: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def resolve_explicit_state_values(cls, value):
        if not isinstance(value, dict):
            return value
        data = dict(value)
        for legacy_name, input_name in (
            ("fundamental_state", "fundamental_state_input"),
            ("valuation_state", "valuation_state_input"),
            ("expectation_state", "expectation_state_input"),
        ):
            explicit = data.get(input_name)
            if explicit is None:
                continue
            if isinstance(explicit, StateInput):
                data[legacy_name] = explicit.value
            elif isinstance(explicit, dict) and explicit.get("value") is not None:
                data[legacy_name] = explicit["value"]
        return data
