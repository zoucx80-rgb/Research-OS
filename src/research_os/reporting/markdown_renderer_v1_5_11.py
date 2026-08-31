from __future__ import annotations

from datetime import date, datetime
from typing import Any

from research_os.reporting.document import ResearchReportDocument, ValuationRationaleBlock
from research_os.reporting.markdown_renderer_v1_5_10 import (
    ResearchReportMarkdownRenderer as _PreviousRenderer,
)


class ResearchReportMarkdownRenderer(_PreviousRenderer):
    """v1.5.11 investor-facing integrity formatting without semantic recomputation."""

    version = "professional-markdown-renderer@1.3.0"

    @staticmethod
    def _escape(value: Any) -> str:
        if value is None:
            return "—"
        return _PreviousRenderer._escape(value)

    @classmethod
    def _shown(cls, value: Any) -> str:
        if value is None:
            return "—"
        return super()._shown(value)

    @staticmethod
    def _body_date(value: Any) -> str:
        if isinstance(value, datetime):
            return value.date().isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if value in (None, ""):
            return ""
        text = str(value)
        if "T" in text and len(text) >= 10:
            return text[:10]
        return text

    @classmethod
    def _render_snapshot(cls, document: ResearchReportDocument) -> list[str]:
        return [
            line.replace("证据置信度", "已采纳证据质量")
            for line in super()._render_snapshot(document)
        ]

    @classmethod
    def _render_valuation_rationale(cls, block: ValuationRationaleBlock) -> list[str]:
        lines: list[str] = []
        if block.valuation_models:
            lines += [
                "### 模型适用性",
                "",
                "模型 | 适用性 | 说明",
                "--- | --- | ---",
            ]
            for model in block.valuation_models:
                lines.append(
                    " | ".join(
                        cls._escape(item)
                        for item in (
                            model.get("label") or model.get("model_id") or "",
                            cls._semantic_label(model.get("status")),
                            model.get("explanation")
                            or cls._display_scalar(model.get("reasons")),
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

    def render(self, document: ResearchReportDocument) -> str:
        text = super().render(document)
        body_date = self._body_date(
            document.metadata.get("decision_ts") or document.decision_snapshot.decision_ts
        )
        if not body_date:
            return text

        lines = text.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("**决策日期**："):
                lines[index] = f"**决策日期**：{body_date}"
                break
        return "\n".join(lines).rstrip() + "\n"
