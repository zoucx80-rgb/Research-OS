import json
from pathlib import Path
from datetime import datetime, timezone
from research_os.domain.evidence import Evidence
from research_os.router.classifier import BusinessModelRouter
from research_os.kpi.base import KpiPackRegistry
from research_os.drivers.graph import DriverGraph
from research_os.thesis.service import ThesisService
from research_os.expectations.models import ConsensusVintage, ExpectationService
from research_os.valuation.fitness import ModelFitnessInputs
from research_os.valuation.router import ValuationContext, ValuationRouter
from research_os.decision.models import DecisionContext
from research_os.decision.engine import DecisionEngine
from research_os.snapshots.service import SnapshotService


def test_distributor_research_run_is_complete():
    f=json.loads(Path("tests/fixtures/distributor_full_run.json").read_text())
    ts=datetime.fromisoformat(f["decision_ts"])
    evidence=[Evidence(evidence_id=k,company_id=f["company_id"],evidence_type="calculated_metric",source_table=k,value=v,publish_ts=ts,ingested_at=ts,confidence_grade="B",verification_status="PRIMARY_VERIFIED") for k,v in f["facts"].items()]
    profile=BusinessModelRouter().classify(f["company_id"],evidence)
    packs=KpiPackRegistry.default().resolve(profile)
    metrics=[]
    for p in packs: metrics.extend(p.calculate(f["facts"]))
    drivers=DriverGraph.build(f["company_id"],[p.pack_id for p in packs],evidence)
    theses=ThesisService().evaluate(f["company_id"],evidence,drivers)
    es=ExpectationService(); es.add(ConsensusVintage(company_id=f["company_id"],as_of=ts,forecast_period="2026FY",net_profit=f["consensus_net_profit"]))
    expectations=es.snapshot(f["company_id"],ts)
    fit=lambda **kw: ModelFitnessInputs(data_quality=.9,earnings_stability=.8,cash_flow_visibility=kw.get("cash_flow_visibility",.8),capital_structure_fit=.8,business_model_fit=.9,forecast_stability=.7)
    valuation=ValuationRouter().route(ValuationContext(business_model=profile.primary_model,models={"pe":fit(),"pb":fit(),"dcf":fit(cash_flow_visibility=.2)}))
    thesis_state=theses[0].status.upper(); thesis_state="FALSIFIED" if thesis_state=="FALSIFIED" else thesis_state
    decision=DecisionEngine().evaluate(DecisionContext(company_id=f["company_id"],fundamental_state="IMPROVING",valuation_state="FAIR",expectation_state="MIXED",thesis_state=thesis_state,evidence_confidence=.8,evidence_ids=[e.evidence_id for e in evidence],decision_ts=ts))
    versions=f["versions"]
    snapshot=SnapshotService().freeze(f["company_id"],ts,versions)
    assert profile.primary_model=="distributor"
    assert any(m.metric_id=="ccc_days" for m in metrics)
    assert all(t.falsifiers for t in theses if t.status in {"active","weakening","strengthening"})
    assert valuation.primary_models
    assert decision.evidence_ids
    assert snapshot.versions.research_os_version=="1.1.0"
