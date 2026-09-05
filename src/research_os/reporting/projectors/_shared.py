from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, cast

from pydantic import BaseModel, JsonValue

from ..formatting import HumanValueFormatter


@dataclass(frozen=True, slots=True)
class ArtifactProjection:
    section_id: str
    title: str
    payload: JsonValue
    audit_only: bool = False


_FORMATTER = HumanValueFormatter()

_STATUS_LABELS = {
    "READY": "研究就绪",
    "NOT_READY": "研究未就绪",
    "COMPLETE": "执行完成",
    "INCOMPLETE": "执行未完成",
    "PASS": "通过",
    "FAIL": "未通过",
    "SUPPORTED": "证据支持",
    "SUFFICIENT": "充分",
    "LIMITED": "有限",
    "PARTIAL": "部分",
    "MISSING": "缺失",
    "NOT_APPLICABLE": "不适用",
    "EXECUTABLE": "可执行",
    "BLOCKED": "受阻",
    "INSUFFICIENT_EVIDENCE": "证据不足",
    "INSUFFICIENT": "证据不足",
    "RISK_REVIEW": "风险审查",
    "WAIT_FOR_CONFIRMATION": "等待确认",
    "MATERIAL_FUNDING_RISK": "融资循环存在重大风险",
    "DEBT_FUNDS_NWC": "新增营运资本主要依赖债务融资",
    "COMPARISON_BASIS_MISMATCH": "比较口径存在不一致，相关结论需谨慎解释",
    "DETERIORATING": "恶化",
    "IMPROVING": "改善",
    "STABLE": "稳定",
    "RISING": "上升",
    "FALLING": "下降",
    "CONFIRMED": "已确认",
    "POSSIBLE": "可能",
    "NOT_OBSERVED": "未观察到",
    "UNCERTAIN": "不确定",
    "UNKNOWN": "未知",
    "COMPARABLE": "可比",
    "ADJUSTMENT_REQUIRED": "需调整后比较",
    "NOT_COMPARABLE": "不可比",
    "INTERSECTION": "估值区间交集",
    "CROSS_CHECK_BAND": "交叉验证区间",
    "MODEL_DISAGREEMENT": "模型分歧",
    "ADEQUATE": "充分",
    "LOW": "偏低",
    "CLASSIFIED": "已分类",
    "UNRESOLVED": "未解析",
    "valid": "有效",
    "missing": "缺失",
    "invalid": "无效",
    "not_applicable": "不适用",
    "POSITIVE": "正向",
    "NEGATIVE": "负向",
    "NEUTRAL": "中性",
    "MIXED": "混合",
    "BELOW_MARKET": "低于市场预期",
    "ABOVE_MARKET": "高于市场预期",
    "IN_LINE": "符合市场预期",
    "HOLD_AND_MONITOR": "持续跟踪，暂不升级判断",
    "NO_MATERIAL_STATE_CHANGE": "暂无足够证据支持状态升级",
    "LOW_EVIDENCE_CONFIDENCE": "证据置信度不足",
    "INSUFFICIENT_COMPARABLE_POINTS": "可比数据点不足",
    "COMPARISON_BASIS_REQUIRED": "缺少明确比较口径",
    "LINEAGE_MISSING": "缺少绑定版本的证据沿袭",
    "TEMPORAL_OBSERVATIONS_MISSING": "缺少财务报告期观察",
    "ACTIVE": "当前有效",
    "DEBT_FUNDED": "债务融资驱动",
    "SELF_FUNDED": "内部现金流支持",
    "STRESSED": "融资压力较高",
    "MEDIUM": "中等",
    "HIGH": "较高",
    "scheduled": "已计划",
    "pending_date": "日期待定",
    "completed": "已完成",
    "periodic_report": "定期报告",
}

