from datetime import datetime, time, timezone

from pydantic import BaseModel, Field

from research_os.capital.engine import CapitalEfficiencyEngine, CapitalEfficiencyResult, FundingLoopResult
from research_os.completion.gate import REQUIRED_MODULES, ResearchCompletionGate
from research_os.completion.models import ResearchCompletionInput, ResearchCompletionResult
from research_os.decision.engine import DecisionEngine
from research_os.decision.models import DecisionContext, DecisionStateRecord
from research_os.decision.validation import validate_decision_state
from research_os.domain.evidence import Evidence
from research_os.drivers.graph import DriverGraph
from research_os.drivers.models import DriverGraphResult
from research_os.events.validation import NextVerificationEvent, NextVerificationEventValidator
from research_os.expectations.models import ConsensusVintage, ExpectationEvidence, ExpectationService, ExpectationSnapshot
from research_os.expectations.validation import ExpectationEvidenceValidator
from research_os.kpi.base import KpiPackRegistry, KpiPackResolution, MetricResult
from research_os.ledger.service import Claim, EvidenceLedger
from research_os.preflight.models import RepositoryPreflightEvidence
from research_os.preflight.validator import PreflightValidator
from research_os.router.classifier import BusinessModelRouter
from research_os.router.models import BusinessModelProfile
from research_os.snapshots.service import ResearchSnapshot, SnapshotService
from research_os.thesis.models import Thesis
from research_os.thesis.service import ThesisService
from research_os.validation.financial import FinancialMetricObservation, FinancialSanityValidator
from research_os.valuation.execution import ValuationExecution, ValuationExecutionValidator
from research_os.valuation.fitness import ModelFitnessInputs
from research_os.valuation.router import ValuationContext, ValuationRouter, ValuationRoutingResult
from research_os.version import RESEARCH_OS_VERSION


GRADE_SCORE = {"A": 1.0, "B": 0.9, "C": 0.75, "D": 0.5, "E": 0.3}


class ResearchSafetyContext(BaseModel):
    preflight: RepositoryPreflightEvidence | None = None
    financial_unit: str = "元"
    financial_observations: list[FinancialMetricObservation] = Field(default_factory=list)
    expectation_evidence: ExpectationEvidence | None = None
    expectation_conclusion: str | None = None
    valuation_execution: ValuationExecution | None = None
    next_verification_event: NextVerificationEvent | None = None
    claimed_conclusions: list[str] = Field(default_factory=list)


class ResearchRunRequest(BaseModel):
    company_id: str
    decision_ts: datetime
    evidence: list[Evidence]
    facts: dict
    expectation_vintage: ConsensusVintage
    valuation_models: dict[str, ModelFitnessInputs]
    fundamental_state: str
    valuation_state: str
    expectation_state: str
    versions: dict[str, str]
    safety: ResearchSafetyContext | None = None


class ResearchRun(BaseModel):
    company_id: str
    decision_ts: datetime
    profile: BusinessModelProfile
    pack_ids: list[str]
    metrics: list[MetricResult]
    drivers: DriverGraphResult
    theses: list[Thesis]
    claims: list[Claim]
    expectations: ExpectationSnapshot
    valuation: ValuationRoutingResult
    decision: DecisionStateRecord
    snapshot: ResearchSnapshot
    capital_efficiency: CapitalEfficiencyResult | None = None
    funding_loop: FundingLoopResult | None = None
    validation_statuses: dict[str, str] = Field(default_factory=dict)
    completion: ResearchCompletionResult | None = None


