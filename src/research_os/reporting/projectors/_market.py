from __future__ import annotations

from typing import Any

from pydantic import JsonValue

from ._shared import _json, _metric, _model, _number, _reason, _status


def _expectation_snapshot(data: dict[str, Any]) -> JsonValue:
    vintage = data.get("vintage") or {}
    return _json(
        {
            "一致预期时点": vintage.get("as_of"),
            "预测期间": vintage.get("forecast_period"),
            "营业收入": _number(vintage.get("revenue"), unit="CNY"),
            "净利润": _number(vintage.get("net_profit"), unit="CNY"),
            "EPS": _number(vintage.get("eps")),
            "毛利率": _number(vintage.get("gross_margin"), unit="ratio"),
            "来源数量": vintage.get("source_count"),
            "来源质量": _number(vintage.get("source_quality"), field_name="source_quality"),
        }
    )


def _expectation_quality(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "质量状态": _status(data.get("quality_status", "UNKNOWN")),
            "数据年龄": _number(data.get("age_days"), unit="days"),
            "来源数量": data.get("source_count"),
            "限制": [_reason(item) for item in data.get("reason_codes", [])],
        }
    )


def _expectation_gap(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "指标": _metric(data.get("metric_id")),
            "市场预期": _number(data.get("market_value")),
            "Research OS 判断": _number(data.get("os_value")),
            "方向": _status(data.get("direction", "MIXED")),
            "差额": _number(data.get("magnitude")),
            "比较口径": data.get("comparison_basis"),
        }
    )


def _consensus_distribution(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "指标": _metric(data.get("metric_id")),
            "预测期间": data.get("forecast_period"),
            "来源数量": data.get("source_count"),
            "低位": _number(data.get("low")),
            "中位": _number(data.get("median")),
            "高位": _number(data.get("high")),
        }
    )


def _forecast(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "验证状态": _status(data.get("evaluation_status", "INSUFFICIENT_EVIDENCE")),
            "模型": _model(data.get("model_key")) if data.get("model_key") else None,
            "基准": _model(data.get("benchmark_key")) if data.get("benchmark_key") else None,
            "训练截止": data.get("train_cutoff"),
            "评估时点": data.get("evaluation_ts"),
            "OOS 验证折数": len(data.get("folds", [])),
        }
    )


def _forecast_benchmark(data: dict[str, Any]) -> JsonValue:
    metrics = {
        item.get("metric_name"): item.get("value") for item in data.get("metrics", [])
    }
    return _json(
        {
            "模型": _model(data.get("model_key")) if data.get("model_key") else None,
            "目标指标": _metric(data.get("target_metric")),
            "预测周期": data.get("horizon"),
            "样本数": data.get("sample_count"),
            "样本外折数": data.get("fold_count"),
            "样本外验证": bool(data.get("out_of_sample")),
            "PIT 合规": bool(data.get("pit_compliant")),
            "基准模型": _model(data.get("benchmark_key")) if data.get("benchmark_key") else None,
            "基准版本": data.get("benchmark_version"),
            "模型 MAE": _number(metrics.get("MAE")),
            "模型 RMSE": _number(metrics.get("RMSE")),
            "方向准确率": _number(metrics.get("DIRECTION_ACCURACY"), unit="ratio"),
            "区间覆盖率": _number(metrics.get("INTERVAL_COVERAGE"), unit="ratio"),
            "基准 MAE": _number(data.get("benchmark_mae")),
            "相对基准改善": _number(data.get("improvement"), unit="ratio"),
            "跨折稳定": data.get("stable"),
            "稳定性窗口": [
                {
                    "窗口": item.get("window_key"),
                    "模型 MAE": _number(item.get("model_mae")),
                    "基准 MAE": _number(item.get("benchmark_mae")),
                }
                for item in data.get("stability_windows", [])
            ],
            "当前阶段": _status(data.get("current_stage")) if data.get("current_stage") else None,
            "下一阶段": _status(data.get("next_stage")) if data.get("next_stage") else None,
            "晋级结论": _reason(data.get("promotion_reason"))
            if data.get("promotion_reason")
            else None,
            "适用范围": data.get("applicability"),
            "模型边界": data.get("model_boundary"),
            "限制": data.get("caveats", []),
            "不足原因": [_reason(item) for item in data.get("reason_codes", [])],
        }
    )


def _peers(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "同行比较": [
                {
                    "公司": item.get("company_id"),
                    "指标": _metric(item.get("metric_id")),
                    "期间": item.get("period"),
                    "数值": _number(
                        item.get("value"), unit=item.get("unit"), field_name=item.get("metric_id")
                    ),
                    "可比性": _status(item.get("status", "INSUFFICIENT_EVIDENCE")),
                    "限制": [_reason(code) for code in item.get("reason_codes", [])],
                }
                for item in data.get("peers", [])
            ]
        }
    )


def _valuation_routing(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "主要方法": [_model(item) for item in data.get("primary_model_keys", [])],
            "交叉验证方法": [_model(item) for item in data.get("secondary_model_keys", [])],
        }
    )


def _valuation_execution(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "模型结果": [
                {
                    "模型": _model(item.get("model_key")),
                    "状态": _status(item.get("status", "INSUFFICIENT_EVIDENCE")),
                    "估值": _number(item.get("value"), unit=item.get("unit")),
                }
                for item in data.get("results", [])
            ]
        }
    )


def _valuation_result(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "模型": _model(data.get("model_key")),
            "状态": _status(data.get("status", "INSUFFICIENT_EVIDENCE")),
            "估值": _number(data.get("value"), unit=data.get("unit")),
        }
    )


def _valuation_reconciliation(data: dict[str, Any]) -> JsonValue:
    unit = "CNY/share"
    return _json(
        {
            "交叉验证状态": _status(data.get("reconciliation_status", "INSUFFICIENT_EVIDENCE")),
            "综合区间下限": _number(data.get("low"), unit=unit),
            "综合区间上限": _number(data.get("high"), unit=unit),
            "纳入区间": [
                _model(str(item).lower().removesuffix("-range").removesuffix("_range"))
                for item in data.get("included_range_keys", [])
            ],
        }
    )


def _sensitivities(data: dict[str, Any]) -> JsonValue:
    return _json(
        {
            "情景": [
                {
                    "情景": str(item.get("shock_label") or item.get("case_key") or "情景分析"),
                    "驱动": _metric(item.get("driver_key")),
                    "冲击": item.get("shock_label"),
                    "受影响指标": _metric(item.get("affected_metric")),
                    "基准值": _number(item.get("base_value")),
                    "情景结果": _number(item.get("result")),
                    "发生概率": _number(item.get("probability"), unit="ratio"),
                    "关键假设": [
                        {
                            "假设": assumption.get("label"),
                            "取值": assumption.get("value"),
                        }
                        for assumption in item.get("material_assumptions", [])
                    ],
                    "模型边界": item.get("model_boundary"),
                    "适用范围": item.get("applicability"),
                    "限制": item.get("caveats", []),
                }
                for item in data.get("cases", [])
            ]
        }
    )
