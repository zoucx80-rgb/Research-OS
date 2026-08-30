import importlib

import pytest

from research_os.reporting import (
    AuditAppendix,
    CapitalFundingBlock,
    CausalBridgeBlock,
    EvidenceNoteBlock,
    ExpectationForecastBlock,
    FinancialOperatingBlock,
    GapClassificationBlock,
    InvestmentDecisionSnapshot,
    LimitationBlock,
    MonitoringBlock,
    NarrativeBlock,
    ReportSection,
    ResearchReportDocument,
    SemanticValue,
    StateProvenanceBlock,
    ThesisDebateBlock,
    ValuationRationaleBlock,
)


def _semantic(code: str, label: str, explanation: str = "") -> SemanticValue:
    return SemanticValue(code=code, label=label, explanation=explanation or label)


def _renderer_cls():
    reporting = importlib.import_module("research_os.reporting")
    assert hasattr(reporting, "ResearchReportMarkdownRenderer"), (
        "v1.5.07 requires a public ResearchReportMarkdownRenderer"
    )
    return reporting.ResearchReportMarkdownRenderer


def _document(*, business_model_label: str = "分销业务") -> ResearchReportDocument:
    snapshot = InvestmentDecisionSnapshot(
        company_id="synthetic:renderer",
        decision_ts="2026-08-30T00:00:00Z",
        business_model=_semantic("distributor", business_model_label),
        decision_state=_semantic("WAIT_FOR_CONFIRMATION", "等待进一步确认"),
        fundamental_state=_semantic("UNCERTAIN", "基本面方向尚不确定"),
        thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
        expectation_state=_semantic("MIXED", "市场预期信号混合"),
        valuation_state=_semantic("USABLE", "估值可用"),
        primary_thesis="增长质量取决于营运资金占用能否转化为现金回报。",
        material_drivers=["收入", "营运资金", "经营现金流"],
        material_risks=[
            _semantic("NEGATIVE_OCF", "经营现金流为负", "现金质量承压。"),
            _semantic("DEBT_FUNDS_NWC", "新增债务支持营运资金", "外部融资依赖上升。"),
        ],
        evidence_confidence=0.81,
        next_verification_event="下一次重大信息披露",
        material_limitation_count=1,
        top_limitation="市场一致预期来源仍偏薄。",
    )
    sections = [
        ReportSection(
            section_id="core-investment-judgment",
            title="核心投资判断",
            blocks=[NarrativeBlock(title="核心投资逻辑", text="收入增长很快，但现金经济性仍需验证。")],
        ),
        ReportSection(
            section_id="financial-operating-performance",
            title="财务与经营表现",
            blocks=[
                FinancialOperatingBlock(
                    financial_sanity={
                        "status": {"code": "PASS", "label": "财务一致性通过", "explanation": "核心口径一致。"},
                        "explanation": "核心财务口径通过一致性校验。",
                    },
                    kpi_metrics=[
                        {
                            "metric_id": "cash_conversion",
                            "label": "利润现金转化率",
                            "explanation": "观察利润的现金质量。",
                            "value": -1.5,
                            "formatted_value": "-1.50x",
                            "display_unit": "x",
                            "period_label": "2026H1",
                            "period_days": 181,
                            "annualized": False,
                            "status": {"code": "valid", "label": "指标有效", "explanation": "可计算。"},
                            "reason": None,
                            "formula_version": "cash@1",
                        }
                    ],
                )
            ],
        ),
        ReportSection(
            section_id="capital-funding",
            title="资本效率与融资循环",
            blocks=[
                CapitalFundingBlock(
                    capital_efficiency={
                        "calculation_status": {"code": "PASS", "label": "资本效率可计算", "explanation": "口径可用。"},
                        "roic": 0.11,
                        "incremental_roic": None,
                    },
                    funding_loop={
                        "calculation_status": {"code": "PASS", "label": "融资循环可判断", "explanation": "输入充分。"},
                        "state": {"code": "debt_funded", "label": "债务融资驱动", "explanation": "新增债务主要支持营运资金。"},
                        "operating_cash_flow": -175.0,
                        "incremental_debt": 164.0,
                        "factoring_balance": 12.0,
                        "comparison_basis_status": {"code": "PASS", "label": "比较期间基准一致", "explanation": "可比。"},
                    },
                )
            ],
        ),
        ReportSection(
            section_id="causal-bridge",
            title="关键因果链",
            blocks=[CausalBridgeBlock(steps=["收入", "营运资金", "融资需求", "融资成本", "估值"])],
        ),
        ReportSection(
            section_id="thesis-debate",
            title="投资逻辑与反证",
            blocks=[
                ThesisDebateBlock(
                    theses=[
                        {
                            "title": "增长质量",
                            "statement": "增长能够转化为可持续现金回报。",
                            "mechanism": "收入增长 → 营运资金 → 经营现金流。",
                            "anti_thesis": "营运资金占用持续快于收入增长。",
                            "status": {"code": "ACTIVE", "label": "投资逻辑仍然成立", "explanation": "尚未被证伪。"},
                            "falsifiers": [
                                {
                                    "metric": "ocf",
                                    "metric_label": "经营现金流",
                                    "operator": "<",
                                    "threshold": 0.0,
                                    "explanation": "经营现金流持续为负将削弱增长质量论点。",
                                }
                            ],
                            "confidence": 0.72,
                            "next_check_date": "2026-10-31",
                        }
                    ],
                    signal_assessment={
                        "state": {"code": "MIXED", "label": "正负信号并存", "explanation": "需要继续验证。"},
                        "positive_signals": ["收入增长"],
                        "negative_signals": ["经营现金流为负"],
                    },
                )
            ],
        ),
        ReportSection(
            section_id="expectation-forecast",
            title="市场预期与预测纪律",
            blocks=[
                ExpectationForecastBlock(
                    expectation_quality={
                        "state": {"code": "MEDIUM", "label": "市场预期质量中等", "explanation": "来源数量有限。"},
                        "source_count": 3,
                        "source_quality": 0.72,
                        "age_days": 12,
                        "post_event_consensus": True,
                    },
                    forecast_discipline={
                        "status": {"code": "PASS", "label": "预测纪律通过", "explanation": "假设有支持。"},
                        "reason": "关键假设具有证据或基准支持。",
                    },
                )
            ],
        ),
        ReportSection(
            section_id="valuation-rationale",
            title="估值方法与适用性",
            blocks=[
                ValuationRationaleBlock(
                    valuation_models=[
                        {
                            "model_id": "dcf",
                            "label": "DCF",
                            "explanation": "现金经济性是核心价值驱动。",
                            "score": 0.82,
                            "status": {"code": "FIT", "label": "适用", "explanation": "适用性较高。"},
                            "reasons": [],
                        }
                    ],
                    valuation_execution={
                        "selected_model": "dcf",
                        "executed_model": "dcf",
                        "selection_reason": "现金经济性是核心价值驱动。",
                        "scenario_logic": "熊/基准/牛三情景。",
                        "assumptions": [{"name": "margin", "value": 0.1}],
                        "driver_bridge": ["收入", "营运资金", "估值"],
                    },
                )
            ],
        ),
        ReportSection(
            section_id="monitoring",
            title="监控与验证",
            blocks=[
                MonitoringBlock(
                    next_verification_event="下一次重大信息披露",
                    conviction_up_conditions=["经营现金流明显改善"],
                    thesis_broken_conditions=["经营现金流持续显著为负"],
                    key_metrics=["经营现金流", "应收账款周转天数"],
                )
            ],
        ),
        ReportSection(
            section_id="state-provenance",
            title="状态来源",
            blocks=[
                StateProvenanceBlock(
                    items=[
                        {
                            "dimension": "fundamental_state",
                            "state": {"code": "UNCERTAIN", "label": "基本面方向尚不确定", "explanation": "信号混合。"},
                            "source": {"code": "canonical", "label": "规范化研究状态", "explanation": "来自 canonical state。"},
                            "method": "canonical_state_projection",
                        }
                    ]
                )
            ],
        ),
        ReportSection(
            section_id="research-gaps",
            title="研究缺口分类",
            blocks=[
                GapClassificationBlock(
                    evidence_missing=["同店经营证据"],
                    capability_missing=["专业行业策略插件"],
                    not_applicable=["当前不存在该类增量比较"],
                    presentation_or_deferred=["租赁调整后资本回报尚未实现"],
                )
            ],
        ),
        ReportSection(
            section_id="material-limitations",
            title="关键研究限制",
            blocks=[LimitationBlock(items=["市场一致预期来源仍偏薄。"])],
        ),
        ReportSection(
            section_id="evidence-traceability",
            title="证据追溯",
            blocks=[
                EvidenceNoteBlock(
                    text="关键结论保留规范化证据追溯；完整证据索引见审计附录。",
                    evidence_ids=["ev:body-secret"],
                )
            ],
        ),
    ]
    appendix = AuditAppendix(
        repository="zoucx80-rgb/Research-OS",
        repository_commit="a" * 40,
        research_os_version="1.5.7",
        core_api_version="1.0",
        presentation_version="professional-research-view@1.3.0",
        industry_plugins=[{"plugin_id": "industry:distributor", "plugin_version": "1.2.0"}],
        methodology_plugins=[],
        module_statuses={"core:funding": {"code": "PASS", "label": "通过"}},
        evidence_ids=["ev:body-secret", "ev:audit-only"],
        assumption_ids=["assumption:secret"],
    )
    return ResearchReportDocument(
        metadata={
            "company_id": "synthetic:renderer",
            "decision_ts": "2026-08-30T00:00:00Z",
            "business_model": business_model_label,
        },
        decision_snapshot=snapshot,
        sections=sections,
        audit_appendix=appendix,
        composition_version="research-report-composer@1.1.0",
    )


