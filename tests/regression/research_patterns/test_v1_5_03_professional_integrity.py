from datetime import date, datetime, timezone

from research_os.capital.engine import CapitalEfficiencyEngine, FundingLoopResult
from research_os.decision.models import DecisionStateRecord
from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.drivers.graph import DriverGraph
from research_os.expectations.models import ConsensusVintage
from research_os.expectations.validation import ExpectationEvidenceValidator
from research_os.kpi.base import MetricResult
from research_os.kpi.distributor import DistributorPack
from research_os.plugins.builtins import ManufacturingIndustryPlugin
from research_os.reporting.research_view import ResearchViewPresenter
from research_os.router.classifier import BusinessModelRouter
from research_os.runtime.builtin_modules import DecisionModule
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.runtime.inputs import ResearchInputs
from research_os.runtime.state import ResearchStateView
from research_os.thesis.models import Falsifier, Thesis
from research_os.thesis.service import ThesisService


def _evidence(key: str, value, *, company_id: str = "synthetic:v1.5.03", period: str | None = None) -> Evidence:
    ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    return Evidence(
        evidence_id=f"ev:{key}",
        company_id=company_id,
        evidence_type=EvidenceType.FILING_FACT,
        publish_ts=ts,
        ingested_at=ts,
        value=value,
        source_table=key,
        confidence_grade=ConfidenceGrade.A,
        verification_status=VerificationStatus.PRIMARY_VERIFIED,
        period=period,
    )


def _context(evidence: list[Evidence], values: dict | None = None) -> ResearchContext:
    facts = values or {item.source_table: item.value for item in evidence if item.source_table}
    by_fact = {
        key: [item.evidence_id for item in evidence if item.source_table == key]
        for key in facts
    }
    return ResearchContext(
        run_id="run:v1.5.03:red",
        company=CompanyRef(company_id="synthetic:v1.5.03"),
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="feature/v1.5.03-professional-research-integrity",
            commit_sha="1" * 40,
            research_os_version="1.5.2",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(values=facts, evidence_by_fact=by_fact),
        options=ResearchOptions(),
    )


def test_legacy_high_level_states_are_exposed_as_analyst_assumptions():
    evidence = [_evidence("revenue", 100.0)]
    context = _context(evidence)
    thesis = Thesis(
        thesis_id="synthetic:v1.5.03:thesis",
        company_id="synthetic:v1.5.03",
        title="Cash quality",
        statement="Growth should convert to cash.",
        mechanism="Working-capital efficiency supports cash generation.",
        anti_thesis="Growth remains externally funded.",
        status="active",
        falsifiers=[Falsifier(metric="cfo", operator="<", threshold=0)],
        next_check_date=date(2026, 11, 30),
    )
    module = DecisionModule(
        inputs=ResearchInputs(
            fundamental_state="IMPROVING",
            valuation_state="FAIR",
            expectation_state="IN_LINE",
        )
    )
    result = module.run(
        context,
        ResearchStateView(
            {
                "thesis.items": [thesis],
                "claims.items": [],
                "evidence.pit": evidence,
                "capital.funding_loop": FundingLoopResult(funding_state="self_funded"),
            }
        ),
    )
    provenance = result.artifacts["decision.state_provenance"]
    assert provenance["fundamental"].source == "analyst_assumption"
    assert provenance["fundamental"].value == "IMPROVING"
    assert provenance["valuation"].source == "analyst_assumption"
    assert provenance["expectation"].source == "analyst_assumption"


def test_manufacturing_driver_lineage_is_fact_specific_and_includes_supported_working_capital_nodes():
    evidence = [
        _evidence("revenue", 100.0),
        _evidence("gross_margin", 0.20),
        _evidence("ar_end", 30.0),
        _evidence("inventory_end", 40.0),
        _evidence("capex_cash", 5.0),
        _evidence("ocf", 12.0),
    ]
    graph = DriverGraph.build("synthetic:v1.5.03", ["manufacturing"], evidence)
    nodes = {node.driver_id: node for node in graph.nodes}
    assert "ar" in nodes
    assert "inventory" in nodes
    assert "capex" in nodes
    assert nodes["revenue"].evidence_ids == ["ev:revenue"]
    assert "ev:inventory_end" not in nodes["revenue"].evidence_ids
    assert nodes["ar"].evidence_ids == ["ev:ar_end"]