_REASON_LABELS = {
    "NEGATIVE_OCF": "经营现金流为负",
    "MATERIAL_FACTORING_EXPOSURE": "保理/应收融资暴露较高",
    "MATERIAL_FUNDING_RISK": "融资循环存在重大风险",
    "DEBT_FUNDS_NWC": "新增营运资本主要依赖债务融资",
    "COMPARISON_BASIS_MISMATCH": "比较口径存在不一致，相关结论需谨慎解释",
    "NO_VALID_METRICS": "缺少有效指标",
    "NO_CONSENSUS_VINTAGE": "缺少可用的一致预期快照",
    "STALE_CONSENSUS": "一致预期数据过旧",
    "LOW_SOURCE_COUNT": "一致预期来源数量不足",
    "NO_MATERIAL_STATE_CHANGE": "暂无足够证据支持状态升级",
    "LOW_EVIDENCE_CONFIDENCE": "证据置信度不足",
    "INSUFFICIENT_COMPARABLE_POINTS": "可比数据点不足",
    "COMPARISON_BASIS_REQUIRED": "缺少明确比较口径",
    "LINEAGE_MISSING": "缺少绑定版本的证据沿袭",
    "TEMPORAL_OBSERVATIONS_MISSING": "缺少财务报告期观察",
    "SUPPORTED_BUSINESS_MODEL_SIGNAL": "业务模式证据支持当前分类",
    "Debt Funds Nwc": "新增营运资本主要依赖债务融资",
    "Comparison Basis Mismatch": "比较口径存在不一致，相关结论需谨慎解释",
}

_METRIC_LABELS = {
    "revenue": "营业收入",
    "net_profit": "净利润",
    "net_profit_parent": "归母净利润",
    "gross_margin": "毛利率",
    "roe": "ROE",
    "roic": "ROIC",
    "incremental_roic": "增量 ROIC",
    "iwcr": "增量营运资本回报",
    "operating_cash_flow": "经营现金流",
    "simplified_fcf": "简化自由现金流",
    "simple_fcf": "简化自由现金流",
    "cash_conversion": "现金转化率",
    "cash_conversion_parent": "归母现金转化率",
    "ccc_days": "现金转换周期",
    "factoring_to_ar": "保理余额/应收账款",
    "funding_loop_debt_share": "融资循环债务占比",
    "funding_loop_external_share": "融资循环外部融资占比",
    "gross_profit_to_working_capital": "毛利/营运资本",
    "interest_to_gross_profit": "利息支出/毛利",
    "inventory_turns": "存货周转次数",
    "nwc_intensity": "营运资本强度",
    "ar_days": "应收账款周转天数",
    "asset_turnover": "总资产周转率",
    "capex_intensity": "资本开支强度",
    "equity_multiplier": "权益乘数",
    "fixed_asset_turnover": "固定资产周转率",
    "inventory_days": "存货周转天数",
    "net_margin": "净利率",
    "revenue_growth": "营业收入同比增速",
    "margin_change": "毛利率变化",
    "ar_growth": "应收账款同比增速",
    "inventory_growth": "存货同比增速",
    "delta_nwc": "营运资本增量",
    "delta_revenue": "营业收入增量",
    "delta_debt": "有息债务增量",
    "financing_cost": "融资成本",
    "fixed_asset_to_assets": "固定资产/总资产",
    "right_of_use_assets_to_assets": "使用权资产/总资产",
    "lease_liabilities_to_assets": "租赁负债/总资产",
    "inventory_turns_period": "期间存货周转次数",
    "short_debt_to_equity": "短期债务/权益",
    "short_debt_to_inventory": "短期债务/存货",
    "total_financing_cost_to_gross_profit": "总融资成本/毛利",
    "working_capital_financing_to_gross_profit": "营运资金融资暴露/毛利",
    "raw_material_price": "原材料价格",
    "cycle_recovery": "周期复苏",
    "economic_moat": "经济护城河",
}

