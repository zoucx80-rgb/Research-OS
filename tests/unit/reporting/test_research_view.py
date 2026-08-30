from datetime import datetime, timezone

from research_os.domain.enums import ConfidenceGrade, EvidenceType, VerificationStatus
from research_os.domain.evidence import Evidence
from research_os.expectations.models import ConsensusVintage
from research_os.reporting import ResearchViewPresenter
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
from research_os.valuation.fitness import ModelFitnessInputs


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
        run_id=f"run:{company_id}:v1.5.02-view",
        company=CompanyRef(company_id=company_id),
        decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
        baseline=BaselineFingerprint(
            repository_full_name="zoucx80-rgb/Research-OS",
            repository_id=1350382205,
            branch="main",
            commit_sha="2" * 40,
            research_os_version="1.5.1",
            core_api_version="1.0",
        ),
        evidence=LegacyEvidenceView(evidence),
        facts=LegacyFactView(
            values=values,
            evidence_by_fact={
                key: [f"ev:{company_id}:{key}"]
                for key in values
            },
        ),
        options=ResearchOptions(),
    )


def _fitness():
    return ModelFitnessInputs(
        data_quality=0.9,
        earnings_stability=0.8,
        cash_flow_visibility=0.7,
        capital_structure_fit=0.9,
        business_model_fit=0.9,
        forecast_stability=0.8,
    )


def test_distributor_research_view_humanizes_end_to_end_machine_artifacts():
    company_id = "synthetic:distributor-view"
    values = {
        "business_description": "authorized electronics component distribution",
        "revenue": 1000.0,
        "cogs": 970.0,
        "avg_ar": 200.0,
        "avg_inventory": 300.0,
        "avg_ap": 100.0,
        "ar": 250.0,
        "inventory": 350.0,
        "ap": 120.0,
        "delta_nwc": 100.0,
        "delta_revenue": 300.0,
        "short_debt": 300.0,
        "equity": 150.0,
        "gross_profit": 30.0,
        "interest_expense": 10.0,
        "ocf": -50.0,
        "cfo": -50.0,
        "net_profit": 15.0,
        "delta_debt": 90.0,
        "delta_equity": 0.0,
        "period_type": "H1",
        "period_days": 181,
    }
    context = _context(company_id, values)
    inputs = ResearchInputs(
        expectation_vintage=ConsensusVintage(
            company_id=company_id,
            as_of=datetime(2026, 4, 30, tzinfo=timezone.utc),
            forecast_period="2026",
            net_profit=40.0,
            source_count=2,
            source_quality=0.4,
        ),
        valuation_models={"pe": _fitness()},
        fundamental_state="STABLE",
        valuation_state="FAIR",
        expectation_state="IN_LINE",
    )
    result = ResearchRuntimeFactory.default().run_context(context, inputs)

    view = ResearchViewPresenter().build(result)

    assert view.presentation_version == "semantic-research-view@1.0.0"
    assert view.business_model.label == "分销业务"
    assert view.classification_status.label == "业务模型已识别"
    assert view.industry_plugins[0].label == "分销业务策略插件"
    assert view.coverage_gaps == []
    assert view.report_contributions
    assert all(item.title for item in view.report_contributions)

    dso = next(item for item in view.kpi_metrics if item.metric_id == "dso_days")
    assert dso.label == "应收账款周转天数"
    assert dso.status.label == "指标有效"

    assert view.funding_loop is not None
    assert view.funding_loop.state.label == "债务融资驱动"
    assert {item.label for item in view.funding_loop.reasons} >= {
        "新增债务主要支持营运资金",
        "经营现金流为负",
    }

    assert any(item.label == "收入" for item in view.driver_graph.nodes)
    assert view.theses
    assert view.theses[0].statement.startswith("收入增长应")
    assert view.expectation_quality is not None
    assert view.expectation_quality.state.label == "市场预期证据质量偏低"
    assert {item.label for item in view.expectation_quality.reasons} >= {
        "覆盖机构数量较少",
        "预期数据距离决策时点较久",
    }
    assert view.valuation_models[0].label == "市盈率（PE）"
    assert view.valuation_models[0].status.label == "主要估值方法"
    assert view.decision_summary.decision_state is not None
    assert view.decision_summary.decision_state.label == "进入风险复核"
    assert view.decision_summary.final_status.label != view.decision_summary.final_status.code


def test_hospitality_research_view_exposes_coverage_limit_without_fake_thesis():
    company_id = "synthetic:hospitality-view"
    values = {
        "business_description": "hotel hospitality lodging management and operations",
        "revenue": 100.0,
        "ocf": 20.0,
        "cfo": 20.0,
        "period_type": "H1",
        "period_days": 181,
    }
    result = ResearchRuntimeFactory.default().run_context(
        _context(company_id, values),
        ResearchInputs(),
    )

    view = ResearchViewPresenter().build(result)

    assert view.business_model.label == "酒店与住宿服务"
    assert view.industry_plugins == []
    assert view.coverage_gaps
    gap = view.coverage_gaps[0]
    assert gap.gap_type.label == "缺少专业行业策略覆盖"
    assert gap.business_model is not None
    assert gap.business_model.label == "酒店与住宿服务"
    assert gap.reason.label == "当前版本缺少兼容的行业策略插件"
    assert view.driver_graph is not None
    assert view.driver_graph.coverage_limited is True
    assert view.driver_graph.coverage.label == "通用驱动，仅供信息参考"
    assert view.theses == []
    assert view.decision_summary.module_statuses["核心驱动关系"].label == "证据不足"
    assert view.decision_summary.final_status.label == "研究流程未完成"
