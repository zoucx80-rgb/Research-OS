from datetime import datetime, timezone

from research_os.reporting import (
    HumanReadableCoverageGap,
    HumanReadableDecisionSummary,
    HumanReadableExpectationQuality,
    HumanReadableFundingLoop,
    HumanReadableMetric,
    HumanReadableResearchView,
    HumanReadableStateProvenance,
    HumanReadableThesis,
    HumanReadableThesisSignalAssessment,
    HumanReadableValuationExecution,
    HumanReadableValuationModel,
    ResearchReportComposer,
    SemanticValue,
)
from research_os.reporting.research_view import (
    HumanReadableCapitalEfficiency,
    HumanReadableFinancialSanity,
    HumanReadableForecastDiscipline,
)


def _semantic(code: str, label: str | None = None) -> SemanticValue:
    return SemanticValue(label=label or code, explanation=f"{code} explanation", code=code)


def _summary(business_model: str = "manufacturing") -> HumanReadableDecisionSummary:
    return HumanReadableDecisionSummary.model_construct(
        company_id=f"synthetic:{business_model}",
        business_model=_semantic(business_model, business_model),
        primary_thesis="增长质量取决于经营改善能否转化为可持续现金回报。",
        thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
        fundamental_state=_semantic("IMPROVING", "基本面改善"),
        expectation_state=_semantic("MIXED", "市场预期信号混合"),
        valuation_state=_semantic("USABLE", "估值可用"),
        evidence_confidence=0.81,
        top_drivers=["收入", "营运资金", "经营现金流"],
        top_risks=[_semantic("WORKING_CAPITAL_PRESSURE", "营运资金占用上升")],
        next_verification_event="下一次重大信息披露",
        research_os_version="1.5.5",
        decision_state=_semantic("WAIT_FOR_CONFIRMATION", "等待进一步确认"),
        final_status=_semantic("COMPLETE", "研究流程完整"),
        blocking_modules=[],
        module_statuses={},
        expectation_evidence_status=_semantic("PASS", "通过"),
        valuation_execution_status=_semantic("PASS", "通过"),
        core_contradiction=None,
        sections=[],
        presentation_version="semantic-report@1.0.0",
    )


def _base_view(**updates) -> HumanReadableResearchView:
    data = dict(
        company_id="synthetic:manufacturing",
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        repository="zoucx80-rgb/Research-OS",
        commit_sha="c" * 40,
        research_os_version="1.5.5",
        core_api_version="1.0",
        business_model=_semantic("manufacturing", "制造业务"),
        classification_status=_semantic("classified", "业务模型已识别"),
        classification_reason=None,
        secondary_business_models=[],
        industry_plugins=[],
        methodology_plugins=[],
        coverage_gaps=[],
        report_contributions=[],
        question_assessments=[],
        financial_sanity=None,
        kpi_metrics=[],
        capital_efficiency=None,
        funding_loop=None,
        driver_graph=None,
        theses=[],
        thesis_signal_assessment=None,
        expectation_quality=None,
        forecast_discipline=None,
        valuation_models=[],
        valuation_execution=None,
        state_provenance=[],
        next_verification_event=None,
        expectation_gap=None,
        valuation_result=None,
        monitoring=None,
        presentation_limitations=[],
        decision_summary=_summary(),
        presentation_version="professional-research-view@1.3.0",
    )
    data.update(updates)
    return HumanReadableResearchView.model_construct(**data)


def _metric(metric_id: str, label: str, value: float, evidence_id: str) -> HumanReadableMetric:
    return HumanReadableMetric.model_construct(
        metric_id=metric_id,
        label=label,
        explanation=f"{label}的规范化指标。",
        value=value,
        formatted_value=str(value),
        display_unit="%",
        period_label="2026H1",
        period_days=181,
        annualized=False,
        status=_semantic("valid", "指标有效"),
        reason=None,
        formula_version="test@1",
        evidence_ids=[evidence_id],
    )