_METRIC_UNITS = {
    "simple_fcf": "CNY",
    "simplified_fcf": "CNY",
    "cash_conversion": "x",
    "cash_conversion_parent": "x",
    "ccc_days": "days",
    "factoring_to_ar": "ratio",
    "funding_loop_debt_share": "ratio",
    "funding_loop_external_share": "ratio",
    "gross_profit_to_working_capital": "x",
    "interest_to_gross_profit": "ratio",
    "inventory_turns": "x",
    "nwc_intensity": "ratio",
    "ar_days": "days",
    "asset_turnover": "x",
    "capex_intensity": "ratio",
    "equity_multiplier": "x",
    "fixed_asset_turnover": "x",
    "inventory_days": "days",
    "net_margin": "ratio",
    "gross_margin": "ratio",
    "revenue_growth": "ratio",
    "ar_growth": "ratio",
    "inventory_growth": "ratio",
    "fixed_asset_to_assets": "ratio",
    "right_of_use_assets_to_assets": "ratio",
    "lease_liabilities_to_assets": "ratio",
    "short_debt_to_equity": "ratio",
    "short_debt_to_inventory": "ratio",
    "total_financing_cost_to_gross_profit": "ratio",
    "working_capital_financing_to_gross_profit": "ratio",
    "net_profit_parent": "CNY",
    "net_profit": "CNY",
    "operating_cash_flow": "CNY",
    "delta_nwc": "CNY",
    "delta_revenue": "CNY",
    "delta_debt": "CNY",
    "financing_cost": "CNY",
    "roe": "ratio",
    "roic": "ratio",
    "incremental_roic": "ratio",
    "iwcr": "ratio",
}

_BUSINESS_MODEL_LABELS = {
    "manufacturing": "制造业",
    "distributor": "分销业务",
    "hospitality": "酒店与住宿服务",
    "unknown": "未明确分类",
}

_DIMENSION_LABELS = {
    "thesis_portfolio": "投资逻辑",
    "funding_loop": "融资循环",
    "valuation": "估值",
    "expectation": "市场预期",
    "semantic_signals": "语义证据",
    "time_series": "财务时序",
    "financial_temporal": "财务跨期分析",
    "operating_evidence": "经营证据",
    "cash_flow": "现金流",
    "consensus": "一致预期",
    "peers": "同行可比",
    "sensitivity": "敏感性分析",
    "monitoring_events": "监控事件",
    "prior_run_validation": "上期判断验证",
    "methodology": "方法与覆盖",
    "execution_completion": "执行完成度",
}

_MODEL_LABELS = {
    "dcf": "DCF",
    "pe": "PE",
    "pb": "PB",
    "ev_ebitda": "EV/EBITDA",
}

_SEMANTIC_LABELS = {
    "RECOVERY_OBSERVED_TROUGH_UNCONFIRMED": "已观察到复苏迹象，但周期底部尚未确认",
    "BARRIER_EVIDENCE_PRESENT_ECONOMIC_MOAT_UNCONFIRMED": "存在壁垒证据，但尚不能确认已形成经济护城河",
}

_SECTION_TITLES = {
    "decision": "投资决策快照",
    "scope": "业务模式与研究范围",
    "financial": "财务与经营表现",
    "capital": "资本效率与融资循环",
    "thesis": "驱动、投资逻辑与反证",
    "expectation": "市场预期与预测纪律",
    "valuation": "同行、估值与情景",
    "monitoring": "监控与验证",
    "readiness": "研究就绪度与缺口",
    "methodology": "方法与限制",
    "other": "其他研究信息",
}

