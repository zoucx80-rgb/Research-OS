from __future__ import annotations

from typing import Any

from research_os.reporting.document import ResearchCompletenessBlock
from research_os.reporting.markdown_renderer_v1_5_09 import ResearchReportMarkdownRenderer as _PreviousRenderer


class ResearchReportMarkdownRenderer(_PreviousRenderer):
    """v1.5.10 deterministic display of canonical research-completeness blocks."""

    version = "professional-markdown-renderer@1.2.0"

    @classmethod
    def _shown(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.4g}"
        return cls._display_scalar(value)

    @classmethod
    def _table(cls, headers: list[str], rows: list[list[Any]], right: set[int] | None = None) -> list[str]:
        right = right or set()
        align = ["---:" if index in right else "---" for index in range(len(headers))]
        lines = [" | ".join(headers), " | ".join(align)]
        for row in rows:
            lines.append(" | ".join(cls._escape(cls._shown(value)) for value in row))
        return lines

    @classmethod
    def _render_completeness(cls, block: ResearchCompletenessBlock) -> list[str]:
        payload = block.payload
        if block.kind == "financial_time_series":
            rows = []
            for series in payload or []:
                for point in series.get("points", []):
                    rows.append([series.get("metric_id"), point.get("period"), point.get("value"), series.get("unit")])
            return cls._table(["指标", "期间", "数值", "单位"], rows, {2})

        if block.kind == "operating_evidence":
            rows = []
            for item in payload or []:
                subject = item.get("segment_label") or item.get("entity_label") or ""
                rows.append([item.get("category"), subject, item.get("metric_id"), item.get("value"), item.get("unit"), item.get("period")])
            return cls._table(["类别", "对象", "指标", "数值", "单位", "期间"], rows, {3})

        if block.kind == "cash_flow_quality":
            labels = (
                ("net_profit", "净利润"),
                ("operating_cash_flow", "经营现金流"),
                ("working_capital_contribution", "营运资本变动贡献"),
                ("other_adjustments", "其他调整"),
                ("capex_cash", "资本开支现金支出"),
                ("simplified_fcf", "simplified FCF"),
            )
            lines = []
            for key, label in labels:
                value = payload.get(key)
                if value is not None:
                    lines.append(f"- **{label}**：{cls._shown(value)} {payload.get('unit') or ''}".rstrip())
            lines += ["", "> 口径说明：simplified FCF = 经营现金流 - 资本开支现金支出；它不是 FCFF。"]
            return lines

        if block.kind == "peer_comparison":
            rows = [[item.get("peer_id"), item.get("peer_role"), item.get("product_or_segment"), item.get("metric"), item.get("value"), item.get("period")] for item in payload or []]
            return cls._table(["可比对象", "角色", "产品/分部", "指标", "数值", "期间"], rows, {4})

        if block.kind == "consensus_distribution":
            breadth = {"single_source": "单一来源", "multi_source": "多来源", "none": "无有效来源"}
            rows = [[item.get("metric"), item.get("forecast_period"), item.get("source_count"), breadth.get(item.get("breadth"), item.get("breadth")), item.get("low"), item.get("median"), item.get("high"), item.get("dispersion")] for item in payload or []]
            return cls._table(["指标", "预测期", "来源数", "覆盖", "低值", "中位数", "高值", "分歧范围"], rows, {2, 4, 5, 6, 7})

        if block.kind == "sensitivity_scenarios":
            rows = [[item.get("driver_id"), item.get("shock_label"), item.get("affected_metric"), item.get("result") if item.get("result") is not None else f"{cls._shown(item.get('result_low'))}–{cls._shown(item.get('result_high'))}", item.get("probability")] for item in payload or []]
            return cls._table(["驱动", "冲击", "影响指标", "结果", "主观概率"], rows, {3, 4})

        if block.kind == "monitoring_calendar":
            rules = payload.get("rules", [])
            events = payload.get("events", [])
            lines = ["### 量化监控规则", ""]
            lines += cls._table(["指标", "条件", "阈值", "频率", "依据"], [[item.get("metric"), item.get("operator"), item.get("threshold"), item.get("frequency"), item.get("rationale")] for item in rules], {2})
            lines += ["", "### 验证事件日历", ""]
            lines += cls._table(["事件", "类型", "时间", "状态", "信息价值"], [[item.get("label"), item.get("event_type"), item.get("due_ts"), item.get("status"), item.get("information_value")] for item in events])
            return lines

        if block.kind == "prior_run_review":
            rows = [[item.get("prior_statement"), item.get("metric"), item.get("predicted_value"), item.get("actual_value"), item.get("status"), item.get("absolute_error")] for item in payload.get("items", [])]
            lines = cls._table(["上期判断", "指标", "预测", "实际", "结果", "绝对误差"], rows, {2, 3, 5})
            lines += ["", f"已评分 {payload.get('scored_count', 0)} 项；命中 {payload.get('hit_count', 0)} 项；未命中 {payload.get('miss_count', 0)} 项。"]
            return lines

        if block.kind == "methodology_disclosure":
            labels = {
                "architecture": "单向研究链",
                "pit_rule": "PIT 规则",
                "lineage_rule": "证据与假设边界",
                "threshold_policy": "监控阈值规则",
                "cash_flow_methodology": "现金流口径",
                "missingness_policy": "缺失值规则",
            }
            lines = []
            for key, label in labels.items():
                value = payload.get(key)
                if not value:
                    continue
                if key == "cash_flow_methodology":
                    lines.append("- **现金流口径**：simplified FCF 仅在 OCF 与资本开支均有明确输入时计算，且不是 FCFF。")
                else:
                    lines.append(f"- **{label}**：{cls._shown(value)}")
            return lines

        return []

    @classmethod
    def _render_block(cls, block):
        if isinstance(block, ResearchCompletenessBlock):
            return cls._render_completeness(block)
        return super()._render_block(block)