def test_material_canonical_artifacts_are_composed_into_body_sections():
    thesis = HumanReadableThesis.model_construct(
        title="增长质量",
        statement="增长需要转化为现金回报。",
        mechanism="收入增长 -> 营运资金 -> 经营现金流。",
        anti_thesis="营运资金占用持续快于收入增长。",
        status=_semantic("ACTIVE", "投资逻辑仍然成立"),
        falsifiers=[],
        confidence=0.76,
        next_check_date="2026-10-31",
    )
    view = _base_view(
        financial_sanity=HumanReadableFinancialSanity(
            status=_semantic("PASS", "财务一致性通过"),
            explanation="核心财务口径通过一致性校验。",
        ),
        kpi_metrics=[_metric("net_margin", "归母净利率", 5.2, "ev:kpi-secret")],
        capital_efficiency=HumanReadableCapitalEfficiency.model_construct(
            calculation_status=_semantic("PASS", "资本效率可计算"),
            roic=0.11,
            incremental_roic=0.14,
            iwcr=0.09,
            iwcr_limitation=None,
        ),
        funding_loop=HumanReadableFundingLoop.model_construct(
            calculation_status=_semantic("PASS", "融资循环可判断"),
            state=_semantic("mixed", "混合融资"),
            reasons=[],
            incremental_revenue=100.0,
            incremental_nwc=30.0,
            incremental_debt=12.0,
            incremental_equity=None,
            reported_equity_change=2.0,
            operating_cash_flow=20.0,
            factoring_balance=None,
            derecognized_receivables=None,
            receivable_transfer_balance=None,
            other_working_capital_financing=None,
            factoring_to_ar=None,
            comparison_basis_status=_semantic("PASS", "比较期间基准一致"),
            comparison_basis_limitations=[],
        ),
        theses=[thesis],
        thesis_signal_assessment=HumanReadableThesisSignalAssessment.model_construct(
            state=_semantic("MIXED", "正负信号并存"),
            positive_signals=["利润率改善"],
            negative_signals=["营运资金占用上升"],
            evidence_ids=["ev:thesis-secret"],
        ),
        expectation_quality=HumanReadableExpectationQuality.model_construct(
            state=_semantic("MEDIUM", "市场预期质量中等"),
            reasons=[],
            source_count=3,
            source_quality=0.72,
            age_days=12,
            latest_material_event_ts=None,
            latest_material_event_label=None,
            post_event_consensus=True,
        ),
        forecast_discipline=HumanReadableForecastDiscipline(
            status=_semantic("PASS", "预测纪律通过"),
            reason="关键预测假设具有证据或基准支持。",
        ),
        valuation_models=[
            HumanReadableValuationModel.model_construct(
                model_id="dcf",
                label="DCF",
                explanation="现金流估值。",
                score=0.8,
                status=_semantic("FIT", "适用"),
                reasons=[],
            )
        ],
        valuation_execution=HumanReadableValuationExecution.model_construct(
            selected_model="dcf",
            executed_model="dcf",
            selection_reason="现金经济性是核心价值驱动。",
            scenario_logic="熊/基准/牛三情景。",
            assumptions=[{"id": "assumption-secret", "name": "margin", "value": 0.1}],
            lineage={"margin": ["ev:valuation-secret"]},
            driver_bridge=["Revenue", "Working Capital", "Net Profit / Cash Economics", "Valuation"],
        ),
        state_provenance=[
            HumanReadableStateProvenance.model_construct(
                dimension="fundamental_state",
                state=_semantic("IMPROVING", "基本面改善"),
                source=_semantic("canonical", "规范化研究状态"),
                evidence_ids=["ev:state-secret"],
                method="canonical_state_projection",
            )
        ],
    )

    doc = ResearchReportComposer().compose(view)
    section_ids = [section.section_id for section in doc.sections]

    for expected in (
        "financial-operating-performance",
        "capital-funding",
        "thesis-debate",
        "expectation-forecast",
        "valuation-rationale",
        "state-provenance",
    ):
        assert expected in section_ids


