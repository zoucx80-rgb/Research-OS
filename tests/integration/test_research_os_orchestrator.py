import json
from pathlib import Path
from datetime import datetime
from research_os.domain.evidence import Evidence
from research_os.expectations.models import ConsensusVintage
from research_os.valuation.fitness import ModelFitnessInputs
from research_os.orchestration import ResearchOS, ResearchRunRequest

def test_complete_run_orchestrates_and_freezes_auditable_payload():
    f=json.loads(Path('tests/fixtures/distributor_full_run.json').read_text())
    ts=datetime.fromisoformat(f['decision_ts'])
    evidence=[Evidence(evidence_id=k,company_id=f['company_id'],evidence_type='calculated_metric',source_table=k,value=v,publish_ts=ts,ingested_at=ts,confidence_grade='B',verification_status='PRIMARY_VERIFIED') for k,v in f['facts'].items()]
    fit=lambda cash=.8: ModelFitnessInputs(data_quality=.9,earnings_stability=.8,cash_flow_visibility=cash,capital_structure_fit=.8,business_model_fit=.9,forecast_stability=.7)
    req=ResearchRunRequest(company_id=f['company_id'],decision_ts=ts,evidence=evidence,facts=f['facts'],
        expectation_vintage=ConsensusVintage(company_id=f['company_id'],as_of=ts,forecast_period='2026FY',net_profit=6.0),
        valuation_models={'pe':fit(),'pb':fit(),'dcf':fit(.2)},fundamental_state='IMPROVING',valuation_state='FAIR',expectation_state='MIXED',versions=f['versions'])
    run=ResearchOS().complete_run(req)
    assert run.profile.primary_model=='distributor'
    assert 'distributor' in run.pack_ids
    assert run.theses[0].anti_thesis
    assert run.claims
    assert run.snapshot.payload_hash
    assert run.snapshot.payload['decision']['state']==run.decision.state

def test_calculated_metrics_carry_input_evidence_lineage():
    f=json.loads(Path('tests/fixtures/distributor_full_run.json').read_text())
    ts=datetime.fromisoformat(f['decision_ts'])
    evidence=[Evidence(evidence_id=k,company_id=f['company_id'],evidence_type='calculated_metric',source_table=k,value=v,publish_ts=ts,ingested_at=ts,confidence_grade='B',verification_status='PRIMARY_VERIFIED') for k,v in f['facts'].items()]
    fit=lambda cash=.8: ModelFitnessInputs(data_quality=.9,earnings_stability=.8,cash_flow_visibility=cash,capital_structure_fit=.8,business_model_fit=.9,forecast_stability=.7)
    req=ResearchRunRequest(company_id=f['company_id'],decision_ts=ts,evidence=evidence,facts=f['facts'],expectation_vintage=ConsensusVintage(company_id=f['company_id'],as_of=ts,forecast_period='2026FY',net_profit=6.0),valuation_models={'pe':fit(),'pb':fit(),'dcf':fit(.2)},fundamental_state='IMPROVING',valuation_state='FAIR',expectation_state='MIXED',versions=f['versions'])
    run=ResearchOS().complete_run(req)
    ccc=next(m for m in run.metrics if m.metric_id=='ccc_days')
    assert {'avg_ar','revenue','avg_inventory','cogs','avg_ap'} <= set(ccc.evidence_ids)

def test_complete_run_rejects_fact_value_not_supported_by_asof_evidence():
    f=json.loads(Path('tests/fixtures/distributor_full_run.json').read_text())
    ts=datetime.fromisoformat(f['decision_ts'])
    evidence=[]
    for k,v in f['facts'].items():
        evidence.append(Evidence(evidence_id=k,company_id=f['company_id'],evidence_type='calculated_metric',source_table=k,value=v,publish_ts=ts,ingested_at=ts,confidence_grade='B',verification_status='PRIMARY_VERIFIED'))
    # Future revision exists but is not knowable at decision_ts.
    from datetime import timedelta
    evidence.append(Evidence(evidence_id='revenue_future',company_id=f['company_id'],evidence_type='calculated_metric',source_table='revenue',value=999.0,publish_ts=ts+timedelta(days=1),ingested_at=ts+timedelta(days=1),confidence_grade='B',verification_status='PRIMARY_VERIFIED'))
    facts=dict(f['facts']); facts['revenue']=999.0
    fit=lambda cash=.8: ModelFitnessInputs(data_quality=.9,earnings_stability=.8,cash_flow_visibility=cash,capital_structure_fit=.8,business_model_fit=.9,forecast_stability=.7)
    req=ResearchRunRequest(company_id=f['company_id'],decision_ts=ts,evidence=evidence,facts=facts,expectation_vintage=ConsensusVintage(company_id=f['company_id'],as_of=ts,forecast_period='2026FY',net_profit=6.0),valuation_models={'pe':fit(),'pb':fit(),'dcf':fit(.2)},fundamental_state='IMPROVING',valuation_state='FAIR',expectation_state='MIXED',versions=f['versions'])
    import pytest
    with pytest.raises(ValueError,match='not supported by as-of evidence'):
        ResearchOS().complete_run(req)
