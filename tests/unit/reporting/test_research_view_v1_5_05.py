from datetime import datetime, timezone

from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.expectations.models import ExpectationGapResult
from research_os.reporting import ResearchViewPresenter
from research_os.runtime import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchInputs,
    ResearchOptions,
)
from research_os.runtime.factory import ResearchRuntimeFactory
from research_os.valuation.execution import ValuationExecution, ValuationResult
from research_os.valuation.fitness import ModelFitnessInputs


def _context(company_id: str, values: dict) -> ResearchContext:
    publish_ts = datetime(2026, 8, 1, tzinfo=timezone.utc)
    evidence = [
        Evidence(
            evidence_id=f"ev:{company_id}:{key}",
            company_id=company_id,
            evidence_type=EvidenceType.FILING_FACT,
            publish_ts=publish_ts,
            ingested_at=publish_ts,
            value=value,
            source_table=key,
            confidence_grade=ConfidenceGrade.A,
            verification_status=VerificationStatus.PRIMARY_VERIFIED,
        )
        for key, value in values.items()
    ]
    return ResearchContext(
        run_id=f"run:{company_id}:v1.5.05-view",
        company=CompanyRef(company_id=company_id),
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="5" * 40,
            research_os_version="1.5.5",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(
            values=values,
            evidence_by_fact={key: [f"ev:{company_id}:{key}"] for key in values},
        ),
        options=ResearchOptions(),
    )


def _fitness():
    return ModelFitnessInputs(
        data_quality=0.9,
        earnings_stability=0.8,
        cash_flow_visibility=0.7,
        capital_structure_fit=0.9,
        business_model_fit=0.9,
        forecast_stability=0.8,
    )


def test_view_projects_explicit_expectation_gap_and_valuation_result_without_recalculation():
    company_id = "synthetic:v1.5.05-view"
    values = {
        "business_description": "manufacturing producer",
        "revenue": 100.0,
        "net_profit_parent": 8.0,
        "assets_begin": 80.0,
        "assets_end": 90.0,
        "equity_begin": 50.0,
        "equity_end": 55.0,
        "period_type": "H1",
        "period_days": 181,
    }
    expectation_gap = ExpectationGapResult(
        metric="revenue",
        market_value=100.0,
        os_value=120.0,
        direction="ABOVE",
        magnitude=20.0,
        source_count=3,
        source_quality=0.8,
        evidence_ids=["consensus:1", "os:1"],
    )
    valuation_result = ValuationResult(
        currency="CNY",
        bear_case=14.0,
        base_case=18.0,
        bull_case=22.0,
        primary_range_low=16.0,
        primary_range_high=20.0,
        current_price=15.0,
        implied_upside_downside=0.20,
        evidence_ids=["valuation:1"],
    )
    execution = ValuationExecution(
        selected_model="dcf",
        model_fitness_score=0.8,
        selection_reason="cash economics",
        executed_model="dcf",
        business_model="manufacturing",
        inputs={"fcf": 1.0},
        assumptions=[],
        scenario_logic="three cases",
        lineage={"fcf": ["valuation:1"]},
        driver_bridge=["FCF", "Valuation"],
        result=valuation_result,
    )
    result = ResearchRuntimeFactory.default().run_context(
        _context(company_id, values),
        ResearchInputs(
            expectation_gap=expectation_gap,
            valuation_models={"dcf": _fitness()},
            valuation_execution=execution,
        ),
    )
    before = result.model_dump(mode="json")

    view = ResearchViewPresenter().build(result)

    assert view.presentation_version == "professional-research-view@1.3.0"
    assert view.expectation_gap is not None
    assert view.expectation_gap.direction.code == "ABOVE"
    assert view.expectation_gap.magnitude == 20.0
    assert view.expectation_gap.evidence_ids == ["consensus:1", "os:1"]
    assert view.valuation_result is not None
    assert view.valuation_result.base_case == 18.0
    assert view.valuation_result.primary_range_low == 16.0
    assert view.valuation_result.implied_upside_downside == 0.20
    assert result.model_dump(mode="json") == before


def test_lease_heavy_profile_projects_limitation_without_lease_adjusted_calculation():
    company_id = "synthetic:lease-heavy-view"
    values = {
        "business_description": "hotel hospitality lodging management and operations",
        "fixed_asset_to_assets": 0.01,
        "right_of_use_assets_to_assets": 0.49,
        "lease_liabilities_to_assets": 0.51,
        "revenue": 100.0,
        "ocf": 25.0,
        "cfo": 25.0,
        "period_type": "H1",
        "period_days": 181,
    }
    result = ResearchRuntimeFactory.default().run_context(
        _context(company_id, values),
        ResearchInputs(),
    )
    view = ResearchViewPresenter().build(result)

    assert result.business_model.lease_heavy is True
    assert any("租赁" in item for item in view.presentation_limitations)
    assert all("租赁调整后的资本回报" not in item or "未计算" in item for item in view.presentation_limitations)
    assert view.theses == []


def test_monitoring_projection_uses_only_canonical_falsifiers_and_next_event():
    company_id = "synthetic:monitoring-view"
    values = {
        "business_description": "authorized electronics component distribution",
        "revenue": 1000.0,
        "cogs": 970.0,
        "avg_ar": 200.0,
        "avg_inventory": 300.0,
        "avg_ap": 100.0,
        "ar": 250.0,
        "inventory": 350.0,
        "ap": 120.0,
        "delta_nwc": 100.0,
        "delta_revenue": 300.0,
        "short_debt": 300.0,
        "equity": 150.0,
        "gross_profit": 30.0,
        "interest_expense": 10.0,
        "ocf": -50.0,
        "cfo": -50.0,
        "net_profit": 15.0,
        "delta_debt": 90.0,
        "external_equity_financing": 0.0,
        "delta_nwc_comparison_basis": "2026H1_vs_2025H1",
        "delta_revenue_comparison_basis": "2026H1_vs_2025H1",
        "delta_debt_comparison_basis": "2026H1_vs_2025H1",
        "external_equity_financing_comparison_basis": "2026H1_vs_2025H1",
        "period_type": "H1",
        "period_days": 181,
    }
    result = ResearchRuntimeFactory.default().run_context(
        _context(company_id, values),
        ResearchInputs(),
    )
    view = ResearchViewPresenter().build(result)

    assert view.monitoring is not None
    canonical = [f.explanation for thesis in view.theses for f in thesis.falsifiers]
    assert view.monitoring.thesis_broken_conditions == canonical
    assert view.monitoring.conviction_up_conditions == []
    assert view.monitoring.next_verification_event == view.decision_summary.next_verification_event
