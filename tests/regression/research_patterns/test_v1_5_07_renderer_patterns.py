from datetime import datetime, timezone

from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.reporting import (
    ResearchReportComposer,
    ResearchReportMarkdownRenderer,
    ResearchViewPresenter,
)
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
        run_id=f"run:{company_id}:v1.5.07-renderer",
        company=CompanyRef(company_id=company_id),
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="d" * 40,
            research_os_version="1.5.7",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(
            values=values,
            evidence_by_fact={key: [f"ev:{company_id}:{key}"] for key in values},
        ),
        options=ResearchOptions(),
    )


def _render(company_id: str, values: dict, inputs: ResearchInputs | None = None) -> str:
    result = ResearchRuntimeFactory.default().run_context(
        _context(company_id, values),
        inputs or ResearchInputs(),
    )
    view = ResearchViewPresenter().build(result)
    document = ResearchReportComposer().compose(view)
    return ResearchReportMarkdownRenderer().render(document)


def test_manufacturing_renderer_exposes_operating_kpis_and_cash_bridge_without_raw_ids_in_body():
    text = _render(
        "synthetic:manufacturing-renderer",
        {
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
        },
    )

    body = text.split("## 审计附录", 1)[0]
    assert "## 财务与经营表现" in body
    assert "### 关键经营指标" in body
    assert "## 关键因果链" in body
    assert "经营现金流" in body or "自由现金流" in body
    assert "ev:synthetic:manufacturing-renderer" not in body


def test_distributor_renderer_keeps_working_capital_financing_and_factoring_semantics_visible():
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
    text = _render(
        "synthetic:distributor-renderer",
        {
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
            "factoring_balance": 60.0,
            "derecognized_receivables": 40.0,
            "external_equity_financing": 0.0,
            "delta_nwc_comparison_basis": "2026H1_vs_2025H1",
            "delta_revenue_comparison_basis": "2026H1_vs_2025H1",
            "delta_debt_comparison_basis": "2026H1_vs_2025H1",
            "external_equity_financing_comparison_basis": "2026H1_vs_2025H1",
            "period_type": "H1",
            "period_days": 181,
        },
        ResearchInputs(valuation_execution=execution),
    )

    body = text.split("## 审计附录", 1)[0]
    assert "## 资本效率与融资循环" in body
    assert "经营现金流" in body
    assert "保理" in body
    assert "## 关键因果链" in body
    assert "营运资金" in body
    assert "融资成本" in body
    assert "估值" in body
    assert "保理余额就是债务" not in body
    assert "保理即债务" not in body


def test_lease_heavy_hospitality_renderer_surfaces_limits_without_fake_hotel_kpis():
    text = _render(
        "synthetic:hospitality-renderer",
        {
            "business_description": "hotel hospitality lodging management and operations",
            "fixed_asset_to_assets": 0.01,
            "right_of_use_assets_to_assets": 0.49,
            "lease_liabilities_to_assets": 0.51,
            "revenue": 100.0,
            "ocf": 25.0,
            "period_type": "H1",
            "period_days": 181,
        },
    )

    body = text.split("## 审计附录", 1)[0]
    assert "## 研究缺口分类" in body
    assert "能力缺口" in body
    assert "租赁" in body
    for unsupported in ("RevPAR", "ADR", "OCC", "同店", "成熟店曲线"):
        assert unsupported not in body
    for unsafe_claim in ("现金转化极佳", "轻资产", "低资本占用"):
        assert unsafe_claim not in body
