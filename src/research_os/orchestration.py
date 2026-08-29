from datetime import datetime, time, timezone
from pydantic import BaseModel, Field

from research_os.domain.evidence import Evidence
from research_os.router.models import BusinessModelProfile
from research_os.router.classifier import BusinessModelRouter
from research_os.kpi.base import KpiPackRegistry, MetricResult
from research_os.drivers.models import DriverGraphResult
from research_os.drivers.graph import DriverGraph
from research_os.thesis.models import Thesis
from research_os.thesis.service import ThesisService
from research_os.ledger.service import Claim, EvidenceLedger
from research_os.expectations.models import ConsensusVintage, ExpectationService, ExpectationSnapshot
from research_os.valuation.fitness import ModelFitnessInputs
from research_os.valuation.router import ValuationContext, ValuationRouter, ValuationRoutingResult
from research_os.decision.models import DecisionContext, DecisionStateRecord
from research_os.decision.engine import DecisionEngine
from research_os.snapshots.service import ResearchSnapshot, SnapshotService

GRADE_SCORE={"A":1.0,"B":0.9,"C":0.75,"D":0.5,"E":0.3}

class ResearchRunRequest(BaseModel):
    company_id: str
    decision_ts: datetime
    evidence: list[Evidence]
    facts: dict
    expectation_vintage: ConsensusVintage
    valuation_models: dict[str,ModelFitnessInputs]
    fundamental_state: str
    valuation_state: str
    expectation_state: str
    versions: dict[str,str]

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

class ResearchOS:
    """Deterministic v1.1 orchestration over the individually testable research services."""
    def __init__(self):
        self.router=BusinessModelRouter()
        self.registry=KpiPackRegistry.default()
        self.theses=ThesisService()
        self.ledger=EvidenceLedger()
        self.expectations=ExpectationService()
        self.valuation=ValuationRouter()
        self.decision=DecisionEngine()
        self.snapshots=SnapshotService()

    @staticmethod
    def _evidence_confidence(evidence:list[Evidence])->float:
        if not evidence: return 0.0
        return sum(GRADE_SCORE.get(e.confidence_grade.value,0.0) for e in evidence)/len(evidence)

    def complete_run(self,req:ResearchRunRequest)->ResearchRun:
        # Enforce point-in-time at the orchestration boundary as well as the storage boundary.
        available=[e for e in req.evidence if e.publish_ts<=req.decision_ts]
        if not available:
            raise ValueError("no evidence available at decision_ts")

        # A complete research run may not smuggle future or untraceable values through the
        # convenience ``facts`` mapping. Every input fact must equal the latest evidence
        # version that was public at decision_ts.
        latest_by_fact={}
        for e in sorted(available,key=lambda x:(x.publish_ts,x.revision_no)):
            latest_by_fact[e.source_table or e.evidence_id]=e
        for fact,value in req.facts.items():
            evidence_item=latest_by_fact.get(fact)
            if evidence_item is None or evidence_item.value != value:
                raise ValueError(f"fact {fact!r} is not supported by as-of evidence")

        profile=self.router.classify(req.company_id,available)
        packs=self.registry.resolve(profile)
        metrics:list[MetricResult]=[]
        evidence_by_fact={fact:e.evidence_id for fact,e in latest_by_fact.items()}
        for pack in packs:
            calculated=pack.calculate(req.facts)
            dependencies=getattr(pack,"metric_dependencies",{})
            for metric in calculated:
                ids=[evidence_by_fact[fact] for fact in dependencies.get(metric.metric_id,[]) if fact in evidence_by_fact]
                metrics.append(metric.model_copy(update={"evidence_ids":ids}))

        drivers=DriverGraph.build(req.company_id,[p.pack_id for p in packs],available)
        theses=self.theses.evaluate(req.company_id,available,drivers)

        self.expectations.add(req.expectation_vintage)
        expectation=self.expectations.snapshot(req.company_id,req.decision_ts,expectation_type=req.expectation_vintage.expectation_type)
        valuation=self.valuation.route(ValuationContext(business_model=profile.primary_model,models=req.valuation_models))

        claims=[]
        for thesis in theses:
            valid_until=None
            if thesis.next_check_date:
                valid_until=datetime.combine(thesis.next_check_date,time.max,tzinfo=timezone.utc)
            claim=Claim(
                claim_id=f"claim:{thesis.thesis_id}:{req.decision_ts.isoformat()}",company_id=req.company_id,
                claim_text=thesis.statement,claim_type="thesis",confidence_grade="D",
                evidence_ids=thesis.supporting_evidence or [e.evidence_id for e in available],
                assumptions=[thesis.mechanism,thesis.anti_thesis or ""],
                falsifiers=[f.label() for f in thesis.falsifiers],valid_from=req.decision_ts,
                valid_until=valid_until,next_verification_event=(f"next check: {thesis.next_check_date}" if thesis.next_check_date else "next material disclosure"),
            )
            claims.append(self.ledger.add_claim(claim))

        thesis_state=theses[0].status.upper()
        if thesis_state not in {"STRENGTHENING","ACTIVE","WEAKENING","FALSIFIED"}:
            thesis_state="ACTIVE"
        decision=self.decision.evaluate(DecisionContext(
            company_id=req.company_id,fundamental_state=req.fundamental_state,valuation_state=req.valuation_state,
            expectation_state=req.expectation_state,thesis_state=thesis_state,
            evidence_confidence=self._evidence_confidence(available),evidence_ids=[e.evidence_id for e in available],
            claim_ids=[c.claim_id for c in claims],decision_ts=req.decision_ts,
            research_os_version=req.versions.get("research_os_version","1.1.0"),
        ))

        payload={
            "business_model":profile.model_dump(mode="json"),
            "pack_ids":[p.pack_id for p in packs],
            "metrics":[m.model_dump(mode="json") for m in metrics],
            "drivers":drivers.model_dump(mode="json"),
            "theses":[t.model_dump(mode="json") for t in theses],
            "claims":[c.model_dump(mode="json") for c in claims],
            "expectations":expectation.model_dump(mode="json"),
            "valuation":valuation.model_dump(mode="json"),
            "decision":decision.model_dump(mode="json"),
        }
        snapshot=self.snapshots.freeze(req.company_id,req.decision_ts,req.versions,payload=payload)
        return ResearchRun(company_id=req.company_id,decision_ts=req.decision_ts,profile=profile,pack_ids=[p.pack_id for p in packs],
            metrics=metrics,drivers=drivers,theses=theses,claims=claims,expectations=expectation,valuation=valuation,decision=decision,snapshot=snapshot)
