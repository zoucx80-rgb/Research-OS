from __future__ import annotations

from pathlib import Path

from research_os.capital.engine import CapitalEfficiencyEngine
from research_os.decision.models import DecisionContext
from research_os.decision.validation import validate_decision_state
from research_os.runtime.builtin_modules import (
    BusinessModelModule,
    CapitalEfficiencyModule,
    DecisionModule,
    DriverThesisModule,
    ExpectationModule,
    FinancialSanityModule,
    ForecastDisciplineModule,
    FundingLoopModule,
    IndustryKpiModule,
    PITLineageModule,
    RepositoryPreflightModule,
    StrategyResolutionModule,
    TemporalModule,
    ValuationModule,
)
from research_os.runtime.financial_snapshot import FinancialFactSnapshotModule
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.modules import ModuleResult
from research_os.runtime.provenance import StateInput, resolve_state_input
from research_os.runtime.research_completeness import ResearchCompletenessModule
from research_os.runtime.source_pins import (
    SourcePin,
    SourceTreePin,
    load_source_tree_digest,
    validate_source_pins,
    validate_source_tree_pin,
)
from research_os.thesis.semantic_service_v1_5_11 import SemanticThesisService


V1_5_11_SOURCE_PINS = (
    SourcePin(
        "research_os.runtime.builtin_modules",
        "39d4ec55a394c3868cace78874e28219069c50643fee6b60c29d5910351888ce",
    ),
    SourcePin(
        "research_os.runtime.financial_snapshot",
        "bad8e325fa6b396d70fb69394e2db47b848d69554bafe6cae5c8014f3aa6d46b",
    ),
    SourcePin(
        "research_os.runtime.research_completeness",
        "65b76a18a185bef71d82aa5a9bde91a7f4cf5b29e845269365a8296b5b608ea7",
    ),
    SourcePin(
        "research_os.runtime.inputs",
        "4116515f237e64e7a289c123db7e128d70a2c13b3953509c9c697089ae87ff4f",
    ),
    SourcePin(
        "research_os.runtime.provenance",
        "716ff5ed77c7ee61e56e65c519c8777240127db0efd2c7d0b0aae33e124151a7",
    ),
    SourcePin(
        "research_os.thesis.semantic_service_v1_5_11",
        "aa4e0ef474fab018855b51427c4801cbc958793a91b9977a1b7859dda9f90177",
    ),
    SourcePin(
        "research_os.decision.models",
        "04b106a18bc86e0c0718ae672195de73c022b5264069aaea98abbe1d7eea8c13",
    ),
    SourcePin(
        "research_os.decision.validation",
        "1c2a474bae8f04f02cd70be69081b3f215aea45198501368132fed8bcca979f2",
    ),
    SourcePin(
        "research_os.capital.engine",
        "227a053fe10dec1b6f63c7f63f0b9a601fe61a04b01ad3a5bbb9712a02762bba",
    ),
    SourcePin(
        "research_os.expectations.validation",
        "4b0ce4c079a2527eb523759a27abc1048fe84ee67e30c63fbb743c7abe239b08",
    ),
)

V1_5_11_SOURCE_TREE_DIGEST_RESOURCE = Path(__file__).with_name(
    "historical_professional_modules_v1_5_11.sha256"
)
V1_5_11_SOURCE_TREE_PIN = SourceTreePin(
    package_name="research_os",
    sha256=load_source_tree_digest(V1_5_11_SOURCE_TREE_DIGEST_RESOURCE),
)


