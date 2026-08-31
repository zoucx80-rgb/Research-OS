from __future__ import annotations

from datetime import datetime, timezone

from research_os.domain.evidence import Evidence
from research_os.reporting import (
    AuditAppendix,
    CapitalFundingBlock,
    InvestmentDecisionSnapshot,
    ReportSection,
    ResearchReportComposer,
    ResearchReportDocument,
    ResearchReportMarkdownRenderer,
    ResearchViewPresenter,
    SemanticValue,
    ValuationRationaleBlock,
)
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


DECISION_TS = datetime(2026, 8, 30, tzinfo=timezone.utc)


def _context() -> ResearchContext:
    values = {
        "business_description": "high temperature alloy manufacturing producer",
        "revenue": 2_053_495_665.67,
        "revenue_growth": 0.1304,
        "net_profit_parent": 102_870_971.88,
        "gross_profit": 439_265_030.63,
        "gross_margin": 0.2139108633,
        "margin_change": -0.0265554378,
        "ocf": 318_569_605.91,
        "capex_cash": 48_372_915.59,
        "ar_begin": 1_220_914_857.36,
        "ar_end": 1_956_870_704.88,
        "ar_growth": 0.6027904756,
        "inventory_begin": 1_830_061_290.26,
        "inventory_end": 1_617_781_116.58,
        "inventory_growth": -0.11599621,
        "assets_begin": 7_951_135_047.64,
        "assets_end": 7_891_044_594.20,
        "equity_begin": 3_787_194_180.95,
        "equity_end": 3_861_814_964.90,
        "period_type": "H1",
        "period_days": 181,
    }
    evidence = []
    evidence_by_fact = {}
    ratio_keys = {"revenue_growth", "gross_margin", "margin_change", "ar_growth", "inventory_growth"}
    for key, value in values.items():
        evidence_id = f"ev:output:{key}"
        evidence.append(
            Evidence(
                evidence_id=evidence_id,
                company_id="synthetic:output-depth",
                evidence_type="filing_fact",
                period="2026H1",
                period_end="2026-06-30",
                publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
                ingested_at=DECISION_TS,
                value=value,
                unit="ratio" if key in ratio_keys else "元",
                source_table=key,
                confidence_grade="A",
                verification_status="PRIMARY_VERIFIED",
            )
        )
        evidence_by_fact[key] = [evidence_id]
    return ResearchContext(
        run_id="run:output-depth",
        company=CompanyRef(company_id="synthetic:output-depth"),
        decision_ts=DECISION_TS,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="3" * 40,
            research_os_version="1.5.9",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(values=values, evidence_by_fact=evidence_by_fact),
        options=ResearchOptions(),
    )


def _semantic(code: str, label: str) -> SemanticValue:
    return SemanticValue(code=code, label=label, explanation=label)


def _minimal_document() -> ResearchReportDocument:
    return ResearchReportDocument(
        metadata={"company_id": "synthetic:format", "business_model": "分销业务"},
        decision_snapshot=InvestmentDecisionSnapshot(
            company_id="synthetic:format",
            decision_ts=DECISION_TS,
            business_model=_semantic("distributor", "分销业务"),
            decision_state=_semantic("WAIT", "等待进一步确认"),
            fundamental_state=_semantic("UNCERTAIN", "基本面方向尚不确定"),
            thesis_state=_semantic("ACTIVE", "投资逻辑仍然成立"),
            expectation_state=_semantic("MIXED", "市场预期信号混合"),
            valuation_state=_semantic("UNRELIABLE", "估值结果可靠性不足"),
            primary_thesis="现金经济性仍需验证。",
            evidence_confidence="1.00 / 1.00",
        ),
        sections=[
            ReportSection(
                section_id="capital-funding",
                title="资本效率与融资循环",
                blocks=[
                    CapitalFundingBlock(
                        funding_loop={
                            "operating_cash_flow": 318_569_605.91,
                            "incremental_debt": 16_392_000_000.0,
                            "factoring_balance": 1_230_000_000.0,
                            "factoring_to_ar": 0.0471,
                        }
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
                                "model_id": "pe",
                                "label": "PE",
                                "score": 0.084672,
                                "status": _semantic("LOW", "适用性较低").model_dump(mode="python"),
                                "explanation": "现金与资本结构约束较强。",
                            }
                        ]
                    )
                ],
            ),
        ],
        audit_appendix=AuditAppendix(
            repository="zoucx80-rgb/Research-OS",
            repository_commit="3" * 40,
            research_os_version="1.5.9",
            core_api_version="1.0",
            presentation_version="professional-research-view@1.4.0",
        ),
        composition_version="research-report-composer@1.2.0",
    )


def test_core_absolute_financial_facts_reach_document_and_professional_markdown():
    result = ResearchRuntimeFactory.default().run_context(_context(), ResearchInputs())
    before = result.model_dump(mode="json")
    view = ResearchViewPresenter().build(result)

    document = ResearchReportComposer().compose(view)
    financial = next(section for section in document.sections if section.section_id == "financial-operating-performance")
    block = financial.blocks[0]
    rows = {item["fact_key"]: item for item in block.core_financial_facts}

    assert ResearchReportComposer.version == "research-report-composer@1.2.0"
    assert rows["revenue"]["value"] == 2_053_495_665.67
    assert rows["net_profit_parent"]["value"] == 102_870_971.88
    assert rows["ocf"]["value"] == 318_569_605.91
    assert rows["ar_end"]["value"] == 1_956_870_704.88
    assert "debt_end" not in rows

    markdown = ResearchReportMarkdownRenderer().render(document)
    body = markdown.split("## 审计附录", 1)[0]
    assert ResearchReportMarkdownRenderer.version == "professional-markdown-renderer@1.1.0"
    assert "20.53亿元" in body
    assert "1.03亿元" in body
    assert "3.19亿元" in body
    assert "19.57亿元" in body
    assert "4837.29万元" in body
    assert "-2.66个百分点" in body
    assert "毛利率同比下降" in body
    assert "ev:output:" not in body
    assert result.model_dump(mode="json") == before


def test_body_formats_funding_currency_and_model_fitness_without_mutating_document():
    document = _minimal_document()
    before = document.model_dump(mode="json")

    text = ResearchReportMarkdownRenderer().render(document)
    body = text.split("## 审计附录", 1)[0]

    assert "**经营现金流**：3.19亿元" in body
    assert "**新增债务**：163.92亿元" in body
    assert "**保理余额**：12.30亿元" in body
    assert "0.084672" not in body
    assert "0.08" in body
    assert document.model_dump(mode="json") == before
