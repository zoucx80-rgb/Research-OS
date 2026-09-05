from __future__ import annotations

from datetime import date, datetime, timezone
import subprocess

from research_os.application import ResearchApplication, ResearchRunCommand
from research_os.application.bootstrap import RepositoryAttestation
from research_os.application.command import (
    ExpectationResearchInput,
    FinancialResearchInput,
    ForecastResearchInput,
    MonitoringResearchInput,
    PeerResearchInput,
    ResearchReadinessInput,
    ResearchRunOptions,
    ThesisResearchInput,
    ValuationModelInput,
    ValuationResearchInput,
)
from research_os.contracts.artifact_values import (
    AssumptionRef,
    CashFlowQualityInput,
    ConsensusObservation,
    ConsensusVintage,
    ExpectationGap,
    FinancialSeriesPoint,
    FinancialTimeSeries,
    ForecastHypothesis,
    ModelFitnessInputs,
    MonitoringRule,
    PeerComparableObservation,
    PriorRunReviewInput,
    ResearchAssertion,
    ScenarioAssumption,
    SensitivityCase,
    Thesis,
    ValuationExecution,
    ValuationRange,
    ValuationRationale,
    ValuationResult,
    VerificationEvent,
)
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
from research_os.period.models import ReportingPeriod
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    EvidenceView,
    FactView,
    ResearchContext,
)
from research_os.semantics.fingerprint import semantic_fingerprint
from research_os.runtime.core_artifacts import (
    CAPITAL_FUNDING_LOOP,
    DECISION_RECORD,
    DECISION_STATE_PROVENANCE,
    EXPECTATION_GAP,
    EXPECTATION_SNAPSHOT,
    FINANCIAL_TIME_SERIES,
    FORECAST_EVALUATION,
    KPI_METRICS,
    METHODOLOGY_DISCLOSURE,
    MONITORING_PLAN,
    MONITORING_PRIOR_RUN_REVIEW,
    PEERS_NORMALIZED,
    SCENARIO_SENSITIVITIES,
    SEMANTIC_CLAIMS,
    THESIS_SEMANTIC_SIGNAL_ASSESSMENT,
    VALUATION_RECONCILIATION,
    VALUATION_ROUTING,
)
from research_os.version import RESEARCH_OS_VERSION

DECISION_TS = datetime(2026, 8, 30, tzinfo=timezone.utc)
SHA = subprocess.check_output(("git", "rev-parse", "HEAD"), text=True).strip()


class _Attestor:
    def attest(self) -> RepositoryAttestation:
        return RepositoryAttestation(
            repository_host="github.com",
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            head_sha=SHA,
        )


def _context(
    company_id: str, values: dict[str, object]
) -> tuple[ResearchContext, dict[str, object]]:
    evidence = tuple(
        Evidence(
            evidence_id=f"ev:{fact_id}",
            revision_no=1,
            company_id=company_id,
            evidence_type="filing_fact",
            publish_ts=DECISION_TS,
            ingested_at=DECISION_TS,
            value=value,
            source_table=fact_id,
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        )
        for fact_id, value in values.items()
    )
    evidence_view = EvidenceView(evidence, company_id=company_id, decision_ts=DECISION_TS)
    refs = {ref.evidence_id.removeprefix("ev:"): ref for ref in evidence_view.refs()}
    context = ResearchContext(
        run_id=f"run:{company_id}",
        company=CompanyRef(company_id=company_id),
        decision_ts=DECISION_TS,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha=SHA,
            research_os_version=RESEARCH_OS_VERSION,
            core_api_version="2.0",
        ),
        evidence=evidence_view,
        facts=FactView(
            company_id=company_id,
            decision_ts=DECISION_TS,
            values=values,
            evidence_refs_by_fact={key: (refs[key],) for key in values},
            reporting_period=ReportingPeriod(period_type="FY"),
            accounting_scope=AccountingScope(),
        ),
    )
    return context, refs


def _application() -> ResearchApplication:
    return ResearchApplication.build(repository_attestor=_Attestor())


