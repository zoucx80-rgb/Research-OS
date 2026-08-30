from datetime import datetime, timezone

from research_os.reporting import (
    CausalBridgeBlock,
    HumanReadableDecisionSummary,
    HumanReadableDriverEdge,
    HumanReadableDriverGraph,
    HumanReadableDriverNode,
    HumanReadableResearchView,
    HumanReadableValuationExecution,
    ResearchReportComposer,
    SemanticValue,
)
from research_os.reporting.formatting import format_cny


def _semantic(code: str, label: str | None = None) -> SemanticValue:
    return SemanticValue(label=label or code, explanation=f"{code} explanation", code=code)


def _summary(risks=None):
    return HumanReadableDecisionSummary.model_construct(
        company_id="synthetic:composition",
        business_model=_semantic("distributor", "分销业务"),
        primary_thesis="增长能否穿越营运资金占用并转化为现金回报。",
        thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
        fundamental_state=_semantic("UNCERTAIN", "基本面方向尚不确定"),
        expectation_state=_semantic("MIXED", "市场预期信号混合"),
        valuation_state=_semantic("UNRELIABLE", "估值结果可靠性不足"),
        evidence_confidence=0.72,
        top_drivers=["收入", "净营运资金", "经营现金流"],
        top_risks=list(risks or []),
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


def _view(*, graph=None, valuation_execution=None, risks=None):
    return HumanReadableResearchView.model_construct(
        company_id="synthetic:composition",
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        repository="zoucx80-rgb/Research-OS",
        commit_sha="b" * 40,
        research_os_version="1.5.5",
        core_api_version="1.0",
        business_model=_semantic("distributor", "分销业务"),
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
        driver_graph=graph,
        theses=[],
        thesis_signal_assessment=None,
        expectation_quality=None,
        forecast_discipline=None,
        valuation_models=[],
        valuation_execution=valuation_execution,
        state_provenance=[],
        next_verification_event=None,
        expectation_gap=None,
        valuation_result=None,
        monitoring=None,
        presentation_limitations=[],
        decision_summary=_summary(risks=risks),
        presentation_version="professional-research-view@1.3.0",
    )


def _distributor_graph():
    nodes = [
        HumanReadableDriverNode(driver_id="revenue", label="收入", explanation="", critical=True, evidence_ids=["e-revenue"]),
        HumanReadableDriverNode(driver_id="ar", label="应收账款", explanation="", evidence_ids=["e-ar"]),
        HumanReadableDriverNode(driver_id="nwc", label="净营运资金", explanation="", critical=True, evidence_ids=["e-nwc"]),
        HumanReadableDriverNode(driver_id="debt", label="短期债务", explanation="", critical=True, evidence_ids=["e-debt"]),
        HumanReadableDriverNode(driver_id="interest", label="融资成本", explanation="", evidence_ids=["e-interest"]),
        HumanReadableDriverNode(driver_id="ocf", label="经营现金流", explanation="", critical=True, evidence_ids=["e-ocf"]),
    ]
    positive = _semantic("positive", "正向关系")
    negative = _semantic("negative", "反向关系")
    edges = [
        HumanReadableDriverEdge(from_driver="revenue", from_label="收入", to_driver="ar", to_label="应收账款", relation=positive),
        HumanReadableDriverEdge(from_driver="ar", from_label="应收账款", to_driver="nwc", to_label="净营运资金", relation=positive),
        HumanReadableDriverEdge(from_driver="nwc", from_label="净营运资金", to_driver="debt", to_label="短期债务", relation=positive),
        HumanReadableDriverEdge(from_driver="debt", from_label="短期债务", to_driver="interest", to_label="融资成本", relation=positive),
        HumanReadableDriverEdge(from_driver="nwc", from_label="净营运资金", to_driver="ocf", to_label="经营现金流", relation=negative),
    ]
    return HumanReadableDriverGraph(
        coverage=_semantic("professional", "专业驱动覆盖"),
        coverage_limited=False,
        nodes=nodes,
        edges=edges,
    )


def test_repeated_economic_risks_are_deduplicated_by_semantic_code():
    risks = [
        _semantic("NEGATIVE_OCF", "经营现金流为负"),
        _semantic("NEGATIVE_OCF", "经营现金流为负"),
        _semantic("DEBT_FUNDS_NWC", "新增债务主要支持营运资金"),
    ]
    snapshot = ResearchReportComposer().compose(_view(risks=risks)).decision_snapshot

    assert [item.code for item in snapshot.material_risks] == ["NEGATIVE_OCF", "DEBT_FUNDS_NWC"]


def test_distributor_bridge_preserves_existing_causal_order_into_valuation():
    execution = HumanReadableValuationExecution(
        selected_model="dcf",
        executed_model="dcf",
        selection_reason="现金经济性决定模型适用性",
        scenario_logic="三情景",
        assumptions=[],
        lineage={},
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
    doc = ResearchReportComposer().compose(
        _view(graph=_distributor_graph(), valuation_execution=execution)
    )
    bridges = [
        block
        for section in doc.sections
        for block in section.blocks
        if isinstance(block, CausalBridgeBlock)
    ]

    assert bridges
    steps = bridges[0].steps
    for earlier, later in zip(
        ["收入", "营运资金", "融资需求", "融资成本"],
        ["营运资金", "融资需求", "融资成本", "估值"],
    ):
        assert steps.index(earlier) < steps.index(later)


def test_graph_only_bridge_never_invents_an_unsupported_edge():
    graph = _distributor_graph().model_copy(
        update={"edges": _distributor_graph().edges[:1]}
    )
    doc = ResearchReportComposer().compose(_view(graph=graph))
    bridges = [
        block
        for section in doc.sections
        for block in section.blocks
        if isinstance(block, CausalBridgeBlock)
    ]

    assert bridges
    assert bridges[0].steps == ["收入", "应收账款"]
    assert "短期债务" not in bridges[0].steps


def test_large_cny_formatting_is_display_only():
    raw = 73_556_000_000

    formatted = format_cny(raw)

    assert formatted == "735.56亿元"
    assert raw == 73_556_000_000
