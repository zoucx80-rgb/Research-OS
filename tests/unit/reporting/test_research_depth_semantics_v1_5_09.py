from __future__ import annotations

from datetime import datetime, timezone

from research_os.domain.evidence import Evidence
from research_os.reporting import ResearchViewPresenter
from research_os.reporting.semantics import DecisionSummaryPresenter
from research_os.reporting.summary import DecisionSummary
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


def _manufacturing_context() -> ResearchContext:
    values = {
        "business_description": "high temperature alloy manufacturing producer",
        "revenue": 2_053_495_665.67,
        "revenue_growth": 0.1304,
        "net_profit_parent": 102_870_971.88,
        "gross_profit": 439_265_030.63,
        "gross_margin": 0.2139,
        "margin_change": -0.0266,
        "ocf": 318_569_605.91,
        "capex_cash": 48_372_915.59,
        "ar_begin": 1_220_914_857.36,
        "ar_end": 1_956_870_704.88,
        "ar_growth": 0.6028,
        "inventory_begin": 1_830_061_290.26,
        "inventory_end": 1_617_781_116.58,
        "inventory_growth": -0.1160,
        "assets_begin": 7_951_135_047.64,
        "assets_end": 7_891_044_594.20,
        "equity_begin": 3_787_194_180.95,
        "equity_end": 3_861_814_964.90,
        "period_type": "H1",
        "period_days": 181,
    }
    evidence = []
    evidence_by_fact = {}
    for key, value in values.items():
        evidence_id = f"ev:{key}"
        evidence.append(
            Evidence(
                evidence_id=evidence_id,
                company_id="synthetic:depth-semantics",
                evidence_type="filing_fact",
                period="2026H1",
                period_end="2026-06-30",
                publish_ts=datetime(2026, 8, 25, tzinfo=timezone.utc),
                ingested_at=DECISION_TS,
                value=value,
                unit=("ratio" if key in {"revenue_growth", "gross_margin", "margin_change", "ar_growth", "inventory_growth"} else "元"),
                source_table=key,
                confidence_grade="A",
                verification_status="PRIMARY_VERIFIED",
            )
        )
        evidence_by_fact[key] = [evidence_id]
    return ResearchContext(
        run_id="run:depth-semantics",
        company=CompanyRef(company_id="synthetic:depth-semantics"),
        decision_ts=DECISION_TS,
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="2" * 40,
            research_os_version="1.5.9",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(values=values, evidence_by_fact=evidence_by_fact),
        options=ResearchOptions(),
    )


def test_view_projects_core_financial_facts_with_unambiguous_margin_direction():
    result = ResearchRuntimeFactory.default().run_context(
        _manufacturing_context(),
        ResearchInputs(),
    )
    before = result.model_dump(mode="json")

    view = ResearchViewPresenter().build(result)

    assert view.presentation_version == "professional-research-view@1.4.0"
    rows = {item.fact_key: item for item in view.core_financial_facts}
    assert rows["revenue"].label == "营业收入"
    assert rows["revenue"].value == 2_053_495_665.67
    assert rows["revenue"].period == "2026H1"
    assert rows["margin_change"].interpretation == "毛利率同比下降"
    assert "改善" not in rows["margin_change"].interpretation
    assert rows["margin_change"].evidence_ids == ["ev:margin_change"]
    assert result.model_dump(mode="json") == before


def test_chinese_view_localizes_builtin_professional_questions_by_semantic_id():
    result = ResearchRuntimeFactory.default().run_context(
        _manufacturing_context(),
        ResearchInputs(),
    )

    view = ResearchViewPresenter().build(result)

    assert view.question_assessments
    assert all("?" not in item.question for item in view.question_assessments)
    assert all(not item.question.startswith(("What ", "How ", "Is ", "Are ", "Which ")) for item in view.question_assessments)
    assert any("订单" in item.question for item in view.question_assessments)


def test_decision_summary_confidence_has_scale_and_unknown_machine_code_is_not_material_risk():
    summary = DecisionSummary(
        company_id="synthetic:depth-semantics",
        business_model="manufacturing",
        primary_thesis="经营信号存在分化。",
        thesis_state="ACTIVE",
        fundamental_state="UNCERTAIN",
        expectation_state="MIXED",
        valuation_state="UNRELIABLE",
        evidence_confidence=1.0,
        top_drivers=["收入"],
        top_risks=["NEGATIVE_OCF", "UNMAPPED_INTERNAL_CODE"],
        next_verification_event="下一次定期报告",
        research_os_version="1.5.9",
    )

    presented = DecisionSummaryPresenter().present(summary)

    assert presented.evidence_confidence == "1.00 / 1.00"
    assert [item.code for item in presented.top_risks] == ["NEGATIVE_OCF"]
    assert all("尚未配置中文说明" not in item.label for item in presented.top_risks)
