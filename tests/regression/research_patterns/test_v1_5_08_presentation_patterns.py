from __future__ import annotations

from research_os.presentation import HtmlPresentationArtifact, PdfPresentationArtifact
from research_os.reporting import (
    AuditAppendix,
    CapitalFundingBlock,
    CausalBridgeBlock,
    FinancialOperatingBlock,
    GapClassificationBlock,
    InvestmentDecisionSnapshot,
    LimitationBlock,
    NarrativeBlock,
    ReportSection,
    ResearchReportDocument,
    SemanticValue,
    ValuationBlock,
)


class _DeterministicPdfAdapter:
    def render(self, html: HtmlPresentationArtifact) -> PdfPresentationArtifact:
        return PdfPresentationArtifact.from_html(
            html=html,
            renderer_version="professional-pdf-adapter@1.0.0",
            backend_version="test-backend@1.0",
            content=b"%PDF-1.7\ncross-model-regression",
        )


def _semantic(code: str, label: str) -> SemanticValue:
    return SemanticValue(code=code, label=label, explanation=label)


def _document(
    *,
    model_code: str,
    model_label: str,
    sections: list[ReportSection],
    plugin_id: str,
) -> ResearchReportDocument:
    return ResearchReportDocument(
        metadata={"company_id": f"synthetic:{model_code}"},
        decision_snapshot=InvestmentDecisionSnapshot(
            company_id=f"synthetic:{model_code}",
            decision_ts="2026-08-30T00:00:00Z",
            business_model=_semantic(model_code, model_label),
            decision_state=_semantic("WAIT_FOR_CONFIRMATION", "等待进一步确认"),
            fundamental_state=_semantic("MIXED", "基本面信号混合"),
            thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
            expectation_state=_semantic("MISSING", "市场预期缺失"),
            valuation_state=_semantic("MISSING", "估值缺失"),
            primary_thesis="证据同时包含支持项与约束项。",
            material_drivers=["增长", "现金", "资本效率"],
            evidence_confidence=0.62,
            top_limitation="部分专业能力或数据仍然缺失。",
        ),
        sections=sections,
        audit_appendix=AuditAppendix(
            repository="zoucx80-rgb/Research-OS",
            repository_commit="synthetic-sha",
            research_os_version="1.5.8",
            core_api_version="1.0",
            presentation_version="professional-research-view@1.3.0",
            industry_plugins=[{"plugin_id": plugin_id}],
            evidence_ids=[f"ev:{model_code}:secret"],
        ),
    )


def _render(document: ResearchReportDocument):
    from research_os.presentation import ProfessionalPresentationPipeline

    return ProfessionalPresentationPipeline(
        pdf_adapter=_DeterministicPdfAdapter()
    ).render(document)


def _body(html: str) -> str:
    return html.split('<section id="audit-appendix"', maxsplit=1)[0]


def test_manufacturing_presentation_keeps_growth_cash_capex_tension_without_invention():
    document = _document(
        model_code="manufacturing",
        model_label="制造业",
        plugin_id="synthetic-manufacturing@1.0.0",
        sections=[
            ReportSection(
                section_id="financial-operating-performance",
                title="财务与经营表现",
                blocks=[
                    FinancialOperatingBlock(
                        kpi_metrics=[
                            {"label": "收入增长", "formatted_value": "18%", "period_label": "2026H1"},
                            {"label": "毛利率", "formatted_value": "31%", "period_label": "2026H1"},
                            {"label": "应收账款", "formatted_value": "45亿元", "period_label": "2026H1"},
                            {"label": "经营现金流", "formatted_value": "-2亿元", "period_label": "2026H1"},
                            {"label": "资本开支", "formatted_value": "8亿元", "period_label": "2026H1"},
                        ]
                    )
                ],
            ),
            ReportSection(
                section_id="capital-funding",
                title="资本效率与融资循环",
                blocks=[
                    CapitalFundingBlock(
                        capital_efficiency={"roic": "8.2%", "iwcr_limitation": "现金回报承压"}
                    )
                ],
            ),
        ],
    )

    body = _body(_render(document).html.content)

    for supplied in ("收入增长", "毛利率", "应收账款", "经营现金流", "资本开支", "现金回报承压"):
        assert supplied in body
    for invented in ("订单饱满", "产能利用率改善", "良率提升", "资格认证完成"):
        assert invented not in body


def test_distributor_presentation_preserves_debt_and_factoring_as_distinct_links():
    causal_chain = (
        "Revenue → AR/Inventory → NWC → negative OCF → Debt/Factoring "
        "→ financing cost → valuation"
    )
    document = _document(
        model_code="distributor",
        model_label="分销业务",
        plugin_id="synthetic-distributor@1.0.0",
        sections=[
            ReportSection(
                section_id="capital-funding",
                title="资本效率与融资循环",
                blocks=[
                    CapitalFundingBlock(
                        funding_loop={
                            "state": {"label": "债务融资驱动"},
                            "operating_cash_flow": "-3亿元",
                            "incremental_debt": "12亿元",
                            "factoring_balance": "4亿元",
                        }
                    )
                ],
            ),
            ReportSection(
                section_id="causal-bridge",
                title="关键因果链",
                blocks=[CausalBridgeBlock(steps=causal_chain.split(" → "))],
            ),
            ReportSection(
                section_id="valuation",
                title="估值与情景",
                blocks=[ValuationBlock(payload={"limitations": ["融资成本侵蚀估值"]})],
            ),
        ],
    )

    body = _body(_render(document).html.content)

    assert causal_chain in body
    assert "新增债务" in body and "保理余额" in body
    assert "Debt/Factoring" in body
    assert "融资成本侵蚀估值" in body


def test_lease_heavy_hospitality_presentation_keeps_capability_gap_and_no_fake_kpis():
    document = _document(
        model_code="hospitality",
        model_label="酒店运营（租赁较重）",
        plugin_id="synthetic-generic-fallback@1.0.0",
        sections=[
            ReportSection(
                section_id="core-investment-judgment",
                title="核心投资判断",
                blocks=[
                    NarrativeBlock(
                        text="自有PPE较低，但使用权资产与租赁负债重大，不能据此认定轻资产。"
                    )
                ],
            ),
            ReportSection(
                section_id="research-gaps",
                title="研究缺口分类",
                blocks=[
                    GapClassificationBlock(
                        capability_missing=["Hospitality KPI Pack与专业策略能力缺失"]
                    )
                ],
            ),
            ReportSection(
                section_id="material-limitations",
                title="关键研究限制",
                blocks=[LimitationBlock(items=["当前不具备租赁调整后的资本回报与估值能力"])],
            ),
        ],
    )

    rendered = _render(document)
    body = _body(rendered.html.content)

    assert "使用权资产与租赁负债重大" in body
    assert "Hospitality KPI Pack与专业策略能力缺失" in body
    assert "当前不具备租赁调整后的资本回报与估值能力" in body
    for invented in ("RevPAR", "ADR", "OCC", "同店增长", "lease-adjusted ROIC", "lease-adjusted valuation"):
        assert invented not in body
    assert rendered.pdf.source_hash == rendered.html.content_hash