class ProfessionalDriverThesisModuleV1_5_11(DriverThesisModule):
    """Pinned v1.5.11 driver/thesis semantics for historical replay."""

    spec = DriverThesisModule.spec.model_copy(
        update={
            "module_version": "1.4.0",
            "provides": set(DriverThesisModule.spec.provides)
            | {"thesis.semantic_signal_assessment"},
        }
    )

    def __init__(self, *, inputs: ResearchInputs | None = None):
        run_inputs = inputs or ResearchInputs()
        super().__init__(
            theses=SemanticThesisService(
                comparison_rules=run_inputs.thesis_comparison_rules,
                prior_theses=run_inputs.prior_theses,
            )
        )
        self.inputs = run_inputs

    def run(self, context, state):
        result = super().run(context, state)
        evidence = list(state.get("evidence.pit", []) or [])
        artifacts = dict(result.artifacts)
        artifacts["thesis.semantic_signal_assessment"] = (
            self.theses.assess_signals(evidence) if evidence else None
        )
        return result.model_copy(update={"artifacts": artifacts})


class ProfessionalExpectationModuleV1_5_11(ExpectationModule):
    """Pinned v1.5.11 event-relative expectation semantics."""

    spec = ExpectationModule.spec.model_copy(
        update={
            "module_version": "1.3.0",
            "provides": set(ExpectationModule.spec.provides) | {"expectation.gap"},
        }
    )

    def run(self, context, state):
        result = super().run(context, state)
        quality = self.validator.assess_consensus_quality(
            vintage=self.inputs.expectation_vintage,
            decision_ts=context.decision_ts,
            latest_material_event_ts=self.inputs.latest_material_event_ts,
        )
        artifacts = dict(result.artifacts)
        artifacts["expectation.quality"] = quality
        artifacts["expectation.gap"] = self.inputs.expectation_gap
        validation = dict(artifacts.get("validation.expectation") or {})
        validation["quality_status"] = quality.status
        validation["quality_reason_codes"] = list(quality.reason_codes)
        artifacts["validation.expectation"] = validation
        return result.model_copy(update={"artifacts": artifacts})


class ProfessionalValuationModuleV1_5_11(ValuationModule):
    """Pinned v1.5.11 valuation execution projection."""

    spec = ValuationModule.spec.model_copy(
        update={
            "module_version": "1.2.0",
            "provides": set(ValuationModule.spec.provides)
            | {"valuation.execution", "valuation.result"},
        }
    )

    def run(self, context, state):
        result = super().run(context, state)
        artifacts = dict(result.artifacts)
        execution = self.inputs.valuation_execution
        artifacts["valuation.execution"] = execution
        artifacts["valuation.result"] = (
            execution.result if execution is not None else None
        )
        return result.model_copy(update={"artifacts": artifacts})


