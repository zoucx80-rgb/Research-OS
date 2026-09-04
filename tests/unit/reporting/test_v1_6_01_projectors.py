from datetime import datetime, timezone

from research_os.contracts.artifact_values import (
    DecisionStateRecord,
    FundingLoop,
    MethodologyDisclosure,
)
from research_os.reporting.projectors import project_artifact
from research_os.router.models import BusinessModelProfile


def test_known_artifacts_project_to_investor_sections_without_machine_metadata() -> None:
    decision = project_artifact(
        "decision.record",
        DecisionStateRecord(
            domain_status="SUPPORTED",
            company_id="001287.SZ",
            state="RISK_REVIEW",
            decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
            reason_codes=("MATERIAL_FUNDING_RISK", "NEGATIVE_OCF"),
        ),
    )
    funding = project_artifact(
        "capital.funding_loop",
        FundingLoop(
            domain_status="SUPPORTED",
            funding_state="debt_funded",
            reason_codes=("NEGATIVE_OCF",),
        ),
    )
    methodology = project_artifact(
        "methodology.disclosure",
        MethodologyDisclosure(
            domain_status="INSUFFICIENT_EVIDENCE",
            plugin_keys=("hospitality.plugin@2",),
            limitations=("行业插件覆盖不足，酒店 KPI 不做推断。",),
        ),
    )

    assert decision.section_id == "decision"
    assert funding.section_id == "capital"
    assert methodology.section_id == "methodology"
    text = repr((decision.payload, funding.payload, methodology.payload))
    assert "MATERIAL_FUNDING_RISK" not in text
    assert "NEGATIVE_OCF" not in text
    assert "hospitality.plugin@2" not in text
    assert "融资循环存在重大风险" in text
    assert "融资循环存在重大风险；经营现金流为负" in text
    assert "['融资循环存在重大风险', '经营现金流为负']" not in text
    assert "酒店 KPI 不做推断" in text


def test_audit_only_artifacts_do_not_receive_investor_payloads() -> None:
    preflight = project_artifact(
        "validation.repository_preflight",
        {"repository_full_name": "zoucx80-rgb/Research-OS", "commit_sha": "a" * 64},
    )
    strategy = project_artifact("strategy.resolution", {"plugin_id": "secret-machine-name"})

    assert preflight.audit_only is True
    assert strategy.audit_only is True
    assert preflight.payload == {}
    assert strategy.payload == {}


def test_business_model_projection_keeps_business_meaning_not_router_internals() -> None:
    projection = project_artifact(
        "business_model.profile",
        BusinessModelProfile(
            company_id="301073.SZ",
            primary_model="hospitality",
            confidence_band="MEDIUM",
            usable_evidence_coverage=0.75,
            ambiguity=0.25,
            lease_heavy=True,
            router_version="router@1.1.0",
        ),
    )

    text = repr(projection.payload)
    assert projection.section_id == "scope"
    assert "酒店与住宿服务" in text
    assert "hospitality" not in text
    assert "75.00%" in text
    assert "router@1.1.0" not in text


def test_unknown_artifact_is_audit_only_instead_of_recursive_body_dump() -> None:
    projection = project_artifact(
        "future.unknown_artifact",
        {"source_url": "https://example.invalid", "secret_hash": "a" * 64, "nested": {"x": 1}},
    )

    assert projection.audit_only is True
    assert projection.payload == {}


def test_business_model_and_internal_states_are_humanized_for_investor_body() -> None:
    model = project_artifact(
        "business_model.profile",
        BusinessModelProfile(
            company_id="001287.SZ",
            primary_model="distributor",
            confidence_band="MEDIUM",
            usable_evidence_coverage=0.80,
            ambiguity=0.20,
            lease_heavy=False,
            router_version="router@1.1.0",
            classification_reason="SUPPORTED_BUSINESS_MODEL_SIGNAL",
        ),
    )
    decision = project_artifact(
        "decision.record",
        DecisionStateRecord(
            domain_status="SUPPORTED",
            company_id="300034.SZ",
            state="HOLD_AND_MONITOR",
            decision_ts=datetime(2026, 8, 30, tzinfo=timezone.utc),
            reason_codes=("NO_MATERIAL_STATE_CHANGE",),
        ),
    )

    text = repr((model.payload, decision.payload))
    assert "分销业务" in text
    assert "中等" in text
    assert "持续跟踪，暂不升级判断" in text
    assert "暂无足够证据支持状态升级" in text
    for machine_text in (
        "distributor",
        "MEDIUM",
        "SUPPORTED_BUSINESS_MODEL_SIGNAL",
        "HOLD_AND_MONITOR",
        "NO_MATERIAL_STATE_CHANGE",
    ):
        assert machine_text not in text