def test_substantive_professional_inputs_produce_canonical_artifacts() -> None:
    values = {
        "business_description": "precision manufacturing producer",
        "revenue": 1_000.0,
        "net_profit_parent": 80.0,
        "assets_begin": 800.0,
        "assets_end": 920.0,
        "equity_begin": 410.0,
        "equity_end": 470.0,
    }
    context, refs = _context("synthetic:v1.6.01:manufacturing", values)
    revenue_ref = refs["revenue"]
    assumption_ref = AssumptionRef(
        assumption_key="raw-material-shock",
        assumption_version="1",
        content_fingerprint="a" * 64,
    )
    rich = ResearchRunCommand(
        context=context,
        financial=FinancialResearchInput(
            time_series=(
                FinancialTimeSeries(
                    metric_id="revenue",
                    unit="CNY",
                    points=(
                        FinancialSeriesPoint(
                            period="2025FY",
                            period_end=datetime(2025, 12, 31, tzinfo=timezone.utc),
                            value=900.0,
                            evidence_refs=(revenue_ref,),
                        ),
                        FinancialSeriesPoint(
                            period="2026FY",
                            period_end=datetime(2026, 12, 31, tzinfo=timezone.utc),
                            value=1_000.0,
                            evidence_refs=(revenue_ref,),
                        ),
                    ),
                ),
            ),
            cash_flow_quality=CashFlowQualityInput(
                net_profit=80.0,
                operating_cash_flow=95.0,
                capex_cash=30.0,
                evidence_refs=(revenue_ref,),
            ),
        ),
        thesis=ThesisResearchInput(
            cycle_recovery_observed=True,
            cycle_turning_point_support=ResearchAssertion(
                assertion_key="cycle-support",
                statement="Recovery evidence exists but trough confirmation is incomplete.",
                status="SUPPORTED",
                evidence_refs=(revenue_ref,),
            ),
            moat_evidence=(
                ResearchAssertion(
                    assertion_key="technical-barrier",
                    statement="Technical qualification barrier is evidenced.",
                    status="SUPPORTED",
                    evidence_refs=(revenue_ref,),
                ),
            ),
        ),
        expectations=ExpectationResearchInput(
            vintage=ConsensusVintage(
                company_id=context.company.company_id,
                as_of=datetime(2026, 8, 20, tzinfo=timezone.utc),
                forecast_period="2026FY",
                revenue=1_050.0,
                source_count=5,
                source_quality=0.9,
                evidence_refs=(revenue_ref,),
            ),
            gap=ExpectationGap(
                domain_status="SUPPORTED",
                metric_id="revenue",
                market_value=1_050.0,
                os_value=1_000.0,
                direction="BELOW_MARKET",
                magnitude=-50.0,
                comparison_basis="2026FY revenue CNY",
                evidence_refs=(revenue_ref,),
            ),
            consensus_observations=(
                ConsensusObservation(
                    source_key="consensus:a",
                    publish_ts=datetime(2026, 8, 20, tzinfo=timezone.utc),
                    forecast_period="2026FY",
                    metric_id="revenue",
                    value=1_050.0,
                    evidence_refs=(revenue_ref,),
                ),
            ),
        ),
        peers=PeerResearchInput(
            peer_comparables=(
                PeerComparableObservation(
                    peer_key="peer:a",
                    peer_role="operating_peer",
                    metric_id="gross_margin",
                    period="2026H1",
                    value=0.30,
                    unit="ratio",
                    accounting_scope="consolidated",
                    evidence_refs=(revenue_ref,),
                ),
            )
        ),
        valuation=ValuationResearchInput(
            models=(
                ValuationModelInput(
                    model_id="dcf",
                    fitness=ModelFitnessInputs(
                        data_quality=0.9,
                        earnings_stability=0.8,
                        cash_flow_visibility=0.8,
                        capital_structure_fit=0.8,
                        business_model_fit=0.9,
                        forecast_stability=0.8,
                    ),
                ),
                ValuationModelInput(
                    model_id="pe",
                    fitness=ModelFitnessInputs(
                        data_quality=0.9,
                        earnings_stability=0.9,
                        cash_flow_visibility=0.8,
                        capital_structure_fit=0.8,
                        business_model_fit=0.9,
                        forecast_stability=0.8,
                    ),
                ),
            ),
            execution=ValuationExecution(
                domain_status="SUPPORTED",
                results=(
                    ValuationResult(
                        model_key="dcf",
                        status="SUPPORTED",
                        formula_version="dcf@1",
                        value=22.0,
                        unit="CNY/share",
                        evidence_refs=(revenue_ref,),
                    ),
                    ValuationResult(
                        model_key="pe",
                        status="SUPPORTED",
                        formula_version="pe@1",
                        value=23.0,
                        unit="CNY/share",
                        evidence_refs=(revenue_ref,),
                    ),
                ),
                evidence_refs=(revenue_ref,),
            ),
            ranges=(
                ValuationRange(
                    range_key="dcf",
                    low=18.0,
                    high=24.0,
                    basis="equity_value_per_share",
                    currency="CNY",
                    role="model_implied",
                    evidence_refs=(revenue_ref,),
                ),
                ValuationRange(
                    range_key="pe",
                    low=20.0,
                    high=26.0,
                    basis="equity_value_per_share",
                    currency="CNY",
                    role="model_implied",
                    evidence_refs=(revenue_ref,),
                ),
            ),
            rationales=(
                ValuationRationale(
                    model_key="dcf",
                    rationale="Cash-flow visibility supports bounded DCF use.",
                    evidence_refs=(revenue_ref,),
                ),
            ),
        ),
        monitoring=MonitoringResearchInput(
            monitoring_rules=(
                MonitoringRule(
                    rule_key="gross-margin-floor",
                    metric_id="gross_margin",
                    operator="lt",
                    threshold=0.25,
                    frequency="quarterly",
                    rationale="Margin compression would weaken the thesis.",
                    evidence_refs=(revenue_ref,),
                ),
            ),
            next_verification_event=VerificationEvent(
                event_key="next-report",
                label="Next periodic filing",
                event_type="filing",
                due_ts=datetime(2026, 10, 31, tzinfo=timezone.utc),
                status="scheduled",
                evidence_refs=(revenue_ref,),
            ),
        ),
        readiness=ResearchReadinessInput(
            sensitivities=(
                SensitivityCase(
                    case_key="raw-material+5",
                    driver_key="raw-material-price",
                    shock_label="+5%",
                    affected_metric="gross_margin",
                    formula_version="sensitivity@1",
                    base_value=0.30,
                    shock_value=0.05,
                    result=0.28,
                    material_assumptions=(
                        ScenarioAssumption(
                            reference=assumption_ref,
                            label="Other variables held constant",
                            value=True,
                        ),
                    ),
                    model_boundary="Single-factor sensitivity only",
                    evidence_refs=(revenue_ref,),
                ),
            )
        ),
        options=ResearchRunOptions(persist_snapshot=False),
    )

    result = _application().run(rich)
    facts_only = _application().run(
        ResearchRunCommand(
            context=context,
            options=ResearchRunOptions(persist_snapshot=False),
        )
    )

    assert semantic_fingerprint(result.artifacts) != semantic_fingerprint(facts_only.artifacts)

    for key in (
        FINANCIAL_TIME_SERIES,
        EXPECTATION_SNAPSHOT,
        EXPECTATION_GAP,
        PEERS_NORMALIZED,
        VALUATION_ROUTING,
        VALUATION_RECONCILIATION,
        SCENARIO_SENSITIVITIES,
        MONITORING_PLAN,
        THESIS_SEMANTIC_SIGNAL_ASSESSMENT,
        SEMANTIC_CLAIMS,
        METHODOLOGY_DISCLOSURE,
    ):
        assert result.artifacts.get(key) is not None, key.artifact_id

    semantic = result.artifacts.require(THESIS_SEMANTIC_SIGNAL_ASSESSMENT)
    labels = {item.metric_id: item.semantic_label for item in semantic.signals}
    assert labels["cycle_recovery"] == "RECOVERY_OBSERVED_TROUGH_UNCONFIRMED"
    assert labels["economic_moat"] == "BARRIER_EVIDENCE_PRESENT_ECONOMIC_MOAT_UNCONFIRMED"

    decision_provenance = result.artifacts.require(DECISION_STATE_PROVENANCE)
    provenance_dimensions = {item.dimension for item in decision_provenance.inputs}
    assert {"valuation", "expectation", "semantic_signals"} <= provenance_dimensions

    dimensions = {item.dimension_id: item.status for item in result.research_readiness.dimensions}
    assert dimensions["time_series"] == "INCOMPLETE"
    for dimension_id in (
        "cash_flow",
        "consensus",
        "peers",
        "sensitivity",
        "monitoring_events",
    ):
        assert dimensions[dimension_id] == "PASS"
    assert dimensions["operating_evidence"] == "INCOMPLETE"
    assert dimensions["prior_run_validation"] == "INCOMPLETE"


