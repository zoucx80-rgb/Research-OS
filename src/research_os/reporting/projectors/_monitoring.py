from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import JsonValue

from ._shared import (
    _METRIC_UNITS,
    _date_text,
    _dimension,
    _json,
    _metric,
    _number,
    _reason,
    _status,
)


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


def _sufficiency_item(value: Any) -> str:
    text = str(value)
    prefix, separator, metric_id = text.partition(":")
    if separator and prefix == "observation":
        return f"已观察：{_metric(metric_id)}"
    if separator and prefix == "comparable_trend":
        return f"可比趋势：{_metric(metric_id)}"
    if text == "comparable_financial_trends":
        return "可比财务趋势"
    if text == "lineage:financial_temporal":
        return "财务跨期分析的证据沿袭"
    return text.replace("_", " ")


def _sufficiency_reason(value: Any) -> str:
    text = str(value)
    metric_id, separator, reason_code = text.partition(":")
    if separator:
        return f"{_metric(metric_id)}：{_reason(reason_code)}"
    return _reason(text)


def _coverage(value: Any) -> str:
    text = str(value)
    return {
        "COMPLETE": "完整",
        "PARTIAL": "部分",
        "MISSING": "缺失",
        "NOT_APPLICABLE": "不适用",
    }.get(text, _status(text))


def _required_evidence(value: Any) -> str:
    text = str(value)
    if text.startswith("comparable ") and text.endswith(" period"):
        return f"可比{_metric(text.removeprefix('comparable ').removesuffix(' period'))}报告期"
    if text.startswith("add a comparable "):
        metric_id = text.removeprefix("add a comparable ").split(" period", maxsplit=1)[0]
        return f"补充可比{_metric(metric_id)}报告期，明确比较口径并绑定证据版本"
    labels = {
        "explicit comparison basis": "明确的比较口径",
        "revision-bound lineage": "绑定版本的证据沿袭",
        "revision-bound evidence or assumption lineage": "绑定版本的证据或假设沿袭",
        "add revision-bound evidence or assumption lineage": "补充绑定版本的证据或假设沿袭",
        "at least two comparable financial periods": "至少两个可比财务报告期",
        "add at least two comparable financial periods with explicit basis and lineage": (
            "补充至少两个可比财务报告期，明确比较口径并绑定证据版本"
        ),
        "add comparable period observations with explicit basis and lineage": (
            "补充可比报告期观察，明确比较口径并绑定证据版本"
        ),
    }
    return labels.get(text, text)


def _sufficiency(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "总体状态": _status(data.get("overall_status", "INSUFFICIENT_EVIDENCE")),
            "阻断缺口": [
                _reason(str(item).rsplit(":", maxsplit=1)[-1])
                for item in data.get("blocking_gap_keys", [])
            ],
            "领域": [
                {
                    "领域": _dimension(item.get("domain_id")),
                    "覆盖": _coverage(item.get("coverage", "MISSING")),
                    "证据质量": _coverage(item.get("evidence_quality", "MISSING")),
                    "跨期覆盖": _coverage(item.get("temporal_coverage", "MISSING")),
                    "基准覆盖": _coverage(item.get("benchmark_coverage", "NOT_APPLICABLE")),
                    "同行覆盖": _coverage(item.get("peer_coverage", "NOT_APPLICABLE")),
                    "模型可执行性": _status(item.get("model_executability", "NOT_APPLICABLE")),
                    "已知": [_sufficiency_item(value) for value in item.get("known_items", [])],
                    "未知": [_sufficiency_item(value) for value in item.get("unknown_items", [])],
                    "未知原因": [
                        _sufficiency_reason(value) for value in item.get("why_unknown", [])
                    ],
                    "升级所需证据": [
                        _required_evidence(value)
                        for value in item.get("upgrade_evidence_requirements", [])
                    ],
                    "重大缺口": [
                        {
                            "原因": _reason(gap.get("reason_code")),
                            "所需证据": [
                                _required_evidence(value)
                                for value in gap.get("required_evidence", [])
                            ],
                        }
                        for gap in item.get("material_gaps", [])
                    ],
                }
                for item in data.get("domains", [])
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