def test_kpi_projection_keeps_only_valid_metrics_and_summarizes_missing_coverage() -> None:
    projection = project_artifact(
        "kpi.metrics",
        {
            "metrics": [
                {"metric_id": "ccc_days", "value": 48.2, "unit": "days", "status": "valid"},
                {
                    "metric_id": "simple_fcf",
                    "value": 270_196_690.32,
                    "unit": None,
                    "status": "valid",
                },
                {
                    "metric_id": "factoring_to_ar",
                    "value": None,
                    "unit": "ratio",
                    "status": "missing",
                },
                {
                    "metric_id": "interest_to_gross_profit",
                    "value": None,
                    "unit": "ratio",
                    "status": "missing",
                },
            ]
        },
    )

    text = repr(projection.payload)
    assert "现金转换周期" in text
    assert "48.20天" in text
    assert "简化自由现金流" in text
    assert "2.70亿元" in text
    assert "未覆盖指标数量" in text
    assert "'未覆盖指标数量': 2" in text
    assert "保理余额/应收账款" not in text
    assert "利息支出/毛利" not in text
    assert "'数值': '—'" not in text


def test_decision_and_readiness_dimensions_are_humanized() -> None:
    provenance = project_artifact(
        "decision.state_provenance",
        {
            "domain_status": "SUPPORTED",
            "inputs": [
                {"dimension": "thesis_portfolio", "state": "active"},
                {"dimension": "funding_loop", "state": "debt_funded"},
                {"dimension": "semantic_signals", "state": "UNKNOWN"},
            ],
        },
    )
    readiness = project_artifact(
        "research.readiness",
        {
            "domain_status": "SUPPORTED",
            "final_status": "NOT_READY",
            "blocking_dimensions": ["prior_run_validation"],
            "dimensions": [
                {"dimension_id": "time_series", "status": "PASS"},
                {"dimension_id": "prior_run_validation", "status": "INCOMPLETE"},
            ],
        },
    )

    text = repr((provenance.payload, readiness.payload))
    assert "投资逻辑" in text
    assert "融资循环" in text
    assert "语义证据" in text
    assert "当前有效" in text
    assert "债务融资驱动" in text
    assert "财务时序" in text
    assert "上期判断验证" in text
    for machine_text in (
        "thesis portfolio",
        "funding loop",
        "semantic signals",
        "prior run validation",
    ):
        assert machine_text not in text


def test_valuation_model_ids_are_presented_as_finance_labels() -> None:
    routing = project_artifact(
        "valuation.routing",
        {
            "domain_status": "SUPPORTED",
            "primary_model_keys": ["dcf"],
            "secondary_model_keys": ["pe", "ev_ebitda"],
        },
    )
    text = repr(routing.payload)
    assert "DCF" in text
    assert "PE" in text
    assert "EV/EBITDA" in text
    assert "'dcf'" not in text
    assert "'ev_ebitda'" not in text


def test_driver_monitoring_and_methodology_projection_remove_machine_vocabulary() -> None:
    drivers = project_artifact(
        "drivers.graph",
        {
            "nodes": [
                {
                    "name": "operating_cash_flow",
                    "driver_type": "research_driver",
                    "observable_metric": "operating_cash_flow",
                    "critical": True,
                }
            ],
            "edges": [],
        },
    )
    monitoring = project_artifact(
        "monitoring.plan",
        {
            "items": [
                {
                    "metric_id": "gross_margin",
                    "condition": "gte 0.23",
                    "next_check_ts": "2026-10-31T00:00:00Z",
                }
            ]
        },
    )
    methodology = project_artifact(
        "methodology.disclosure",
        {
            "limitations": [
                "industry_strategy: hospitality: NO_COMPATIBLE_INDUSTRY_PLUGIN: "
                "no compatible industry strategy plugin for primary business model"
            ]
        },
    )

    text = repr((drivers.payload, monitoring.payload, methodology.payload))
    assert "经营现金流" in text
    assert "研究驱动" in text
    assert "大于等于 23.00%" in text
    assert "2026-10-31" in text
    assert "行业专属 KPI 不做推断" in text
    for machine_text in (
        "operating_cash_flow",
        "research_driver",
        "gte 0.23",
        "NO_COMPATIBLE_INDUSTRY_PLUGIN",
        "hospitality",
    ):
        assert machine_text not in text


def test_monitoring_asset_ratios_use_percent_display() -> None:
    projected = project_artifact(
        "monitoring.plan",
        {
            "domain_status": "SUPPORTED",
            "items": [
                {
                    "metric_id": "lease_liabilities_to_assets",
                    "condition": "lt 0.50",
                    "next_check_ts": "2026-10-31T00:00:00Z",
                }
            ],
        },
    )

    assert projected.payload["监控项"][0]["触发条件"] == "小于 50.00%"