def test_renderer_public_api_exists():
    renderer_cls = _renderer_cls()
    assert renderer_cls.version == "professional-markdown-renderer@1.0.0"


def test_renderer_outputs_professional_body_without_machine_dump():
    renderer = _renderer_cls()()
    text = renderer.render(_document())
    body, appendix = text.split("## 审计附录", 1)

    assert text.startswith("# 投资研究报告")
    assert "## 投资决策快照" in body
    assert "债务融资驱动" in body
    assert "经营现金流为负" in body
    assert "指标 | 数值 | 期间 | 状态 | 说明" in body
    assert "增长质量" in body
    assert "反方逻辑" in body
    assert "证伪条件" in body
    assert "### 证据缺口" in body
    assert "### 能力缺口" in body
    assert "### 不适用" in body
    assert "### 展示/延期项" in body

    for forbidden in (
        "block_type",
        "metric_id",
        "formula_version",
        "SemanticValue(",
        "{'",
        "None",
        "ev:body-secret",
        "assumption:secret",
    ):
        assert forbidden not in body

    assert "ev:body-secret" in appendix
    assert "assumption:secret" in appendix


def test_renderer_is_deterministic_and_type_bound():
    renderer = _renderer_cls()()
    document = _document()

    first = renderer.render(document)
    second = renderer.render(document)

    assert first == second
    assert first.endswith("\n")
    assert not first.endswith("\n\n")
    with pytest.raises(TypeError):
        renderer.render(document.model_dump(mode="python"))