def test_distributor_funding_loop_can_veto_decision_through_canonical_provenance() -> None:
    values = {
        "business_description": "semiconductor distributor and supply-chain service provider",
        "revenue": 10_000.0,
        "net_profit_parent": 100.0,
        "assets_begin": 8_000.0,
        "assets_end": 9_000.0,
        "equity_begin": 1_500.0,
        "equity_end": 1_600.0,
        "delta_revenue": 1_000.0,
        "delta_nwc": 800.0,
        "delta_debt": 900.0,
        "external_equity_financing": 0.0,
        "operating_cash_flow": -200.0,
        "factoring_balance": 300.0,
        "ar": 1_000.0,
        "delta_revenue_comparison_basis": "YOY_PERIOD",
        "delta_nwc_comparison_basis": "YOY_PERIOD",
        "delta_debt_comparison_basis": "YOY_PERIOD",
        "external_equity_financing_comparison_basis": "YOY_PERIOD",
    }
    context, refs = _context("synthetic:v1.6.01:distributor", values)
    thesis_ref = refs["revenue"]
    command = ResearchRunCommand(
        context=context,
        thesis=ThesisResearchInput(
            prior_theses=(
                Thesis(
                    thesis_key="distribution-scale",
                    company_id=context.company.company_id,
                    title="Scale remains investable only if cash conversion stabilizes",
                    statement="Growth remains conditional on cash conversion.",
                    mechanism="Working-capital intensity transmits growth into financing needs.",
                    anti_thesis="Debt-funded working-capital growth can destroy equity value.",
                    status="active",
                    falsifier_statements=("Funding loop remains stressed",),
                    next_check_date=date(2026, 10, 31),
                    confidence=0.9,
                    claim_strength="STRONG",
                    evidence_refs=(thesis_ref,),
                ),
            )
        ),
        options=ResearchRunOptions(persist_snapshot=False),
    )

    result = _application().run(command)
    funding = result.artifacts.require(CAPITAL_FUNDING_LOOP)
    decision = result.artifacts.require(DECISION_RECORD)
    provenance = result.artifacts.require(DECISION_STATE_PROVENANCE)

    assert funding.funding_state in {"debt_funded", "stressed"}
    assert "NEGATIVE_OCF" in funding.reason_codes
    assert decision.state == "RISK_REVIEW"
    assert "MATERIAL_FUNDING_RISK" in decision.reason_codes
    assert any(item.dimension == "funding_loop" for item in provenance.inputs)


