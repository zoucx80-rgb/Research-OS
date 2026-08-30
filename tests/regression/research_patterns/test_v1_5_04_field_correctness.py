from datetime import date, datetime, timezone

import pytest

from research_os.capital.engine import CapitalEfficiencyEngine
from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.drivers.graph import DriverGraph
from research_os.events.validation import NextVerificationEvent
from research_os.kpi.distributor import DistributorPack
from research_os.reporting.research_view import ResearchViewPresenter
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
from research_os.thesis.service import ThesisService
from research_os.validation.financial import FinancialSanityValidator
from research_os.valuation.fitness import ModelFitnessInputs
from research_os.valuation.router import ValuationContext, ValuationRouter


DECISION_TS = datetime(2026, 8, 30, tzinfo=timezone.utc)


def _evidence(key: str, value, *, company_id: str = "synthetic:v1.5.04") -> Evidence:
    return Evidence(
        evidence_id=f"ev:{company_id}:{key}",
        company_id=company_id,
        evidence_type=EvidenceType.FILING_FACT,
        period_end=date(2026, 6, 30),
        period="2026H1",
        publish_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        ingested_at=DECISION_TS,
        value=value,
        source_table=key,
        confidence_grade=ConfidenceGrade.A,
        verification_status=VerificationStatus.PRIMARY_VERIFIED,
    )


def _context(company_id: str, facts: dict) -> ResearchContext:
    items = [_evidence(key, value, company_id=company_id) for key, value in facts.items()]
    return ResearchContext(
        run_id=f"run:v1.5.04:{company_id}",
        company=CompanyRef(company_id=company_id),
        decision_ts=DECISION_TS,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="d7a6d041ae23f2464b4aeff45d4d98e5d00f0b01",
            research_os_version="1.5.3",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(items),
        facts=LegacyFactView(
            values=facts,
            evidence_by_fact={key: [f"ev:{company_id}:{key}"] for key in facts},
        ),
        options=ResearchOptions(),
    )


def _high_fitness() -> ModelFitnessInputs:
    return ModelFitnessInputs(
        data_quality=0.9,
        earnings_stability=0.9,
        cash_flow_visibility=0.9,
        capital_structure_fit=0.9,
        business_model_fit=0.9,
        forecast_stability=0.9,
    )


def test_reported_yoy_rounding_does_not_fail_financial_sanity():
    validator = FinancialSanityValidator()
    reported_values = (
        (2_053_495_665.67, 1_816_543_136.68, 0.1304),
        (73_555_689_191.12, 27_841_694_363.40, 1.6419),
        (331_023_877.63, 326_420_000.00, 0.0141),
    )

    results = [
        validator.check_yoy(current=current, previous=previous, declared_growth=reported)
        for current, previous, reported in reported_values
    ]

    assert [item.status for item in results] == ["PASS", "PASS", "PASS"]
    assert validator.check_yoy(
        current=113.046,
        previous=100.0,
        declared_growth=0.1304,
    ).status == "FAIL"


def test_negative_ocf_triggers_cash_thesis_falsifier_and_limits_lineage():
    company_id = "synthetic:cash-thesis"
    items = [
        _evidence("revenue", 73_555.0, company_id=company_id),
        _evidence("delta_nwc", 17_470.0, company_id=company_id),
        _evidence("delta_debt", 16_392.0, company_id=company_id),
        _evidence("ocf", -17_500.0, company_id=company_id),
        _evidence("unrelated_brand_fact", "not a cash driver", company_id=company_id),
    ]
    graph = DriverGraph.build(company_id, ["distributor"], items)

    thesis = ThesisService().evaluate(company_id, items, graph)[0]

    assert thesis.status == "weakening"
    assert thesis.falsifiers[0].metric == "ocf"
    assert thesis.triggered_falsifiers == ["ocf < 0.0"]
    assert f"ev:{company_id}:ocf" in thesis.supporting_evidence
    assert f"ev:{company_id}:unrelated_brand_fact" not in thesis.supporting_evidence


