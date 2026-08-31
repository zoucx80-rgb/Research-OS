from datetime import datetime, timezone

from research_os.completeness import (
    CashFlowQualityInput,
    ConsensusObservation,
    FinancialSeriesPoint,
    FinancialTimeSeries,
    MonitoringRule,
    OperatingObservation,
    PeerComparableObservation,
    PriorRunReviewInput,
    SensitivityCase,
    VerificationCalendarEvent,
)
from research_os.domain.evidence import Evidence
from research_os.reporting.composer_v1_5_10 import ResearchReportComposer
from research_os.reporting.markdown_renderer_v1_5_10 import ResearchReportMarkdownRenderer
from research_os.reporting.research_view_v1_5_10 import ResearchViewPresenter
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


DECISION_TS = datetime(2026, 8, 31, tzinfo=timezone.utc)


def _context():
    values = {
        "business_description": "high temperature alloy manufacturing producer",
        "revenue": 200.0,
        "net_profit_parent": 10.0,
        "ocf": 15.0,
        "capex_cash": 4.0,
        "period_type": "H1",
        "period_days": 181,
    }
    evidence = []
    mapping = {}
    for key, value in values.items():
        eid = f"ev:base:{key}"
        evidence.append(Evidence(
            evidence_id=eid,
            company_id="synthetic:complete",
            evidence_type="filing_fact",
            period="2026H1",
            period_end="2026-06-30",
            publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
            ingested_at=DECISION_TS,
            value=value,
            unit="元",
            source_table=key,
            confidence_grade="A",
            verification_status="PRIMARY_VERIFIED",
        ))
        mapping[key] = [eid]
    return ResearchContext(
        run_id="run:complete",
        company=CompanyRef(company_id="synthetic:complete"),
        decision_ts=DECISION_TS,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="4" * 40,
            research_os_version="1.5.10",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(values=values, evidence_by_fact=mapping),
        options=ResearchOptions(),
    )


def _inputs():
    return ResearchInputs(
        operating_observations=(
            OperatingObservation(category="segment", metric_id="segment_growth", value=0.25, unit="ratio", period="2026H1", segment_label="new_alloy", evidence_ids=("ev:segment",)),
            OperatingObservation(category="subsidiary", metric_id="net_profit", value=-2.0, unit="CNY", period="2026H1", entity_label="subsidiary-a", evidence_ids=("ev:sub",)),
        ),
        financial_time_series=(
            FinancialTimeSeries(metric_id="revenue", unit="CNY", points=(
                FinancialSeriesPoint(period="2025Q4", period_end=datetime(2025, 12, 31, tzinfo=timezone.utc), value=90.0, evidence_ids=("ev:q4",)),
                FinancialSeriesPoint(period="2026Q1", period_end=datetime(2026, 3, 31, tzinfo=timezone.utc), value=100.0, evidence_ids=("ev:q1",)),
            )),
        ),
        cash_flow_quality_input=CashFlowQualityInput(net_profit=10.0, operating_cash_flow=15.0, working_capital_contribution=3.0, capex_cash=4.0, evidence_ids=("ev:cash",)),
        consensus_observations=(
            ConsensusObservation(source_id="broker-a", publish_ts=datetime(2026, 8, 20, tzinfo=timezone.utc), forecast_period="2027", metric="net_profit", value=20.0, evidence_ids=("ev:cons-a",)),
            ConsensusObservation(source_id="broker-b", publish_ts=datetime(2026, 8, 21, tzinfo=timezone.utc), forecast_period="2027", metric="net_profit", value=24.0, evidence_ids=("ev:cons-b",)),
        ),
        peer_comparables=(
            PeerComparableObservation(peer_id="peer-1", peer_role="direct_competitor", metric="segment_gross_margin", value=0.30, period="2026H1", period_type="H1", scope="segment", accounting_definition="reported_gross_margin", frequency="interim", share_count_convention="not_applicable", business_model_interpretation="manufacturing", product_or_segment="alloy", evidence_ids=("ev:peer",)),
        ),
        sensitivities=(
            SensitivityCase(case_id="raw-material-up", driver_id="raw_material_price", base_value=100.0, shock_label="+10%", shock_value=0.10, affected_metric="gross_margin", result=0.24, formula_version="analyst-sensitivity@1", assumption_ids=("assumption:raw",)),
        ),
        monitoring_rules=(
            MonitoringRule(rule_id="margin-watch", metric="segment_gross_margin", operator="lt", threshold=0.22, frequency="quarterly", rationale="explicit analyst watch", source_type="analyst_assumption", assumption_ids=("assumption:watch",)),
        ),
        verification_calendar=(
            VerificationCalendarEvent(event_id="q3", label="Q3 report", event_type="financial_report", due_ts=datetime(2026, 10, 31, tzinfo=timezone.utc), status="scheduled", information_value="validate cash and margin"),
        ),
        prior_run_review_items=(
            PriorRunReviewInput(item_id="growth", prior_statement="growth remains positive", metric="revenue_growth", period="2026H1", predicted_value=0.10, actual_value=0.13, tolerance=0.05, actual_evidence_ids=("ev:review",)),
        ),
    )


def test_completeness_artifacts_flow_one_way_into_document_and_markdown():
    result = ResearchRuntimeFactory.historical_v1_5_10().run_context(_context(), _inputs())
    before = result.model_dump(mode="json")
    view = ResearchViewPresenter().build(result)
    document = ResearchReportComposer().compose(view)
    markdown = ResearchReportMarkdownRenderer().render(document)
    body = markdown.split("## 审计附录", 1)[0]

    assert view.presentation_version == "professional-research-view@1.5.0"
    assert document.composition_version == "research-report-composer@1.3.0"
    assert ResearchReportMarkdownRenderer.version == "professional-markdown-renderer@1.2.0"

    section_ids = [section.section_id for section in document.sections]
    for section_id in (
        "financial-trends", "operating-evidence", "cash-flow-quality",
        "peer-comparison", "consensus-dispersion", "sensitivity-scenarios",
        "monitoring-calendar", "prior-run-review", "methodology-disclosure",
    ):
        assert section_id in section_ids

    for term in (
        "财务趋势", "经营证据", "现金流质量", "同行与产品线比较", "一致预期分布",
        "敏感性与情景", "监控规则与验证日历", "上期判断回顾", "方法说明",
        "simplified FCF", "不是 FCFF", "single_source",
    ):
        if term == "single_source":
            assert term not in body
        else:
            assert term in body

    assert "ev:segment" not in body
    assert "assumption:raw" not in body
    assert "assumption:watch" not in body
    assert result.model_dump(mode="json") == before


def test_empty_optional_completeness_inputs_only_add_methodology_section():
    result = ResearchRuntimeFactory.historical_v1_5_10().run_context(_context(), ResearchInputs())
    view = ResearchViewPresenter().build(result)
    document = ResearchReportComposer().compose(view)
    section_ids = [section.section_id for section in document.sections]

    assert "methodology-disclosure" in section_ids
    assert "operating-evidence" not in section_ids
    assert "financial-trends" not in section_ids
    assert "sensitivity-scenarios" not in section_ids