def test_forecast_without_out_of_sample_benchmark_stays_typed_insufficient() -> None:
    values = {
        "business_description": "precision manufacturing producer",
        "revenue": 1_000.0,
        "net_profit_parent": 80.0,
        "assets_begin": 800.0,
        "assets_end": 920.0,
        "equity_begin": 410.0,
        "equity_end": 470.0,
    }
    context, refs = _context("synthetic:v1.6.01:forecast", values)
    command = ResearchRunCommand(
        context=context,
        forecasting=ForecastResearchInput(
            hypotheses=(
                ForecastHypothesis(
                    hypothesis_key="revenue-growth",
                    statement="Revenue growth persists into the next filing period.",
                    target_metric="revenue",
                    horizon="next_filing",
                    evidence_refs=(refs["revenue"],),
                ),
            )
        ),
        monitoring=MonitoringResearchInput(
            prior_run_reviews=(
                PriorRunReviewInput(
                    item_key="prior-revenue",
                    prior_statement="Revenue would be near 1,000.",
                    metric_id="revenue",
                    predicted_value=990.0,
                    actual_value=1_000.0,
                    tolerance=20.0,
                    evidence_refs=(refs["revenue"],),
                ),
            )
        ),
        options=ResearchRunOptions(persist_snapshot=False),
    )

    result = _application().run(command)
    forecast = result.artifacts.require(FORECAST_EVALUATION)
    review = result.artifacts.require(MONITORING_PRIOR_RUN_REVIEW)

    assert forecast.domain_status == "INSUFFICIENT_EVIDENCE"
    assert forecast.evaluation_status == "INSUFFICIENT_EVIDENCE"
    assert review.scored_count == 1
    assert review.hit_count == 1
    assert review.items[0].status == "HIT"


def test_hospitality_without_compatible_plugin_discloses_gap_without_kpi_fabrication() -> None:
    values = {
        "business_description": "hotel owner and operator with lease-heavy properties",
        "revenue": 331_000_000.0,
        "net_profit_parent": 9_500_000.0,
        "operating_cash_flow": 123_000_000.0,
        "right_of_use_assets": 280_000_000.0,
        "lease_liabilities": 300_000_000.0,
    }
    context, _ = _context("synthetic:v1.6.01:hospitality", values)
    result = _application().run(
        ResearchRunCommand(
            context=context,
            options=ResearchRunOptions(persist_snapshot=False),
        )
    )

    methodology = result.artifacts.require(METHODOLOGY_DISCLOSURE)
    metrics = result.artifacts.require(KPI_METRICS)

    assert methodology.limitations
    assert any("hospitality" in item.lower() for item in methodology.limitations)
    assert metrics.metrics == ()
