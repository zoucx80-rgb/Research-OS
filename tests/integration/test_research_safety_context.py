import json
from pathlib import Path
from datetime import datetime, timedelta

import pytest

from research_os.domain.evidence import Evidence
from research_os.expectations.models import ConsensusVintage, ExpectationEvidence
from research_os.preflight.models import RepositoryPreflightEvidence
from research_os.valuation.execution import ValuationExecution
from research_os.valuation.fitness import ModelFitnessInputs
from research_os.events.validation import NextVerificationEvent
import research_os.orchestration as orchestration


def _safety_cls():
    assert hasattr(orchestration, "ResearchSafetyContext"), "ResearchSafetyContext is required"
    return orchestration.ResearchSafetyContext


def _preflight(ts):
    return RepositoryPreflightEvidence(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        head_sha="8b23c6f8196a5d96aa3ebc19d9f4ecb4a05532c2",
        head_commit_message="docs: bind stock research shorthand to canonical protocol",
        agents_blob_sha="02ba8f81430e68121ef5c98b49a3ecfcc103fc5e",
        research_prompt_blob_sha="3210dc567ae25653ea80c3911481e2b0d2864f69",
        verified_at=ts,
        agents_ref="8b23c6f8196a5d96aa3ebc19d9f4ecb4a05532c2",
        research_prompt_ref="8b23c6f8196a5d96aa3ebc19d9f4ecb4a05532c2",
    )


def _fit(cash=.8):
    return ModelFitnessInputs(data_quality=.9, earnings_stability=.8, cash_flow_visibility=cash, capital_structure_fit=.8, business_model_fit=.9, forecast_stability=.7)


def _valuation_execution():
    return ValuationExecution(
        selected_model="pe",
        model_fitness_score=.8,
        selection_reason="stable positive earnings with distributor funding loop explicitly bridged",
        executed_model="pe",
        business_model="distributor",
        inputs={"net_profit": 5.13},
        assumptions=[{"label": "ASSUMPTION", "name": "pe_multiple", "value": 20.0}],
        scenario_logic="net profit times PE after driver bridge validation",
        lineage={"net_profit": ["net_profit"]},
        driver_bridge=["Revenue", "Gross Profit", "Working Capital", "Financing Requirement", "Financing Cost", "Credit / Inventory Loss", "Net Profit / Cash Economics", "Valuation"],
    )


def test_financial_sanity_failure_blocks_run_before_valuation_and_decision():
    Safety = _safety_cls()
    ts = datetime.fromisoformat("2026-08-29T08:00:00+00:00")
    facts = {"revenue": 655.25, "cogs": 634.01, "gross_profit": 2.123, "gross_margin": 0.0324}
    evidence = [
        Evidence(evidence_id=k, company_id="001287.SZ", evidence_type="filing_fact", source_table=k, value=v,
                 publish_ts=ts, ingested_at=ts, confidence_grade="A", verification_status="PRIMARY_VERIFIED")
        for k, v in facts.items()
    ]
    req = orchestration.ResearchRunRequest(
        company_id="001287.SZ", decision_ts=ts, evidence=evidence, facts=facts,
        expectation_vintage=ConsensusVintage(company_id="001287.SZ", as_of=ts, forecast_period="2026FY", net_profit=6.0),
        valuation_models={"pe": _fit()}, fundamental_state="UNCERTAIN", valuation_state="UNRELIABLE", expectation_state="MIXED",
        versions={"research_os_version": "1.2.0"},
        safety=Safety(preflight=_preflight(ts), financial_unit="亿元"),
    )
    with pytest.raises(ValueError, match="FINANCIAL_SANITY_FAIL"):
        orchestration.ResearchOS().complete_run(req)


def test_valid_safety_context_produces_machine_complete_research_run():
    Safety = _safety_cls()
    fixture = json.loads(Path("tests/fixtures/distributor_full_run.json").read_text())
    ts = datetime.fromisoformat(fixture["decision_ts"])
    # This integration case claims a complete funding-loop assessment, so it must provide
    # the funding-source facts required by the v1.2.1 missing-value contract.
    facts = {**fixture["facts"], "delta_debt": 140.0, "delta_equity": 0.0}
    evidence = [
        Evidence(evidence_id=k, company_id=fixture["company_id"], evidence_type="calculated_metric", source_table=k, value=v,
                 publish_ts=ts, ingested_at=ts, confidence_grade="B", verification_status="PRIMARY_VERIFIED")
        for k, v in facts.items()
    ]
    expectation = ExpectationEvidence(
        expectation_source="PIT analyst consensus",
        expectation_publish_ts=ts,
        expectation_period="2026FY",
        metric="net_profit",
        expected_value=6.0,
        actual_value=5.13,
        surprise=-0.87,
        vintage="2026-08-29",
    )
    safety = Safety(
        preflight=_preflight(ts),
        financial_unit="亿元",
        expectation_evidence=expectation,
        expectation_conclusion="miss expectations",
        valuation_execution=_valuation_execution(),
        next_verification_event=NextVerificationEvent(event_name="2026Q3 report", event_time=ts + timedelta(days=60)),
        claimed_conclusions=["expectation", "valuation", "decision_state"],
    )
    req = orchestration.ResearchRunRequest(
        company_id=fixture["company_id"], decision_ts=ts, evidence=evidence, facts=facts,
        expectation_vintage=ConsensusVintage(company_id=fixture["company_id"], as_of=ts, forecast_period="2026FY", net_profit=6.0),
        valuation_models={"pe": _fit(), "pb": _fit(), "dcf": _fit(.2)}, fundamental_state="IMPROVING", valuation_state="FAIR", expectation_state="UNDER_EXPECTED",
        versions={**fixture["versions"], "research_os_version": "1.2.0"}, safety=safety,
    )
    run = orchestration.ResearchOS().complete_run(req)
    assert run.completion.final_status == "COMPLETE"
    assert run.validation_statuses["Financial Sanity"] == "PASS"
    assert run.validation_statuses["Valuation Execution"] == "PASS"
    assert run.validation_statuses["Funding Loop"] == "PASS"
    assert run.funding_loop.funding_state == "debt_funded"
    assert run.capital_efficiency is not None
    assert run.funding_loop is not None