def test_composition_preserves_values_and_keeps_raw_ids_out_of_main_body():
    view = _base_view(
        kpi_metrics=[_metric("net_margin", "归母净利率", 5.2, "ev:kpi-secret")],
        capital_efficiency=HumanReadableCapitalEfficiency.model_construct(
            calculation_status=_semantic("PASS", "资本效率可计算"),
            roic=0.11,
            incremental_roic=None,
            iwcr=None,
            iwcr_limitation=None,
        ),
        funding_loop=HumanReadableFundingLoop.model_construct(
            calculation_status=_semantic("PASS", "融资循环可判断"),
            state=_semantic("debt_funded", "债务融资驱动"),
            reasons=[],
            incremental_revenue=100.0,
            incremental_nwc=50.0,
            incremental_debt=45.0,
            incremental_equity=None,
            reported_equity_change=None,
            operating_cash_flow=-20.0,
            factoring_balance=None,
            derecognized_receivables=None,
            receivable_transfer_balance=None,
            other_working_capital_financing=None,
            factoring_to_ar=None,
            comparison_basis_status=_semantic("PASS", "比较期间基准一致"),
            comparison_basis_limitations=[],
        ),
        thesis_signal_assessment=HumanReadableThesisSignalAssessment.model_construct(
            state=_semantic("NEGATIVE", "负面信号占优"),
            positive_signals=[],
            negative_signals=["现金流承压"],
            evidence_ids=["ev:thesis-secret"],
        ),
        state_provenance=[
            HumanReadableStateProvenance.model_construct(
                dimension="fundamental_state",
                state=_semantic("UNCERTAIN", "基本面方向尚不确定"),
                source=_semantic("canonical", "规范化研究状态"),
                evidence_ids=["ev:state-secret"],
                method="canonical_state_projection",
            )
        ],
    )
    before = view.model_dump(mode="json")

    doc = ResearchReportComposer().compose(view)
    main_body = str([section.model_dump(mode="json") for section in doc.sections])

    assert "debt_funded" in main_body
    assert "-20.0" in main_body
    assert "0.11" in main_body
    assert "ev:kpi-secret" not in main_body
    assert "ev:thesis-secret" not in main_body
    assert "ev:state-secret" not in main_body
    assert view.model_dump(mode="json") == before


def test_coverage_limited_hospitality_does_not_fabricate_operating_kpis():
    gap = HumanReadableCoverageGap.model_construct(
        gap_type=_semantic("industry_strategy", "缺少专业行业策略覆盖"),
        business_model=_semantic("hospitality", "酒店业务"),
        reason=_semantic("NO_COMPATIBLE_INDUSTRY_PLUGIN", "当前版本缺少兼容的行业策略插件"),
        affected_capabilities=["RevPAR", "ADR", "OCC", "same_store"],
        fallback_available=True,
        missing_capability="industry_strategy",
    )
    view = _base_view(
        company_id="synthetic:hospitality",
        business_model=_semantic("hospitality", "酒店业务"),
        coverage_gaps=[gap],
        kpi_metrics=[],
        capital_efficiency=None,
        funding_loop=None,
        theses=[],
        presentation_limitations=[
            "使用权资产或租赁负债具有重要性；当前报告未计算租赁调整后的资本回报或估值。"
        ],
        decision_summary=_summary("hospitality"),
    )

    doc = ResearchReportComposer().compose(view)
    section_ids = [section.section_id for section in doc.sections]
    main_body = str([section.model_dump(mode="json") for section in doc.sections])

    assert "financial-operating-performance" not in section_ids
    assert "capital-funding" not in section_ids
    assert "research-gaps" in section_ids
    assert "material-limitations" in section_ids
    assert "RevPAR" not in main_body
    assert "ADR" not in main_body
    assert "OCC" not in main_body