class ResearchOS:
    """Deterministic orchestration with PIT, lineage and completion safety gates."""

    def __init__(self):
        self.router = BusinessModelRouter()
        self.registry = KpiPackRegistry.default()
        self.theses = ThesisService()
        self.ledger = EvidenceLedger()
        self.expectations = ExpectationService()
        self.valuation = ValuationRouter()
        self.decision = DecisionEngine()
        self.snapshots = SnapshotService()
        self.preflight = PreflightValidator()
        self.financial = FinancialSanityValidator()
        self.expectation_validation = ExpectationEvidenceValidator()
        self.valuation_execution = ValuationExecutionValidator()
        self.capital = CapitalEfficiencyEngine()
        self.temporal = NextVerificationEventValidator()
        self.completion = ResearchCompletionGate()

    @staticmethod
    def _evidence_confidence(evidence: list[Evidence]) -> float:
        if not evidence:
            return 0.0
        return sum(GRADE_SCORE.get(e.confidence_grade.value, 0.0) for e in evidence) / len(evidence)

    @staticmethod
    def _capital_status(metrics: list[MetricResult], result: CapitalEfficiencyResult) -> str:
        if any(m.status == "valid" and m.metric_id in {"roic", "incremental_roic", "incremental_nwc_intensity"} for m in metrics):
            return "PASS"
        if any(value is not None for value in (result.roic, result.incremental_roic, result.iwcr)):
            return "PASS"
        return "INSUFFICIENT_EVIDENCE"

    @staticmethod
    def _funding_status(result: FundingLoopResult) -> str:
        return "INSUFFICIENT_EVIDENCE" if result.funding_state == "unknown" else "PASS"

    @staticmethod
    def _kpi_status(resolution: KpiPackResolution) -> str:
        return "PASS" if resolution.primary_supported else "INSUFFICIENT_EVIDENCE"

    def complete_run(self, req: ResearchRunRequest) -> ResearchRun:
        statuses = {name: "INSUFFICIENT_EVIDENCE" for name in REQUIRED_MODULES}
        safety = req.safety

        if safety is not None:
            if safety.preflight is None:
                raise ValueError("PREFLIGHT_FAIL: repository preflight evidence is required")
            try:
                self.preflight.validate(safety.preflight)
            except ValueError as exc:
                raise ValueError(f"PREFLIGHT_FAIL: {exc}") from exc
            statuses["Repository Preflight"] = "PASS"

        available = [e for e in req.evidence if e.publish_ts <= req.decision_ts]
        if not available:
            raise ValueError("no evidence available at decision_ts")
        statuses["PIT Validation"] = "PASS"

        latest_by_fact = {}
        for e in sorted(available, key=lambda x: (x.publish_ts, x.revision_no)):
            latest_by_fact[e.source_table or e.evidence_id] = e
        for fact, value in req.facts.items():
            evidence_item = latest_by_fact.get(fact)
            if evidence_item is None or evidence_item.value != value:
                raise ValueError(f"fact {fact!r} is not supported by as-of evidence")
        statuses["Evidence Lineage"] = "PASS"

        if safety is not None:
            financial_result = self.financial.validate_fact_mapping(req.facts, unit=safety.financial_unit)
            if safety.financial_observations:
                consistency = self.financial.check_consistency(safety.financial_observations)
                financial_result.errors.extend(consistency.errors)
                if consistency.status == "FAIL":
                    financial_result.status = "FAIL"
            if financial_result.status == "FAIL":
                raise ValueError("FINANCIAL_SANITY_FAIL: " + "; ".join(financial_result.errors))
            statuses["Financial Sanity"] = "PASS"

        profile = self.router.classify(req.company_id, available)
        statuses["Business Model Router"] = "PASS"
        pack_resolution = self.registry.resolve_with_status(profile)
        packs = pack_resolution.packs
        statuses["KPI Pack"] = self._kpi_status(pack_resolution)
        metrics: list[MetricResult] = []
        evidence_by_fact = {fact: e.evidence_id for fact, e in latest_by_fact.items()}
        for pack in packs:
            calculated = pack.calculate(req.facts)
            dependencies = getattr(pack, "metric_dependencies", {})
            for metric in calculated:
                ids = [evidence_by_fact[fact] for fact in dependencies.get(metric.metric_id, []) if fact in evidence_by_fact]
                metrics.append(metric.model_copy(update={"evidence_ids": ids}))
        if any(m.status == "valid" and not m.evidence_ids for m in metrics):
            statuses["Evidence Lineage"] = "FAIL"

        capital_facts = dict(req.facts)
        if capital_facts.get("operating_cash_flow") is None and capital_facts.get("ocf") is not None:
            capital_facts["operating_cash_flow"] = capital_facts["ocf"]
        capital_efficiency = self.capital.calculate(capital_facts)
        funding_loop = self.capital.funding_loop(capital_facts)
        statuses["Capital Efficiency"] = self._capital_status(metrics, capital_efficiency)
        statuses["Funding Loop"] = self._funding_status(funding_loop)

        drivers = DriverGraph.build(req.company_id, [p.pack_id for p in packs], available)
        statuses["Driver Graph"] = "PASS"
        theses = self.theses.evaluate(req.company_id, available, drivers)
        statuses["Thesis"] = "PASS" if theses else "INSUFFICIENT_EVIDENCE"
        statuses["Anti-Thesis"] = "PASS" if theses and all(t.anti_thesis for t in theses) else "INSUFFICIENT_EVIDENCE"
        statuses["Falsifiers"] = "PASS" if theses and any(t.falsifiers for t in theses) else "INSUFFICIENT_EVIDENCE"

        self.expectations.add(req.expectation_vintage)
        expectation = self.expectations.snapshot(req.company_id, req.decision_ts, expectation_type=req.expectation_vintage.expectation_type)
        if safety is not None:
            expectation_assessment = self.expectation_validation.assess(
                conclusion=safety.expectation_conclusion,
                evidence=safety.expectation_evidence,
                decision_ts=req.decision_ts,
            )
            statuses["Expectation Evidence"] = expectation_assessment.status
            if expectation_assessment.status == "FAIL":
                raise ValueError("EXPECTATION_GATE_FAIL: " + "; ".join(expectation_assessment.errors))

        statuses["Forecast Discipline"] = "NOT_APPLICABLE"
        valuation = self.valuation.route(ValuationContext(business_model=profile.primary_model, models=req.valuation_models))
        statuses["Valuation Fitness"] = "PASS" if valuation.primary_models else "INSUFFICIENT_EVIDENCE"

        if safety is not None and safety.valuation_execution is not None:
            valuation_execution_result = self.valuation_execution.validate(safety.valuation_execution)
            if valuation_execution_result.status == "VALUATION_GATE_FAIL":
                raise ValueError("VALUATION_GATE_FAIL: " + "; ".join(valuation_execution_result.errors))
            selected = valuation.models.get(safety.valuation_execution.selected_model)
            if selected is None or selected.status in {"NOT_APPLICABLE", "LOW_CONFIDENCE"}:
                raise ValueError("VALUATION_GATE_FAIL: executed model is not supported by valuation fitness routing")
            statuses["Valuation Execution"] = "PASS" if valuation_execution_result.status == "PASS" else "INSUFFICIENT_EVIDENCE"

        claims = []
        for thesis in theses:
            valid_until = None
            if thesis.next_check_date:
                valid_until = datetime.combine(thesis.next_check_date, time.max, tzinfo=timezone.utc)
            claim = Claim(
                claim_id=f"claim:{thesis.thesis_id}:{req.decision_ts.isoformat()}",
                company_id=req.company_id,
                claim_text=thesis.statement,
                claim_type="thesis",
                confidence_grade="D",
                evidence_ids=thesis.supporting_evidence or [e.evidence_id for e in available],
                assumptions=[thesis.mechanism, thesis.anti_thesis or ""],
                falsifiers=[f.label() for f in thesis.falsifiers],
                valid_from=req.decision_ts,
                valid_until=valid_until,
                next_verification_event=(f"next check: {thesis.next_check_date}" if thesis.next_check_date else "next material disclosure"),
            )
            claims.append(self.ledger.add_claim(claim))

        thesis_state = theses[0].status.upper()
        if thesis_state not in {"STRENGTHENING", "ACTIVE", "WEAKENING", "FALSIFIED"}:
            thesis_state = "ACTIVE"

        decision = self.decision.evaluate(DecisionContext(
            company_id=req.company_id,
            fundamental_state=req.fundamental_state,
            valuation_state=req.valuation_state,
            expectation_state=req.expectation_state,
            thesis_state=thesis_state,
            evidence_confidence=self._evidence_confidence(available),
            evidence_ids=[e.evidence_id for e in available],
            claim_ids=[c.claim_id for c in claims],
            decision_ts=req.decision_ts,
            research_os_version=req.versions.get("research_os_version", RESEARCH_OS_VERSION),
        ))
        validate_decision_state(decision.state)
        statuses["Decision State"] = "PASS"

        if safety is not None and safety.next_verification_event is not None:
            temporal = self.temporal.validate(
                safety.next_verification_event,
                reference_time=req.decision_ts,
                used_evidence_ids=[e.evidence_id for e in available],
            )
            statuses["Temporal Consistency"] = temporal.status
            statuses["Next Verification Event"] = "PASS" if temporal.status == "PASS" else "FAIL"
        elif safety is not None:
            statuses["Next Verification Event"] = "INSUFFICIENT_EVIDENCE"
            statuses["Temporal Consistency"] = "INSUFFICIENT_EVIDENCE"

        completion = self.completion.evaluate(ResearchCompletionInput(
            module_statuses=statuses,
            tool_completed=True,
            claimed_conclusions=(safety.claimed_conclusions if safety is not None else []),
        ))

        payload = {
            "business_model": profile.model_dump(mode="json"),
            "pack_ids": [p.pack_id for p in packs],
            "metrics": [m.model_dump(mode="json") for m in metrics],
            "capital_efficiency": capital_efficiency.model_dump(mode="json"),
            "funding_loop": funding_loop.model_dump(mode="json"),
            "drivers": drivers.model_dump(mode="json"),
            "theses": [t.model_dump(mode="json") for t in theses],
            "claims": [c.model_dump(mode="json") for c in claims],
            "expectations": expectation.model_dump(mode="json"),
            "valuation": valuation.model_dump(mode="json"),
            "decision": decision.model_dump(mode="json"),
            "validation_statuses": statuses,
            "completion": completion.model_dump(mode="json"),
        }
        snapshot = self.snapshots.freeze(req.company_id, req.decision_ts, req.versions, payload=payload)
        return ResearchRun(
            company_id=req.company_id,
            decision_ts=req.decision_ts,
            profile=profile,
            pack_ids=[p.pack_id for p in packs],
            metrics=metrics,
            capital_efficiency=capital_efficiency,
            funding_loop=funding_loop,
            drivers=drivers,
            theses=theses,
            claims=claims,
            expectations=expectation,
            valuation=valuation,
            decision=decision,
            snapshot=snapshot,
            validation_statuses=statuses,
            completion=completion,
        )
