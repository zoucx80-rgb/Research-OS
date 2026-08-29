from datetime import datetime, timedelta, timezone

from research_os.domain.evidence import Evidence
from research_os.events.validation import NextVerificationEvent
from research_os.expectations.models import ConsensusVintage, ExpectationEvidence
from research_os.preflight.models import RepositoryPreflightEvidence
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchInputs,
    ResearchOptions,
    ResearchRuntimeFactory,
)
from research_os.valuation.execution import ValuationExecution
from research_os.valuation.fitness import ModelFitnessInputs


def _fit(cash=.8):
    return ModelFitnessInputs(
        data_quality=.9,
        earnings_stability=.8,
        cash_flow_visibility=cash,
        capital_structure_fit=.8,
        business_model_fit=.9,
        forecast_stability=.7,
    )


def _preflight(ts):
    head = "8b23c6f8196a5d96aa3ebc19d9f4ecb4a05532c2"
    return RepositoryPreflightEvidence(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        head_sha=head,
        head_commit_message="synthetic verified baseline",
        agents_blob_sha="02ba8f81430e68121ef5c98b49a3ecfcc103fc5e",
        research_prompt_blob_sha="3210dc567ae25653ea80c3911481e2b0d2864f69",
        verified_at=ts,
        agents_ref=head,
        research_prompt_ref=head,
    )


def _valuation_execution():
    return ValuationExecution(
        selected_model="pe",
        model_fitness_score=.8,
        selection_reason="synthetic stable earnings with explicit funding bridge",
        executed_model="pe",
        business_model="distributor",
        inputs={"net_profit": 25.0},
        assumptions=[{"label": "ASSUMPTION", "name": "pe_multiple", "value": 20.0}],
        scenario_logic="net profit times PE after driver bridge validation",
        lineage={"net_profit": ["ev:net_profit"]},
        driver_bridge=[
            "Revenue",
            "Gross Profit",
            "Working Capital",
            "Financing Requirement",
            "Financing Cost",
            "Credit / Inventory Loss",
            "Net Profit / Cash Economics",
            "Valuation",
        ],
    )


def _versions():
    return {
        "dataset_version": "synthetic@1",
        "parser_version": "synthetic@1",
        "formula_version": "synthetic@1",
        "router_version": "router@1.0.0",
        "kpi_pack_version": "auto",
        "driver_model_version": "driver@1",
        "forecast_version": "none",
        "valuation_version": "valuation@test",
        "report_version": "runtime@1",
        "core_api_version": "1.0",
    }


def _context(facts, ts):
    evidence = [
        Evidence(
            evidence_id=f"ev:{key}",
            company_id="synthetic:safety",
            evidence_type="filing_fact",
            source_table=key,
            value=value,
            publish_ts=ts,
            ingested_at=ts,
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        )
        for key, value in facts.items()
    ]
    return ResearchContext(
        run_id="run:synthetic:safety",
        company=CompanyRef(company_id="synthetic:safety"),
        decision_ts=ts,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="1234567890abcdef1234567890abcdef12345678",
            research_os_version="1.4.0",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(
            values=facts,
            evidence_by_fact={key: [f"ev:{key}"] for key in facts},
        ),
        options=ResearchOptions(),
    )


def test_financial_sanity_failure_is_explicit_and_blocks_completion():
    ts = datetime(2026, 8, 29, 8, tzinfo=timezone.utc)
    facts = {
        "business_description": "electronic component distribution",
        "revenue": 655.25,
        "cogs": 634.01,
        "gross_profit": 2.123,
        "gross_margin": 0.0324,
        "avg_ar": 100.0,
        "avg_inventory": 100.0,
        "avg_ap": 50.0,
    }
    result = ResearchRuntimeFactory.default().run_context(
        _context(facts, ts),
        ResearchInputs(
            preflight=_preflight(ts),
            financial_unit="亿元",
            versions=_versions(),
        ),
    )

    assert result.module_results["core:financial-sanity"].status == "FAIL"
    assert result.completion.final_status == "INCOMPLETE"
    assert "Financial Sanity" in result.completion.blocking_modules


def test_full_typed_safety_inputs_can_produce_complete_machine_run():
    ts = datetime(2026, 8, 29, 8, tzinfo=timezone.utc)
    facts = {
        "business_description": "electronic component distribution",
        "revenue": 1000.0,
        "cogs": 970.0,
        "gross_profit": 30.0,
        "gross_margin": 0.03,
        "avg_ar": 160.0,
        "avg_inventory": 140.0,
        "avg_ap": 80.0,
        "ar": 180.0,
        "inventory": 150.0,
        "ap": 90.0,
        "delta_nwc": 80.0,
        "delta_revenue": 200.0,
        "delta_debt": 60.0,
        "delta_equity": 0.0,
        "ocf": -20.0,
        "cfo": -20.0,
        "net_profit": 25.0,
        "nopat": 24.0,
        "avg_invested_capital": 300.0,
        "period_type": "FY",
    }
    expectation = ExpectationEvidence(
        expectation_source="synthetic PIT consensus",
        expectation_publish_ts=ts,
        expectation_period="2026FY",
        metric="net_profit",
        expected_value=30.0,
        actual_value=25.0,
        surprise=-5.0,
        vintage="2026-08-29",
    )
    result = ResearchRuntimeFactory.default().run_context(
        _context(facts, ts),
        ResearchInputs(
            preflight=_preflight(ts),
            financial_unit="亿元",
            expectation_vintage=ConsensusVintage(
                company_id="synthetic:safety",
                as_of=ts,
                forecast_period="2026FY",
                net_profit=30.0,
            ),
            expectation_evidence=expectation,
            expectation_conclusion="miss expectations",
            valuation_models={"pe": _fit(), "pb": _fit(), "dcf": _fit(.2)},
            valuation_execution=_valuation_execution(),
            fundamental_state="IMPROVING",
            valuation_state="FAIR",
            expectation_state="UNDER_EXPECTED",
            next_verification_event=NextVerificationEvent(
                event_name="synthetic Q3 report",
                event_time=ts + timedelta(days=60),
            ),
            claimed_conclusions=("expectation", "valuation", "decision_state"),
            versions=_versions(),
        ),
    )

    assert result.completion.final_status == "COMPLETE"
    assert result.completion.module_statuses["Financial Sanity"] == "PASS"
    assert result.completion.module_statuses["Valuation Execution"] == "PASS"
    assert result.completion.module_statuses["Funding Loop"] == "PASS"
    assert result.artifacts["capital.funding_loop"].funding_state == "debt_funded"
    assert result.artifacts["capital.efficiency"] is not None