_ARTIFACT_META: dict[str, tuple[str, str]] = {
    "decision.record": ("decision", "研究决策"),
    "decision.state_provenance": ("decision", "决策状态来源"),
    "business_model.profile": ("scope", "业务模式识别"),
    "kpi.metrics": ("financial", "关键经营指标"),
    "financial.time_series": ("financial", "财务趋势"),
    "financial.temporal_analysis": ("financial", "财务跨期趋势"),
    "research.operating_evidence": ("financial", "经营证据"),
    "cash_flow.quality_bridge": ("financial", "现金流质量"),
    "capital.efficiency": ("capital", "资本效率"),
    "capital.funding_loop": ("capital", "融资循环"),
    "drivers.graph": ("thesis", "关键驱动链"),
    "thesis.portfolio": ("thesis", "核心投资逻辑与反证"),
    "thesis.semantic_signal_assessment": ("thesis", "主张强度与语义边界"),
    "semantic.claims": ("thesis", "研究主张"),
    "expectation.snapshot": ("expectation", "一致预期快照"),
    "expectation.quality": ("expectation", "预期数据质量"),
    "expectation.gap": ("expectation", "市场预期差"),
    "expectation.consensus_distribution": ("expectation", "一致预期分布"),
    "forecast.evaluation": ("expectation", "预测验证纪律"),
    "peers.normalized": ("valuation", "同行可比性"),
    "valuation.routing": ("valuation", "估值方法与适用性"),
    "valuation.execution": ("valuation", "估值模型结果"),
    "valuation.result": ("valuation", "主要估值结果"),
    "valuation.reconciliation": ("valuation", "估值区间与交叉验证"),
    "scenario.sensitivities": ("valuation", "敏感性与情景"),
    "monitoring.plan": ("monitoring", "监控规则与下一验证事件"),
    "monitoring.prior_run_review": ("monitoring", "上期判断回顾"),
    "research.readiness": ("readiness", "研究就绪度"),
    "research.sufficiency": ("readiness", "研究充分性"),
    "methodology.disclosure": ("methodology", "方法与研究限制"),
}

_AUDIT_PREFIXES = ("validation.", "evidence.")

_AUDIT_IDS = {
    "strategy.resolution",
    "financial.fact_snapshot",
    "semantic.preservation",
}


def section_title(section_id: str) -> str:
    return _SECTION_TITLES.get(section_id, _SECTION_TITLES["other"])


def _python(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return {name: _python(getattr(value, name)) for name in type(value).model_fields}
    if isinstance(value, Enum):
        return _python(value.value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reporting requires timezone-aware datetimes")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return value
    if isinstance(value, tuple):
        return [_python(item) for item in value]
    if isinstance(value, list):
        return [_python(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _python(item) for key, item in value.items()}
    return value


def _status(value: Any) -> str:
    text = str(value)
    return _STATUS_LABELS.get(
        text, _STATUS_LABELS.get(text.upper(), text.replace("_", " ").title())
    )


def status_label(value: Any) -> str:
    """Human-readable label for report-level execution/readiness states."""
    return _status(value)


def _date_text(value: Any) -> Any:
    if value is None:
        return None
    text = str(value)
    return text[:10] if len(text) >= 10 and text[4:5] == "-" and text[7:8] == "-" else text


def _reason(value: Any) -> str:
    text = str(value)
    return _REASON_LABELS.get(
        text, _REASON_LABELS.get(text.upper(), text.replace("_", " ").title())
    )


def _dimension(value: Any) -> str:
    text = str(value or "")
    return _DIMENSION_LABELS.get(text, text.replace("_", " "))


def _business_model_label(value: Any) -> str:
    text = str(value or "unknown")
    return _BUSINESS_MODEL_LABELS.get(text, text.replace("_", " "))


def _model(value: Any) -> str:
    text = str(value or "")
    return _MODEL_LABELS.get(text, text.upper().replace("_", "/"))


def _metric(value: Any) -> str:
    if value is None or value == "":
        return "—"
    text = str(value)
    return _METRIC_LABELS.get(text, text.replace("_", " "))


def _number(value: Any, *, unit: str | None = None, field_name: str | None = None) -> str:
    return _FORMATTER.format(value, unit=unit, field_name=field_name)


def _json(value: Any) -> JsonValue:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return cast(JsonValue, {str(key): _json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return cast(JsonValue, [_json(item) for item in value])
    return str(value)
