from __future__ import annotations

from typing import Any

from research_os.reporting.document import CapitalFundingBlock, FinancialOperatingBlock, ValuationRationaleBlock
from research_os.reporting.formatting import format_cny
from research_os.reporting.markdown_renderer import ResearchReportMarkdownRenderer as _PreviousRenderer


class ResearchReportMarkdownRenderer(_PreviousRenderer):
    """v1.5.09 additive professional number presentation without recalculation."""

    version = "professional-markdown-renderer@1.1.0"

    _CNY_FUNDING_KEYS = {
        "incremental_revenue",
        "incremental_nwc",
        "incremental_debt",
        "incremental_equity",
        "reported_equity_change",
        "operating_cash_flow",
        "factoring_balance",
        "derecognized_receivables",
        "receivable_transfer_balance",
        "other_working_capital_financing",
    }
    _RATIO_FINANCIAL_FACTS = {
        "revenue_growth",
        "gross_margin",
        "ar_growth",
        "inventory_growth",
    }

    @classmethod
    def _format_financial_fact(cls, item: dict[str, Any]) -> str:
        value = item.get("value")
        if value is None:
            return ""
        fact_key = str(item.get("fact_key", ""))
        unit = item.get("unit")
        if fact_key == "margin_change" and isinstance(value, (int, float)):
            return f"{float(value) * 100:.2f}个百分点"
        if fact_key in cls._RATIO_FINANCIAL_FACTS and isinstance(value, (int, float)):
            return f"{float(value) * 100:.2f}%"
        if unit in {"元", "CNY", "RMB"} and isinstance(value, (int, float)):
            return format_cny(value) or ""
        return cls._display_scalar(value)

    @classmethod
    def _render_financial(cls, block: FinancialOperatingBlock) -> list[str]:
        lines: list[str] = []
        if block.financial_sanity:
            status = cls._semantic_label(block.financial_sanity.get("status"))
            explanation = cls._display_scalar(block.financial_sanity.get("explanation"))
            lines += ["### 财务一致性", ""]
            if status:
                lines.append(f"- **状态**：{status}")
            if explanation:
                lines.append(f"- **说明**：{explanation}")

        if block.core_financial_facts:
            if lines:
                lines.append("")
            lines += [
                "### 核心财务事实",
                "",
                "项目 | 数值 | 期间 | 解释",
                "--- | ---: | --- | ---",
            ]
            for item in block.core_financial_facts:
                lines.append(
                    " | ".join(
                        cls._escape(value)
                        for value in (
                            item.get("label", ""),
                            cls._format_financial_fact(item),
                            item.get("period", ""),
                            item.get("interpretation", ""),
                        )
                    )
                )

        if block.kpi_metrics:
            if lines:
                lines.append("")
            lines += [
                "### 关键经营指标",
                "",
                "指标 | 数值 | 期间 | 状态 | 说明",
                "--- | ---: | --- | --- | ---",
            ]
            for metric in block.kpi_metrics:
                value = metric.get("formatted_value")
                if value in (None, ""):
                    value = cls._display_scalar(metric.get("value"))
                period = cls._display_scalar(metric.get("period_label"))
                status = cls._semantic_label(metric.get("status"))
                reason = metric.get("reason")
                explanation = cls._semantic_explanation(reason) or cls._display_scalar(metric.get("explanation"))
                lines.append(
                    " | ".join(
                        cls._escape(item)
                        for item in (
                            metric.get("label", ""),
                            value,
                            period,
                            status,
                            explanation,
                        )
                    )
                )
        return lines

    @classmethod
    def _funding_value(cls, key: str, value: Any) -> str:
        if key in cls._CNY_FUNDING_KEYS and isinstance(value, (int, float)):
            return format_cny(value) or ""
        if key == "factoring_to_ar" and isinstance(value, (int, float)):
            return f"{float(value) * 100:.2f}%"
        if isinstance(value, dict) and ("label" in value or "explanation" in value):
            return cls._semantic_label(value)
        return cls._display_scalar(value)

    @classmethod
    def _render_capital_funding(cls, block: CapitalFundingBlock) -> list[str]:
        lines: list[str] = []
        if block.capital_efficiency:
            lines += ["### 资本效率", "", *cls._kv_lines(block.capital_efficiency, cls._CAPITAL_LABELS)]
        if block.funding_loop:
            if lines:
                lines.append("")
            lines += ["### 融资循环", ""]
            for key, label in cls._FUNDING_LABELS.items():
                if key not in block.funding_loop:
                    continue
                value = block.funding_loop.get(key)
                if value in (None, "", [], {}):
                    continue
                shown = cls._funding_value(key, value)
                if shown:
                    lines.append(f"- **{label}**：{shown}")
        return lines

    @classmethod
    def _render_valuation_rationale(cls, block: ValuationRationaleBlock) -> list[str]:
        lines: list[str] = []
        if block.valuation_models:
            lines += ["### 模型适用性", "", "模型 | 状态 | 评分 | 说明", "--- | --- | ---: | ---"]
            for model in block.valuation_models:
                score = model.get("score")
                shown_score = f"{float(score):.2f}" if isinstance(score, (int, float)) else cls._display_scalar(score)
                lines.append(
                    " | ".join(
                        cls._escape(item)
                        for item in (
                            model.get("label") or model.get("model_id") or "",
                            cls._semantic_label(model.get("status")),
                            shown_score,
                            model.get("explanation") or cls._display_scalar(model.get("reasons")),
                        )
                    )
                )
        if block.valuation_execution:
            if lines:
                lines.append("")
            lines += ["### 估值执行", ""]
            labels = {
                "selected_model": "选择模型",
                "executed_model": "执行模型",
                "selection_reason": "选择原因",
                "scenario_logic": "情景逻辑",
                "assumptions": "关键假设",
                "driver_bridge": "估值驱动链",
            }
            lines.extend(cls._kv_lines(block.valuation_execution, labels))
        return lines