def test_renderer_preserves_distributor_cash_and_financing_tension_without_relabeling_factoring():
    text = _renderer_cls()().render(_document())
    body = text.split("## 审计附录", 1)[0]

    assert "经营现金流" in body
    assert "-175" in body
    assert "债务融资驱动" in body
    assert "保理余额" in body
    assert "12" in body
    assert "保理余额（债务）" not in body


def test_renderer_does_not_invent_hospitality_kpis_when_document_has_only_gap_and_lease_limitation():
    document = _document(business_model_label="酒店业务").model_copy(
        update={
            "sections": [
                ReportSection(
                    section_id="research-gaps",
                    title="研究缺口分类",
                    blocks=[
                        GapClassificationBlock(
                            capability_missing=["专业酒店行业策略能力"],
                            presentation_or_deferred=["租赁调整后资本回报尚未实现"],
                        )
                    ],
                ),
                ReportSection(
                    section_id="material-limitations",
                    title="关键研究限制",
                    blocks=[LimitationBlock(items=["租赁项目具有重要性；资产结构需在租赁口径下复核。"])],
                ),
            ]
        }
    )

    body = _renderer_cls()().render(document).split("## 审计附录", 1)[0]

    assert "酒店业务" in body
    assert "专业酒店行业策略能力" in body
    assert "租赁项目具有重要性" in body
    for invented in ("RevPAR", "ADR", "OCC", "同店", "轻资产"):
        assert invented not in body
