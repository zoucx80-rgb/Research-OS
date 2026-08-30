from __future__ import annotations

from datetime import date, datetime
from typing import Any

from research_os.reporting.document import (
    CapitalFundingBlock,
    CausalBridgeBlock,
    EvidenceNoteBlock,
    ExpectationForecastBlock,
    ExpectationGapBlock,
    FinancialOperatingBlock,
    GapClassificationBlock,
    LimitationBlock,
    MonitoringBlock,
    NarrativeBlock,
    ResearchReportDocument,
    StateProvenanceBlock,
    ThesisDebateBlock,
    ValuationBlock,
    ValuationRationaleBlock,
)


class ResearchReportMarkdownRenderer:
    """Deterministic zh-CN Markdown projection of one ResearchReportDocument."""

    version = "professional-markdown-renderer@1.0.0"

    _CAPITAL_LABELS = {
        "calculation_status": "计算状态",
        "roic": "ROIC",
        "incremental_roic": "增量ROIC",
        "iwcr": "IWCR",
        "iwcr_limitation": "IWCR限制",
    }
    _FUNDING_LABELS = {
        "calculation_status": "计算状态",
        "state": "融资循环状态",
        "reasons": "判断依据",
        "incremental_revenue": "新增收入",
        "incremental_nwc": "新增净营运资金",
        "incremental_debt": "新增债务",
        "incremental_equity": "新增外部股权融资",
        "reported_equity_change": "报告口径权益变动",
        "operating_cash_flow": "经营现金流",
        "factoring_balance": "保理余额",
        "derecognized_receivables": "终止确认应收款",
        "receivable_transfer_balance": "应收转让余额",
        "other_working_capital_financing": "其他营运资金融资",
        "factoring_to_ar": "保理暴露对应收比",
        "comparison_basis_status": "比较期间基准",
        "comparison_basis_limitations": "比较期间限制",
    }
    _EXPECTATION_LABELS = {
        "state": "预期质量",
        "reasons": "限制/依据",
        "source_count": "来源数量",
        "source_quality": "来源质量",
        "age_days": "预期年龄（天）",
        "latest_material_event_ts": "最近重大事件时间",
        "latest_material_event_label": "最近重大事件",
        "post_event_consensus": "是否已吸收最近重大事件",
    }
    _VALUATION_RESULT_LABELS = {
        "currency": "币种",
        "valuation_date": "估值日期",
        "equity_value": "股权价值",
        "enterprise_value": "企业价值",
        "per_share_value": "每股价值",
        "bear_case": "熊市情景",
        "base_case": "基准情景",
        "bull_case": "牛市情景",
        "primary_range_low": "主估值区间下限",
        "primary_range_high": "主估值区间上限",
        "current_price": "当前价格",
        "implied_upside_downside": "隐含涨跌幅",
        "method_result": "方法结果",
        "sensitivities": "敏感性",
        "limitations": "估值限制",
    }

    @staticmethod
    def _escape(value: Any) -> str:
        text = str(value).replace("\n", " ").replace("|", "\\|").strip()
        return text

    @classmethod
    def _semantic_label(cls, value: Any) -> str:
        if value is None:
            return ""
        if hasattr(value, "label"):
            return cls._escape(getattr(value, "label"))
        if isinstance(value, dict):
            label = value.get("label")
            if label not in (None, ""):
                return cls._escape(label)
            explanation = value.get("explanation")
            if explanation not in (None, ""):
                return cls._escape(explanation)
        return cls._display_scalar(value)

    @classmethod
    def _semantic_explanation(cls, value: Any) -> str:
        if value is None:
            return ""
        if hasattr(value, "explanation"):
            return cls._escape(getattr(value, "explanation"))
        if isinstance(value, dict):
            explanation = value.get("explanation")
            if explanation not in (None, ""):
                return cls._escape(explanation)
        return ""

    @classmethod
    def _display_scalar(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "是" if value else "否"
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, float):
            return f"{value:.10g}"
        if isinstance(value, int):
            return str(value)
        if hasattr(value, "label"):
            return cls._semantic_label(value)
        if isinstance(value, dict):
            if "label" in value or "explanation" in value:
                return cls._semantic_label(value)
            parts = []
            for key in sorted(value):
                shown = cls._display_scalar(value[key])
                if shown:
                    parts.append(f"{key}: {shown}")
            return "; ".join(parts)
        if isinstance(value, (list, tuple)):
            return "；".join(
                shown for item in value if (shown := cls._display_scalar(item))
            )
        return cls._escape(value)

    @classmethod
    def _bullet_list(cls, items: list[Any]) -> list[str]:
        return [f"- {shown}" for item in items if (shown := cls._display_scalar(item))]

    @classmethod
    def _kv_lines(cls, payload: dict[str, Any], labels: dict[str, str]) -> list[str]:
        lines: list[str] = []
        for key, label in labels.items():
            if key not in payload:
                continue
            value = payload.get(key)
            if value in (None, "", [], {}):
                continue
            shown = cls._semantic_label(value) if isinstance(value, dict) and (
                "label" in value or "explanation" in value
            ) else cls._display_scalar(value)
            if shown:
                lines.append(f"- **{label}**：{shown}")
        return lines

    @classmethod
    def _render_snapshot(cls, document: ResearchReportDocument) -> list[str]:
        item = document.decision_snapshot
        lines = ["## 投资决策快照", "", "| 维度 | 结论 |", "| --- | --- |"]
        rows = [
            ("业务模型", cls._semantic_label(item.business_model)),
            ("研究决策", cls._semantic_label(item.decision_state)),
            ("基本面", cls._semantic_label(item.fundamental_state)),
            ("投资逻辑", cls._semantic_label(item.thesis_state)),
            ("市场预期", cls._semantic_label(item.expectation_state)),
            ("估值", cls._semantic_label(item.valuation_state)),
            ("证据置信度", cls._display_scalar(item.evidence_confidence)),
        ]
        for label, value in rows:
            if value:
                lines.append(f"| {label} | {value} |")
        lines += ["", "### 核心投资逻辑", "", item.primary_thesis]
        if item.material_drivers:
            lines += ["", "### 关键驱动", "", *cls._bullet_list(item.material_drivers)]
        if item.material_risks:
            lines += ["", "### 关键风险", ""]
            for risk in item.material_risks:
                label = cls._semantic_label(risk)
                explanation = cls._semantic_explanation(risk)
                lines.append(f"- **{label}**{f'：{explanation}' if explanation and explanation != label else ''}")
        if item.next_verification_event:
            lines += ["", f"**下一验证事件**：{item.next_verification_event}"]
        if item.top_limitation:
            lines += ["", f"**最重要研究限制**：{item.top_limitation}"]
        return lines

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
    def _render_capital_funding(cls, block: CapitalFundingBlock) -> list[str]:
        lines: list[str] = []
        if block.capital_efficiency:
            lines += ["### 资本效率", "", *cls._kv_lines(block.capital_efficiency, cls._CAPITAL_LABELS)]
        if block.funding_loop:
            if lines:
                lines.append("")
            lines += ["### 融资循环", "", *cls._kv_lines(block.funding_loop, cls._FUNDING_LABELS)]
        return lines

    @classmethod
    def _render_thesis(cls, block: ThesisDebateBlock) -> list[str]:
        lines: list[str] = []
        for thesis in block.theses:
            title = cls._display_scalar(thesis.get("title")) or "投资逻辑"
            lines += [f"### {title}", ""]
            status = cls._semantic_label(thesis.get("status"))
            if status:
                lines.append(f"- **状态**：{status}")
            for key, label in (
                ("statement", "主逻辑"),
                ("mechanism", "作用机制"),
                ("anti_thesis", "反方逻辑"),
            ):
                shown = cls._display_scalar(thesis.get(key))
                if shown:
                    lines.append(f"- **{label}**：{shown}")
            falsifiers = thesis.get("falsifiers") or []
            if falsifiers:
                lines += ["", "#### 证伪条件", ""]
                for falsifier in falsifiers:
                    metric = cls._display_scalar(falsifier.get("metric_label"))
                    operator = cls._display_scalar(falsifier.get("operator"))
                    threshold = cls._display_scalar(falsifier.get("threshold"))
                    explanation = cls._display_scalar(falsifier.get("explanation"))
                    condition = " ".join(item for item in (metric, operator, threshold) if item)
                    lines.append(f"- {condition}{f'：{explanation}' if explanation else ''}")
            confidence = thesis.get("confidence")
            if confidence is not None:
                lines.append(f"- **置信度**：{cls._display_scalar(confidence)}")
            next_check = cls._display_scalar(thesis.get("next_check_date"))
            if next_check:
                lines.append(f"- **下一检查日期**：{next_check}")
            lines.append("")
        if block.signal_assessment:
            lines += ["### 逻辑信号评估", ""]
            state = cls._semantic_label(block.signal_assessment.get("state"))
            if state:
                lines.append(f"- **状态**：{state}")
            positive = block.signal_assessment.get("positive_signals") or []
            negative = block.signal_assessment.get("negative_signals") or []
            if positive:
                lines += ["- **正面信号**：" + "；".join(cls._display_scalar(v) for v in positive)]
            if negative:
                lines += ["- **负面信号**：" + "；".join(cls._display_scalar(v) for v in negative)]
        return lines

    @classmethod
    def _render_expectation_forecast(cls, block: ExpectationForecastBlock) -> list[str]:
        lines: list[str] = []
        if block.expectation_quality:
            lines += ["### 市场预期质量", "", *cls._kv_lines(block.expectation_quality, cls._EXPECTATION_LABELS)]
        if block.forecast_discipline:
            if lines:
                lines.append("")
            lines += ["### 预测纪律", ""]
            status = cls._semantic_label(block.forecast_discipline.get("status"))
            reason = cls._display_scalar(block.forecast_discipline.get("reason"))
            if status:
                lines.append(f"- **状态**：{status}")
            if reason:
                lines.append(f"- **说明**：{reason}")
        return lines

    @classmethod
    def _render_expectation_gap(cls, block: ExpectationGapBlock) -> list[str]:
        labels = {
            "metric": "指标",
            "direction": "预期差方向",
            "market_value": "市场值",
            "market_range_low": "市场区间下限",
            "market_range_high": "市场区间上限",
            "market_direction": "市场方向",
            "os_value": "Research OS值",
            "os_range_low": "Research OS区间下限",
            "os_range_high": "Research OS区间上限",
            "os_direction": "Research OS方向",
            "magnitude": "差异幅度",
            "unit": "单位",
            "comparison_basis": "比较口径",
            "source_count": "来源数量",
            "source_quality": "来源质量",
            "age_days": "预期年龄（天）",
            "post_event_consensus": "是否已吸收最近重大事件",
            "limitation": "限制",
        }
        return cls._kv_lines(block.payload, labels)

    @classmethod
    def _render_valuation_rationale(cls, block: ValuationRationaleBlock) -> list[str]:
        lines: list[str] = []
        if block.valuation_models:
            lines += ["### 模型适用性", "", "模型 | 状态 | 评分 | 说明", "--- | --- | ---: | ---"]
            for model in block.valuation_models:
                lines.append(
                    " | ".join(
                        cls._escape(item)
                        for item in (
                            model.get("label") or model.get("model_id") or "",
                            cls._semantic_label(model.get("status")),
                            cls._display_scalar(model.get("score")),
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

    @classmethod
    def _render_valuation(cls, block: ValuationBlock) -> list[str]:
        return cls._kv_lines(block.payload, cls._VALUATION_RESULT_LABELS)

    @classmethod
    def _render_monitoring(cls, block: MonitoringBlock) -> list[str]:
        lines: list[str] = []
        if block.next_verification_event:
            lines.append(f"- **下一验证事件**：{block.next_verification_event}")
        if block.conviction_up_conditions:
            lines += ["", "### Conviction 上升条件", "", *cls._bullet_list(block.conviction_up_conditions)]
        if block.thesis_broken_conditions:
            lines += ["", "### Thesis Broken 条件", "", *cls._bullet_list(block.thesis_broken_conditions)]
        if block.key_metrics:
            lines += ["", "### 关键监控指标", "", *cls._bullet_list(block.key_metrics)]
        return lines

    @classmethod
    def _render_state_provenance(cls, block: StateProvenanceBlock) -> list[str]:
        lines = ["维度 | 状态 | 来源 | 方法", "--- | --- | --- | ---"]
        for item in block.items:
            lines.append(
                " | ".join(
                    cls._escape(value)
                    for value in (
                        item.get("dimension", ""),
                        cls._semantic_label(item.get("state")),
                        cls._semantic_label(item.get("source")),
                        item.get("method", ""),
                    )
                )
            )
        return lines

    @classmethod
    def _render_gaps(cls, block: GapClassificationBlock) -> list[str]:
        lines: list[str] = []
        for title, items in (
            ("证据缺口", block.evidence_missing),
            ("能力缺口", block.capability_missing),
            ("不适用", block.not_applicable),
            ("展示/延期项", block.presentation_or_deferred),
        ):
            if not items:
                continue
            if lines:
                lines.append("")
            lines += [f"### {title}", "", *cls._bullet_list(items)]
        return lines

    @classmethod
    def _render_block(cls, block: Any) -> list[str]:
        if isinstance(block, NarrativeBlock):
            lines = []
            if block.title:
                lines += [f"### {block.title}", ""]
            lines.append(block.text)
            return lines
        if isinstance(block, FinancialOperatingBlock):
            return cls._render_financial(block)
        if isinstance(block, CapitalFundingBlock):
            return cls._render_capital_funding(block)
        if isinstance(block, CausalBridgeBlock):
            return [" → ".join(block.steps)] if block.steps else []
        if isinstance(block, ThesisDebateBlock):
            return cls._render_thesis(block)
        if isinstance(block, ExpectationForecastBlock):
            return cls._render_expectation_forecast(block)
        if isinstance(block, ExpectationGapBlock):
            return cls._render_expectation_gap(block)
        if isinstance(block, ValuationRationaleBlock):
            return cls._render_valuation_rationale(block)
        if isinstance(block, ValuationBlock):
            return cls._render_valuation(block)
        if isinstance(block, MonitoringBlock):
            return cls._render_monitoring(block)
        if isinstance(block, StateProvenanceBlock):
            return cls._render_state_provenance(block)
        if isinstance(block, GapClassificationBlock):
            return cls._render_gaps(block)
        if isinstance(block, LimitationBlock):
            return cls._bullet_list(block.items)
        if isinstance(block, EvidenceNoteBlock):
            return [block.text] if block.text else []
        raise TypeError(f"Unsupported report block: {type(block).__name__}")

    @classmethod
    def _render_audit_appendix(cls, document: ResearchReportDocument) -> list[str]:
        appendix = document.audit_appendix
        lines = ["## 审计附录", ""]
        rows = [
            ("Repository", appendix.repository),
            ("Commit", appendix.repository_commit),
            ("Research OS", appendix.research_os_version),
            ("Core API", appendix.core_api_version),
            ("Presentation", appendix.presentation_version),
            ("Composition", document.composition_version),
            ("Renderer", cls.version),
        ]
        for label, value in rows:
            if value:
                lines.append(f"- **{label}**：{value}")
        if appendix.industry_plugins:
            lines += ["", "### Industry Plugins", ""]
            for item in appendix.industry_plugins:
                plugin = item.get("plugin_id") or item.get("label") or "plugin"
                version = item.get("plugin_version") or ""
                lines.append(f"- {plugin}{f' @ {version}' if version else ''}")
        if appendix.methodology_plugins:
            lines += ["", "### Methodology Plugins", ""]
            for item in appendix.methodology_plugins:
                plugin = item.get("plugin_id") or item.get("label") or "plugin"
                version = item.get("plugin_version") or ""
                lines.append(f"- {plugin}{f' @ {version}' if version else ''}")
        if appendix.module_statuses:
            lines += ["", "### Module Statuses", ""]
            for name in sorted(appendix.module_statuses):
                status = appendix.module_statuses[name]
                shown = cls._semantic_label(status)
                lines.append(f"- {name}: {shown}")
        if appendix.evidence_ids:
            lines += ["", "### Evidence IDs", "", *cls._bullet_list(appendix.evidence_ids)]
        if appendix.assumption_ids:
            lines += ["", "### Assumption IDs", "", *cls._bullet_list(appendix.assumption_ids)]
        return lines

    def render(self, document: ResearchReportDocument) -> str:
        if not isinstance(document, ResearchReportDocument):
            raise TypeError("ResearchReportMarkdownRenderer.render requires ResearchReportDocument")

        metadata = document.metadata
        company_id = self._display_scalar(metadata.get("company_id")) or document.decision_snapshot.company_id
        decision_ts = self._display_scalar(metadata.get("decision_ts")) or self._display_scalar(document.decision_snapshot.decision_ts)
        business_model = self._display_scalar(metadata.get("business_model")) or self._semantic_label(document.decision_snapshot.business_model)

        lines = ["# 投资研究报告", "", f"**公司**：{company_id}"]
        if decision_ts:
            lines.append(f"**决策日期**：{decision_ts}")
        if business_model:
            lines.append(f"**业务模型**：{business_model}")
        lines += ["", *self._render_snapshot(document)]

        for section in document.sections:
            rendered_blocks: list[str] = []
            for block in section.blocks:
                block_lines = self._render_block(block)
                if not block_lines:
                    continue
                if rendered_blocks and rendered_blocks[-1] != "":
                    rendered_blocks.append("")
                rendered_blocks.extend(block_lines)
            if not any(line.strip() for line in rendered_blocks):
                continue
            lines += ["", f"## {section.title}", "", *rendered_blocks]

        lines += ["", *self._render_audit_appendix(document)]

        cleaned: list[str] = []
        blank = False
        for raw in lines:
            line = raw.rstrip()
            if not line:
                if blank:
                    continue
                blank = True
                cleaned.append("")
            else:
                blank = False
                cleaned.append(line)
        return "\n".join(cleaned).rstrip() + "\n"