def test_book_equity_change_is_not_external_financing_or_dilution():
    result = CapitalEfficiencyEngine().funding_loop(
        {
            "delta_nwc": 100.0,
            "delta_nwc_comparison_basis": "2026H1_vs_2025H1",
            "delta_debt": 0.0,
            "delta_debt_comparison_basis": "2026H1_vs_2025H1",
            "delta_equity": 25.0,
            "operating_cash_flow": -10.0,
        }
    )

    assert result.funding_state == "unknown"
    assert result.incremental_equity is None
    assert result.reported_equity_change == 25.0
    assert "EQUITY_DILUTION" not in result.reason_codes


def test_incomparable_delta_bases_do_not_produce_incremental_ratios():
    facts = {
        "delta_nwc": 60.0,
        "delta_nwc_comparison_basis": "2026H1_vs_2025YE",
        "delta_revenue": 100.0,
        "delta_revenue_comparison_basis": "2026H1_vs_2025H1",
    }

    capital = CapitalEfficiencyEngine().calculate(facts)
    metrics = {item.metric_id: item for item in DistributorPack().calculate(facts)}

    assert capital.iwcr is None
    assert capital.iwcr_reason_code == "COMPARISON_BASIS_MISMATCH"
    assert metrics["incremental_nwc_intensity"].value is None
    assert metrics["incremental_nwc_intensity"].reason_code == "COMPARISON_BASIS_MISMATCH"


def test_debt_funded_negative_ocf_distributor_cannot_route_pe_as_primary():
    routing = ValuationRouter().route(
        ValuationContext(
            business_model="distributor",
            models={"pe": _high_fitness(), "pb": _high_fitness()},
            funding_state="debt_funded",
            funding_reason_codes=["DEBT_FUNDS_NWC", "NEGATIVE_OCF"],
        )
    )

    assert routing.models["pe"].status != "PRIMARY"
    assert "pe" not in routing.primary_models
    assert "CASH_FUNDING_RISK_PE_PENALTY" in routing.models["pe"].reason_codes
    assert routing.models["pb"].status == "PRIMARY"


def test_professional_view_projects_material_canonical_artifacts():
    company_id = "synthetic:material-view"
    basis = "2026H1_vs_2025H1"
    facts = {
        "business_description": "authorized electronics component distribution",
        "revenue": 1_000.0,
        "cogs": 970.0,
        "gross_profit": 30.0,
        "avg_ar": 200.0,
        "avg_inventory": 300.0,
        "avg_ap": 100.0,
        "ar": 250.0,
        "inventory": 350.0,
        "ap": 120.0,
        "delta_nwc": 60.0,
        "delta_nwc_comparison_basis": basis,
        "delta_revenue": 100.0,
        "delta_revenue_comparison_basis": basis,
        "delta_debt": 55.0,
        "delta_debt_comparison_basis": basis,
        "external_equity_financing": 0.0,
        "external_equity_financing_comparison_basis": basis,
        "short_debt": 300.0,
        "equity": 150.0,
        "ocf": -50.0,
        "net_profit": 15.0,
        "period_type": "H1",
        "period_days": 181,
    }
    result = ResearchRuntimeFactory.default().run_context(
        _context(company_id, facts),
        ResearchInputs(
            valuation_models={"pe": _high_fitness(), "pb": _high_fitness()},
            next_verification_event=NextVerificationEvent(
                event_name="下一次营运资金和现金流披露",
            ),
        ),
    )

    view = ResearchViewPresenter().build(result)

    assert view.financial_sanity is not None
    assert view.financial_sanity.status.code == result.module_results["core:financial-sanity"].status
    assert "不代表经营状况健康" in view.financial_sanity.explanation
    assert view.capital_efficiency is not None
    assert view.capital_efficiency.iwcr == pytest.approx(result.artifacts["capital.efficiency"].iwcr)
    assert view.forecast_discipline is not None
    assert view.forecast_discipline.status.code == result.module_results["core:forecast-discipline"].status
    assert view.next_verification_event is not None
    assert view.next_verification_event.event_name == "下一次营运资金和现金流披露"