class ProfessionalDecisionModuleV1_5_11(DecisionModule):
    """Pinned v1.5.11 decision and state-provenance semantics."""

    spec = DecisionModule.spec.model_copy(
        update={
            "module_version": "1.3.0",
            "provides": set(DecisionModule.spec.provides) | {"decision.state_provenance"},
        }
    )

    @staticmethod
    def _funding_material_risk(funding) -> bool:
        if funding is None:
            return False
        state = getattr(funding, "funding_state", None)
        reasons = set(getattr(funding, "reason_codes", []) or [])
        if state == "stressed":
            return True
        if (
            state == "debt_funded"
            and {"DEBT_FUNDS_NWC", "NEGATIVE_OCF"}.issubset(reasons)
        ):
            return True
        if "MATERIAL_FACTORING_EXPOSURE" in reasons and reasons.intersection(
            {"NEGATIVE_OCF", "HIGH_IWCR", "DEBT_FUNDS_NWC"}
        ):
            return True
        return False

    def _has_explicit_expectation_state(self) -> bool:
        return (
            self.inputs.expectation_state_input is not None
            or "expectation_state" in self.inputs.model_fields_set
        )

    def _effective_expectation_state(self, state) -> str:
        if self.inputs.expectation_state_input is not None:
            return self.inputs.expectation_state_input.value
        if self._has_explicit_expectation_state():
            return self.inputs.expectation_state
        snapshot = state.get("expectation.snapshot")
        validation = state.get("validation.expectation") or {}
        validation_status = (
            validation.get("status")
            if isinstance(validation, dict)
            else getattr(validation, "status", None)
        )
        if snapshot is None or validation_status == "INSUFFICIENT_EVIDENCE":
            return "UNKNOWN"
        return self.inputs.expectation_state

    def _state_provenance(self, state=None):
        if state is not None and not self._has_explicit_expectation_state():
            expectation_state = self._effective_expectation_state(state)
            if expectation_state == "UNKNOWN":
                expectation = StateInput(
                    value="UNKNOWN",
                    source="derived",
                    method="no PIT-compliant expectation snapshot available",
                )
            else:
                expectation = resolve_state_input(None, expectation_state)
        else:
            expectation = resolve_state_input(
                self.inputs.expectation_state_input,
                self.inputs.expectation_state,
            )
        return {
            "fundamental": resolve_state_input(
                self.inputs.fundamental_state_input,
                self.inputs.fundamental_state,
            ),
            "valuation": resolve_state_input(
                self.inputs.valuation_state_input,
                self.inputs.valuation_state,
            ),
            "expectation": expectation,
        }

    def run(self, context, state):
        theses = list(state.get("thesis.items", []) or [])
        claims = list(state.get("claims.items", []) or [])
        evidence = list(state.get("evidence.pit", []) or [])
        funding = state.get("capital.funding_loop")
        if not theses:
            return ModuleResult(
                module_id=self.spec.module_id,
                status="INSUFFICIENT_EVIDENCE",
                artifacts={
                    "decision.record": None,
                    "validation.decision": {"status": "INSUFFICIENT_EVIDENCE"},
                    "decision.state_provenance": self._state_provenance(state),
                },
            )

        thesis_state = theses[0].status.upper()
        if thesis_state not in {
            "STRENGTHENING",
            "ACTIVE",
            "WEAKENING",
            "FALSIFIED",
            "UNRESOLVED",
        }:
            thesis_state = "ACTIVE"

        decision = self.engine.evaluate(
            DecisionContext(
                company_id=context.company.company_id,
                fundamental_state=self.inputs.fundamental_state,
                valuation_state=self.inputs.valuation_state,
                expectation_state=self._effective_expectation_state(state),
                thesis_state=thesis_state,
                evidence_confidence=self._confidence(evidence),
                evidence_ids=[item.evidence_id for item in evidence],
                claim_ids=[claim.claim_id for claim in claims],
                decision_ts=context.decision_ts,
                research_os_version=self.inputs.versions.get(
                    "research_os_version",
                    context.baseline.research_os_version,
                ),
                material_risk=self._funding_material_risk(funding),
            )
        )
        validate_decision_state(decision.state)
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS",
            artifacts={
                "decision.record": decision,
                "validation.decision": {"status": "PASS"},
                "decision.state_provenance": self._state_provenance(state),
            },
            evidence_ids=[item.evidence_id for item in evidence],
        )


def build_professional_builtin_modules_v1_5_11(
    *, registry, inputs: ResearchInputs | None = None
):
    """Compose the immutable v1.5.11 module sequence for historical replay."""

    validate_source_tree_pin(V1_5_11_SOURCE_TREE_PIN)
    validate_source_pins(V1_5_11_SOURCE_PINS)
    run_inputs = inputs or ResearchInputs()
    capital = CapitalEfficiencyEngine()
    return [
        RepositoryPreflightModule(inputs=run_inputs),
        PITLineageModule(),
        FinancialFactSnapshotModule(),
        ResearchCompletenessModule(inputs=run_inputs),
        FinancialSanityModule(inputs=run_inputs),
        BusinessModelModule(),
        StrategyResolutionModule(registry=registry),
        IndustryKpiModule(registry=registry),
        CapitalEfficiencyModule(engine=capital),
        FundingLoopModule(engine=capital),
        ProfessionalDriverThesisModuleV1_5_11(inputs=run_inputs),
        ProfessionalExpectationModuleV1_5_11(inputs=run_inputs),
        ForecastDisciplineModule(),
        ProfessionalValuationModuleV1_5_11(inputs=run_inputs),
        ProfessionalDecisionModuleV1_5_11(inputs=run_inputs),
        TemporalModule(inputs=run_inputs),
    ]
