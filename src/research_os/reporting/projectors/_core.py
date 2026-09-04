from __future__ import annotations

from typing import Any

from pydantic import JsonValue

from ._shared import (
    _METRIC_UNITS,
    _SEMANTIC_LABELS,
    _business_model_label,
    _date_text,
    _dimension,
    _json,
    _metric,
    _number,
    _reason,
    _status,
)


def _decision(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "状态": _status(data.get("state", "INSUFFICIENT_EVIDENCE")),
            "决策时点": _date_text(data.get("decision_ts")),
            "核心原因": "；".join(_reason(item) for item in data.get("reason_codes", [])),
            "纳入决策的投资逻辑数量": len(data.get("thesis_keys", [])),
        }
    )


def _decision_provenance(data: dict[str, Any]) -> JsonValue:
    rows = []
    for item in data.get("inputs", []):
        rows.append(
            {
                "维度": _dimension(item.get("dimension")),
                "状态": _status(item.get("state", "UNKNOWN")),
            }
        )
    return _json({"状态来源": rows})


def _business_model(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "主要业务模式": _business_model_label(data.get("primary_model")),
            "辅助业务模式": [
                _business_model_label(item) for item in data.get("secondary_models", [])
            ],
            "分类状态": _status(data.get("classification_status", "UNKNOWN")),
            "置信区间": _status(data.get("confidence_band", "UNKNOWN")),
            "可用证据覆盖": _number(
                data.get("usable_evidence_coverage"), field_name="usable_evidence_coverage"
            ),
            "租赁特征显著": "是" if data.get("lease_heavy") else "否",
        }
    )


def _metrics(data: dict[str, Any]) -> JsonValue:
    rows = []
    omitted = 0
    for item in data.get("metrics", []):
        metric_id = str(item.get("metric_id") or "")
        if item.get("status") != "valid" or item.get("value") is None:
            omitted += 1
            continue
        unit = item.get("unit") or _METRIC_UNITS.get(metric_id)
        rows.append(
            {
                "指标": _metric(metric_id),
                "数值": _number(item.get("value"), unit=unit, field_name=metric_id),
            }
        )
    payload: dict[str, Any] = {"有效指标": rows}
    if omitted:
        payload["未覆盖指标数量"] = omitted
    return _json(payload)


def _financial_series(data: dict[str, Any]) -> JsonValue:
    rows = []
    for series in data.get("series", []):
        for point in series.get("points", []):
            rows.append(
                {
                    "指标": _metric(series.get("metric_id")),
                    "期间": point.get("period"),
                    "数值": _number(
                        point.get("value"),
                        unit=series.get("unit"),
                        field_name=series.get("metric_id"),
                    ),
                }
            )
    return _json({"趋势": rows})


def _operating(data: dict[str, Any]) -> JsonValue:
    rows = []
    for item in data.get("observations", []):
        rows.append(
            {
                "类别": {
                    "reported_or_derived": "已报告/派生",
                    "reported": "已报告",
                    "derived": "派生",
                }.get(str(item.get("category")), str(item.get("category") or "—")),
                "指标": _metric(item.get("metric_id")),
                "期间": item.get("period") or item.get("as_of"),
                "数值": _number(
                    item.get("value"), unit=item.get("unit"), field_name=item.get("metric_id")
                ),
                "分部": item.get("segment_label"),
            }
        )
    return _json({"经营观察": rows})


def _cash_flow(data: dict[str, Any]) -> JsonValue:
    unit = data.get("unit")
    return _json(
        {
            "净利润": _number(data.get("net_profit"), unit=unit),
            "经营现金流": _number(data.get("operating_cash_flow"), unit=unit),
            "营运资本影响": _number(data.get("working_capital_contribution"), unit=unit),
            "资本开支": _number(data.get("capex_cash"), unit=unit),
            "简化自由现金流": _number(data.get("simplified_fcf"), unit=unit),
        }
    )


def _capital(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "ROIC": _number(data.get("roic"), unit="ratio"),
            "增量 ROIC": _number(data.get("incremental_roic"), unit="ratio"),
            "增量营运资本回报": _number(data.get("iwcr"), unit="ratio"),
        }
    )


def _funding(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "融资状态": _status(data.get("funding_state", "UNKNOWN")),
            "关键风险": [_reason(item) for item in data.get("reason_codes", [])],
        }
    )


def _thesis(data: dict[str, Any]) -> JsonValue:
    primary = data.get("primary")
    payload: dict[str, Any] = {}
    if primary:
        payload["核心逻辑"] = {
            "标题": primary.get("title"),
            "判断": primary.get("statement"),
            "机制": primary.get("mechanism"),
            "反方观点": primary.get("anti_thesis"),
            "证伪条件": primary.get("falsifier_statements", []),
            "下一检查日": primary.get("next_check_date"),
            "置信度": _number(primary.get("confidence"), field_name="confidence"),
            "主张强度": {
                "STRONG": "强",
                "MODERATE": "中等",
                "WEAK": "弱",
                "OBSERVED": "观察性主张",
            }.get(
                str(primary.get("claim_strength", "UNKNOWN")).upper(),
                _status(primary.get("claim_strength", "UNKNOWN")),
            ),
        }
    for key, label in (
        ("supporting", "支持逻辑"),
        ("conflicting", "冲突逻辑"),
        ("unresolved", "待验证逻辑"),
    ):
        if data.get(key):
            payload[label] = [item.get("title") or item.get("statement") for item in data[key]]
    return _json(payload)


def _semantic_signals(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "总体状态": _status(data.get("assessment_status", "INSUFFICIENT")),
            "信号": [
                {
                    "指标": _metric(item.get("metric_id")),
                    "方向": _status(item.get("direction", "UNKNOWN")),
                    "语义边界": _SEMANTIC_LABELS.get(
                        str(item.get("semantic_label", "")),
                        str(item.get("semantic_label", "")).replace("_", " "),
                    ),
                }
                for item in data.get("signals", [])
            ],
        }
    )


def _claims(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "主张": [
                {
                    "类型": {
                        "FACT": "事实",
                        "CALCULATION": "计算",
                        "STATISTICAL EVIDENCE": "统计证据",
                        "STATISTICAL_EVIDENCE": "统计证据",
                        "ASSUMPTION": "假设",
                        "CONCLUSION": "研究结论",
                    }.get(
                        str(item.get("claim_type", "UNKNOWN")).upper(),
                        _status(item.get("claim_type", "UNKNOWN")),
                    ),
                    "内容": item.get("statement"),
                }
                for item in data.get("claims", [])
            ]
        }
    )


def _driver_graph(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "关键驱动": [
                {
                    "名称": _metric(item.get("name")),
                    "类型": {
                        "research_driver": "研究驱动",
                        "operating_driver": "经营驱动",
                        "financial_driver": "财务驱动",
                    }.get(
                        str(item.get("driver_type")), _status(item.get("driver_type", "UNKNOWN"))
                    ),
                    "观察指标": _metric(item.get("observable_metric"))
                    if item.get("observable_metric")
                    else None,
                    "关键驱动": "是" if item.get("critical") else "否",
                }
                for item in data.get("nodes", [])
            ],
            "因果关系": [
                {
                    "从": item.get("from_driver"),
                    "到": item.get("to_driver"),
                    "关系": _status(item.get("relation", "UNKNOWN")),
                    "机制": item.get("mechanism_description"),
                }
                for item in data.get("edges", [])
            ],
        }
    )
