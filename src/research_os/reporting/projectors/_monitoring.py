from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import JsonValue

from ._shared import _METRIC_UNITS, _date_text, _dimension, _json, _metric, _number, _status


def _monitoring_condition(metric_id: str, condition: Any) -> str:
    text = str(condition or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        return text
    operator, raw = parts
    labels = {"gt": "大于", "gte": "大于等于", "lt": "小于", "lte": "小于等于", "eq": "等于"}
    if operator not in labels:
        return text
    try:
        threshold: Any = Decimal(raw)
    except Exception:
        threshold = raw
    unit = _METRIC_UNITS.get(metric_id)
    rendered = (
        _number(threshold, unit=unit, field_name=metric_id)
        if isinstance(threshold, Decimal)
        else str(threshold)
    )
    return f"{labels[operator]} {rendered}"


def _monitoring(data: dict[str, Any]) -> JsonValue:
    next_event = data.get("next_verification_event") or {}
    return _json(
        {
            "监控项": [
                {
                    "指标": _metric(item.get("metric_id")),
                    "触发条件": _monitoring_condition(
                        str(item.get("metric_id") or ""), item.get("condition")
                    ),
                    "下一检查时点": _date_text(item.get("next_check_ts")),
                }
                for item in data.get("items", [])
            ],
            "下一验证事件": (
                {
                    "事件": next_event.get("label"),
                    "类型": _status(next_event.get("event_type")),
                    "计划时点": _date_text(next_event.get("due_ts")),
                    "状态": _status(next_event.get("status")),
                }
                if next_event
                else None
            ),
        }
    )


def _prior_run(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "已评分": data.get("scored_count", 0),
            "命中": data.get("hit_count", 0),
            "未命中": data.get("miss_count", 0),
            "回顾": [
                {
                    "上期判断": item.get("prior_statement"),
                    "结果": _status(item.get("status", "UNKNOWN")),
                    "误差": _number(item.get("error")),
                }
                for item in data.get("items", [])
            ],
        }
    )


def _readiness(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "总体状态": _status(data.get("final_status", "NOT_READY")),
            "阻塞维度": [_dimension(item) for item in data.get("blocking_dimensions", [])],
            "维度": [
                {
                    "维度": _dimension(item.get("dimension_id")),
                    "状态": _status(item.get("status", "INCOMPLETE")),
                }
                for item in data.get("dimensions", [])
            ],
        }
    )


def _methodology_limit(value: Any) -> str:
    text = str(value)
    if "NO_COMPATIBLE_INDUSTRY_PLUGIN" in text:
        return "当前没有与主要业务模式兼容的行业策略插件；行业专属 KPI 不做推断，相关结论保持证据不足。"
    return text


def _methodology(data: dict[str, Any]) -> JsonValue:
    return _json({"研究限制": [_methodology_limit(item) for item in data.get("limitations", [])]})
