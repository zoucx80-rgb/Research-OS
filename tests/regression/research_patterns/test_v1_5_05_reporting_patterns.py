from datetime import datetime, timezone

from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.reporting import CausalBridgeBlock, ResearchReportComposer, ResearchViewPresenter
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
from research_os.valuation.execution import ValuationExecution


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
        run_id=f"run:{company_id}:v1.5.05-reporting",
        company=CompanyRef(company_id=company_id),
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="c" * 40,
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


def _document(company_id: str, values: dict, inputs: ResearchInputs | None = None):
    result = ResearchRuntimeFactory.default().run_context(
        _context(company_id, values),
        inputs or ResearchInputs(),
    )
    view = ResearchViewPresenter().build(result)
    return result, view, ResearchReportComposer().compose(view)


def test_manufacturing_pattern_composes_supported_operating_to_cash_bridge():
    values = {
        "business_description": "advanced alloy manufacturing producer",
        "revenue": 100.0,
        "revenue_growth": 0.15,
        "net_profit_parent": 10.0,
        "assets_begin": 80.0,
        "assets_end": 90.0,
        "equity_begin": 45.0,
        "equity_end": 50.0,
        "gross_margin": 0.25,
        "margin_change": 0.02,
        "ar_begin": 10.0,
        "ar_end": 12.0,
        "inventory_begin": 15.0,
        "inventory_end": 14.0,
        "cogs": 75.0,
        "ocf": 13.0,
        "capex_cash": 4.0,
        "ppe_begin": 20.0,
        "ppe_end": 24.0,
        "period_type": "H1",
        "period_days": 181,
    }
    result, view, doc = _document("synthetic:manufacturing-report", values)

    assert result.business_model.primary_model == "manufacturing"
    bridges = [
        block
        for section in doc.sections
        for block in section.blocks
        if isinstance(block, CausalBridgeBlock)
    ]
    assert bridges
    assert any("收入" in step for step in bridges[0].steps)
    assert any("经营现金流" in step or "自由现金流" in step for step in bridges[0].steps)
    assert view.presentation_limitations == []


def test_distributor_pattern_composes_funding_and_valuation_chain_without_relabeling_state():
    values = {
        "business_description": "authorized electronics component distribution",
        "revenue": 1000.0,
        "revenue_growth": 0.60,
        "cogs": 970.0,
        "gross_profit": 30.0,
        "gross_margin": 0.03,
        "avg_ar": 200.0,
        "avg_inventory": 300.0,
        "avg_ap": 100.0,
        "ar": 250.0,
        "inventory": 350.0,
        "ap": 120.0,
        "delta_nwc": 100.0,
        "delta_revenue": 300.0,
        "delta_debt": 90.0,
        "short_debt": 300.0,
        "equity": 150.0,
        "interest_expense": 10.0,
        "ocf": -50.0,
        "net_profit": 15.0,
        "external_equity_financing": 0.0,
        "delta_nwc_comparison_basis": "2026H1_vs_2025H1",
        "delta_revenue_comparison_basis": "2026H1_vs_2025H1",
        "delta_debt_comparison_basis": "2026H1_vs_2025H1",
        "external_equity_financing_comparison_basis": "2026H1_vs_2025H1",
        "period_type": "H1",
        "period_days": 181,
    }
    execution = ValuationExecution(
        selected_model="dcf",
        model_fitness_score=0.8,
        selection_reason="cash economics",
        executed_model="dcf",
        business_model="distributor",
        inputs={"cash_economics": 1.0},
        assumptions=[],
        scenario_logic="three cases",
        lineage={"cash_economics": ["ev:valuation"]},
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
    result, view, doc = _document(
        "synthetic:distributor-report",
        values,
        ResearchInputs(valuation_execution=execution),
    )

    assert result.business_model.primary_model == "distributor"
    assert doc.decision_snapshot.decision_state == view.decision_summary.decision_state
    bridges = [
        block
        for section in doc.sections
        for block in section.blocks
        if isinstance(block, CausalBridgeBlock)
    ]
    assert bridges
    joined = " → ".join(bridges[0].steps)
    assert "营运资金" in joined
    assert "融资成本" in joined
    assert "估值" in joined


def test_lease_heavy_hospitality_without_plugin_surfaces_capability_break_and_no_fake_hotel_kpis():
    values = {
        "business_description": "hotel hospitality lodging management and operations",
        "fixed_asset_to_assets": 0.01,
        "right_of_use_assets_to_assets": 0.49,
        "lease_liabilities_to_assets": 0.51,
        "revenue": 100.0,
        "ocf": 25.0,
        "period_type": "H1",
        "period_days": 181,
    }
    result, view, doc = _document("synthetic:hospitality-report", values)

    assert result.business_model.primary_model == "hospitality"
    assert result.business_model.lease_heavy is True
    assert view.industry_plugins == []
    assert view.coverage_gaps
    main_body = str([section.model_dump(mode="json") for section in doc.sections])
    assert "兼容的行业策略插件" in main_body
    assert "租赁" in main_body
    for unsupported in ("RevPAR", "ADR", "OCC", "同店", "成熟店曲线"):
        assert unsupported not in main_body
    for unsafe_claim in ("现金转化极佳", "轻资产", "低资本占用"):
        assert unsafe_claim not in main_body
