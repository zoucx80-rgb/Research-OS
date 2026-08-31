from __future__ import annotations

from typing import Any

from research_os.reporting.document import ResearchCompletenessBlock, ValuationRationaleBlock
from research_os.reporting.markdown_renderer_v1_5_11 import (
    ResearchReportMarkdownRenderer as _PreviousRenderer,
)


class ResearchReportMarkdownRenderer(_PreviousRenderer):
    """v1.5.12 renderer for inseparable qualifiers and typed reconciliation."""

    version = "professional-markdown-renderer@1.4.0"

    _THRESHOLD_TYPE_LABELS = {
        "company_guidance": "公司指引阈值",
        "accounting_or_regulatory": "会计或监管阈值",
        "industry_benchmark": "行业基准阈值",
        "historical_company_benchmark": "公司历史基准阈值",
        "analyst_defined_monitoring": "研究预警线",
        "contractual": "合同阈值",
        "other": "其他来源阈值",
    }
    _RECONCILIATION_LABELS = {
        "INTERSECTION": "数学交集",
        "CROSS_CHECK_BAND": "交叉校验带",
        "MODEL_DISAGREEMENT": "模型分歧",
        "NOT_COMPARABLE": "口径不可比",
        "INSUFFICIENT_EVIDENCE": "证据不足",
    }
    _CYCLE_LABELS = {
        "RECOVERY_NOT_OBSERVED": "尚未观察到修复迹象；周期底部无法判断",
        "RECOVERY_OBSERVED": "修复迹象已观察；周期底部未确认",
        "TROUGH_UNCONFIRMED": "修复迹象已观察；周期底部未确认",
        "TROUGH_CONFIRMED": "周期底部已确认",
    }
    _MOAT_LABELS = {
        "INSUFFICIENT_MOAT_EVIDENCE": "护城河证据不足",
        "OTHER_BARRIER_EVIDENCED": "非技术壁垒有证据；不等同于已实现经济护城河",
        "TECHNICAL_BARRIER_EVIDENCED": "技术壁垒有证据；不等同于已实现经济护城河",
        "ECONOMIC_MOAT_UNREALIZED": "商业壁垒有证据；经济护城河尚未实现",
        "ECONOMIC_MOAT_REALIZED": "经济护城河已实现",
    }

    @classmethod
    def _assumption_text(cls, assumptions: list[dict[str, Any]]) -> str:
        values = []
        for item in assumptions:
            value = cls._shown(item.get("value"))
            unit = item.get("unit") or ""
            values.append(
                f"{item.get('label') or item.get('assumption_id') or ''}={value}{unit}"
            )
        return "；".join(values)

    @classmethod
    def _render_completeness(cls, block: ResearchCompletenessBlock) -> list[str]:
        payload = block.payload
        if block.kind == "semantic_claims":
            lines: list[str] = []
            cycle = payload.get("cycle") or {}
            moat = payload.get("moat") or {}
            if cycle:
                lines.append(
                    f"- **周期判断**：{cls._CYCLE_LABELS.get(cycle.get('state'), cycle.get('state') or '—')}"
                )
                lines.append(f"- **主张强度**：{cycle.get('claim_strength') or '—'}")
            if moat:
                lines.append(
                    f"- **护城河判断**：{cls._MOAT_LABELS.get(moat.get('state'), moat.get('state') or '—')}"
                )
            return lines

        if block.kind == "sensitivity_scenarios":
            lines: list[str] = []
            for item in payload or []:
                if lines:
                    lines.append("")
                lines += [f"### {item.get('shock_label') or item.get('driver_id') or '情景'}", ""]
                result = item.get("result")
                if result is None and any(
                    item.get(key) is not None for key in ("result_low", "result_high")
                ):
                    result = (
                        f"{cls._shown(item.get('result_low'))}–"
                        f"{cls._shown(item.get('result_high'))}"
                    )
                lines.append(
                    f"- **结果**：{item.get('affected_metric') or ''} = {cls._shown(result)}"
                )
                assumptions = list(item.get("material_assumptions") or [])
                if assumptions:
                    lines.append(f"- **关键假设**：{cls._assumption_text(assumptions)}")
                if item.get("model_boundary"):
                    lines.append(f"- **模型边界**：{item['model_boundary']}")
                if item.get("applicability"):
                    lines.append(f"- **适用范围**：{item['applicability']}")
                caveats = list(item.get("caveats") or [])
                if caveats:
                    lines.append(f"- **限定条件**：{'；'.join(str(item) for item in caveats)}")
                if item.get("probability") is not None:
                    lines.append(f"- **主观概率**：{cls._shown(item['probability'])}")
            return lines

        if block.kind == "monitoring_calendar":
            rules = payload.get("rules", [])
            events = payload.get("events", [])
            lines = ["### 量化监控规则", ""]
            lines += cls._table(
                ["指标", "条件", "阈值", "阈值性质", "来源", "比较口径", "适用范围", "频率", "依据"],
                [
                    [
                        item.get("metric"),
                        item.get("operator"),
                        item.get("threshold"),
                        cls._THRESHOLD_TYPE_LABELS.get(
                            item.get("threshold_type"), item.get("threshold_type")
                        ),
                        item.get("threshold_source"),
                        item.get("comparison_basis"),
                        item.get("applicability"),
                        item.get("frequency"),
                        item.get("rationale"),
                    ]
                    for item in rules
                ],
                {2},
            )
            lines += ["", "### 验证事件日历", ""]
            lines += cls._table(
                ["事件", "类型", "时间", "状态", "信息价值"],
                [
                    [
                        item.get("label"),
                        item.get("event_type"),
                        item.get("due_ts"),
                        item.get("status"),
                        item.get("information_value"),
                    ]
                    for item in events
                ],
            )
            return lines

        return super()._render_completeness(block)

    @classmethod
    def _render_valuation_rationale(cls, block: ValuationRationaleBlock) -> list[str]:
        lines = list(super()._render_valuation_rationale(block))
        if block.valuation_model_rationales:
            if lines:
                lines.append("")
            lines += ["### 经济适用性理由", ""]
            lines += cls._table(
                ["模型", "结论", "经济因素", "说明"],
                [
                    [
                        item.get("model_id"),
                        item.get("status"),
                        cls._display_scalar(item.get("economic_factors") or []),
                        item.get("explanation"),
                    ]
                    for item in block.valuation_model_rationales
                ],
            )
        reconciliation = block.valuation_reconciliation
        if not reconciliation:
            return lines
        if lines:
            lines.append("")
        status = reconciliation.get("status")
        lines += ["### 跨模型估值协调", ""]
        lines.append(
            f"- **协调结论**：{cls._RECONCILIATION_LABELS.get(status, status or '—')}"
        )
        low = reconciliation.get("low")
        high = reconciliation.get("high")
        if low is not None and high is not None:
            currency = reconciliation.get("currency") or ""
            lines.append(
                f"- **协调区间**：{cls._shown(low)}–{cls._shown(high)} {currency}".rstrip()
            )
        if reconciliation.get("basis"):
            lines.append(f"- **估值口径**：{reconciliation['basis']}")
        if reconciliation.get("reason"):
            lines.append(f"- **依据**：{reconciliation['reason']}")
        return lines