def test_manufacturing_mixed_signals_do_not_assert_fundamentals_improve():
    evidence = [
        _evidence("revenue_growth", 0.13),
        _evidence("margin_change", -0.03),
        _evidence("ocf", 100.0),
        _evidence("ar_growth", 0.60),
    ]
    graph = DriverGraph.build("synthetic:v1.5.03", ["manufacturing"], evidence)
    theses = ThesisService().evaluate("synthetic:v1.5.03", evidence, graph)
    assert theses
    assert theses[0].title != "Fundamentals improve"
    assert "mixed" in theses[0].title.lower() or "确认" in theses[0].statement


def test_builtin_industry_questions_have_structured_capability_and_evidence_contract():
    contributions = ManufacturingIndustryPlugin().report_contributions()
    specs = [spec for item in contributions for spec in item.question_specs]
    assert specs
    order = next(spec for spec in specs if spec.question_id == "manufacturing.orders_backlog")
    assert "manufacturing.orders" in order.required_capabilities
    assert "orders_backlog" in order.evidence_keys


def test_consensus_predating_material_event_is_low_quality_even_when_calendar_fresh():
    validator = ExpectationEvidenceValidator()
    decision_ts = datetime(2026, 8, 30, tzinfo=timezone.utc)
    material_event_ts = datetime(2026, 8, 29, tzinfo=timezone.utc)
    vintage = ConsensusVintage(
        company_id="synthetic:v1.5.03",
        as_of=datetime(2026, 7, 27, tzinfo=timezone.utc),
        forecast_period="2026",
        net_profit=100.0,
        source_count=4,
        source_quality=0.8,
    )
    quality = validator.assess_consensus_quality(
        vintage=vintage,
        decision_ts=decision_ts,
        latest_material_event_ts=material_event_ts,
    )
    assert quality.status == "LOW"
    assert quality.age_days == 34
    assert quality.post_event_consensus is False
    assert "CONSENSUS_PREDATES_MATERIAL_EVENT" in quality.reason_codes


def test_material_right_of_use_assets_suppress_low_ppe_distributor_heuristic():
    evidence = [
        _evidence("business_description", "hotel hospitality lodging operations"),
        _evidence("fixed_asset_to_assets", 0.01),
        _evidence("right_of_use_assets_to_assets", 0.49),
        _evidence("gross_margin", 0.08),
    ]
    profile = BusinessModelRouter().classify("synthetic:v1.5.03", evidence)
    assert profile.primary_model == "hospitality"
    assert "distributor" not in profile.secondary_models


def test_distributor_pack_exposes_factoring_and_total_financing_burden_without_relabeling_as_debt():
    facts = {
        "revenue": 1000.0,
        "cogs": 970.0,
        "avg_ar": 200.0,
        "avg_inventory": 150.0,
        "avg_ap": 100.0,
        "ar": 260.0,
        "inventory": 180.0,
        "ap": 110.0,
        "gross_profit": 30.0,
        "factoring_balance": 60.0,
        "derecognized_receivables": 60.0,
        "financing_cost": 9.0,
        "interest_expense": 4.0,
        "period_days": 181,
    }
    metrics = {item.metric_id: item for item in DistributorPack().calculate(facts)}
    assert metrics["factoring_to_ar"].value == 60.0 / 260.0
    assert metrics["total_financing_cost_to_gross_profit"].value == 0.3

    funding = CapitalEfficiencyEngine().funding_loop(
        {
            "delta_nwc": 100.0,
            "delta_revenue": 300.0,
            "delta_debt": 0.0,
            "delta_equity": 0.0,
            "operating_cash_flow": 20.0,
            "factoring_balance": 60.0,
            "ar": 260.0,
        }
    )
    assert "MATERIAL_FACTORING_EXPOSURE" in funding.reason_codes
    assert funding.funding_state != "debt_funded"


def test_human_readable_metric_formats_percentage_days_and_period_semantics():
    presenter = ResearchViewPresenter()
    margin = presenter._metric(
        MetricResult(
            metric_id="net_margin",
            value=0.0500955,
            unit="percent",
            status="valid",
            formula_version="finance-core@2.0.1",
            period_label="2026H1",
            period_days=181,
            annualized=False,
        )
    )
    days = presenter._metric(
        MetricResult(
            metric_id="ar_days",
            value=140.05,
            unit="days",
            status="valid",
            formula_version="finance-core@2.0.1",
            period_label="2026H1",
            period_days=181,
            annualized=False,
        )
    )
    assert margin.value == 0.0500955
    assert margin.formatted_value == "5.01%"
    assert margin.display_unit == "%"
    assert margin.period_label == "2026H1"
    assert margin.period_days == 181
    assert margin.annualized is False
    assert days.formatted_value == "140.05天"
