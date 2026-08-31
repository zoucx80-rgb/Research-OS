from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from research_os.reporting.research_view_v1_5_05 import (
    HumanReadableResearchView as _PreviousResearchView,
    ResearchViewPresenter as _PreviousResearchViewPresenter,
)
from research_os.runtime.result import ResearchRunResult


class HumanReadableFinancialFact(BaseModel):
    model_config = ConfigDict(frozen=True)

    fact_key: str
    label: str
    value: Any
    unit: str | None = None
    period: str | None = None
    period_end: Any = None
    interpretation: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class HumanReadableResearchView(_PreviousResearchView):
    model_config = ConfigDict(frozen=True)

    core_financial_facts: list[HumanReadableFinancialFact] = Field(default_factory=list)
    presentation_diagnostics: list[str] = Field(default_factory=list)
    presentation_version: str = "professional-research-view@1.4.0"


class ResearchViewPresenter(_PreviousResearchViewPresenter):
    """v1.5.09 additive research-depth projection over canonical artifacts."""

    version = "professional-research-view@1.4.0"

    _FINANCIAL_LABELS = {
        "revenue": "营业收入",
        "revenue_growth": "营业收入增长率",
        "net_profit_parent": "归母净利润",
        "gross_profit": "毛利",
        "gross_margin": "毛利率",
        "margin_change": "毛利率变化",
        "operating_cash_flow": "经营现金流",
        "ocf": "经营现金流",
        "capex_cash": "资本开支现金支出",
        "ar_begin": "期初应收账款",
        "ar_end": "期末应收账款",
        "ar_change": "应收账款变化",
        "ar_growth": "应收账款期末较期初变化率",
        "inventory_begin": "期初存货",
        "inventory_end": "期末存货",
        "inventory_change": "存货变化",
        "inventory_growth": "存货期末较期初变化率",
        "debt_begin": "期初债务",
        "debt_end": "期末债务",
        "debt_change": "债务变化",
        "ppe_begin": "期初固定资产",
        "ppe_end": "期末固定资产",
    }
    _QUESTIONS = {
        "manufacturing.orders_backlog": "订单、在手任务与客户验收进展如何",
        "manufacturing.capacity_utilization": "产能、利用率、良率与产品结构如何变化",
        "manufacturing.raw_material_qualification": "哪些原材料或认证约束可能限制毛利率修复",
        "manufacturing.cash_conversion": "营运资金是否正在转化为经营现金",
        "manufacturing.capex_productivity": "资本开支是否转化为有效产能和资本回报",
        "manufacturing.working_capital_growth": "应收或存货是否快于经营活动增长",
        "distributor.working_capital_growth": "应收和存货是否快于收入增长",
        "distributor.cash_conversion_cycle": "DSO、DIO、DPO 与现金转换周期如何变化",
        "distributor.working_capital_return": "毛利是否足以补偿营运资金占用",
        "distributor.debt_funding": "新增营运资金有多少由债务融资支持",
        "distributor.financing_cost": "融资成本相对毛利的负担有多大",
        "distributor.factoring_exposure": "保理或应收转让暴露的重要性有多高",
        "distributor.impairment_sensitivity": "利润对存货或信用减值有多敏感",
    }
    _QUESTION_TEXT = {
        "What are the order, backlog and customer acceptance dynamics?": _QUESTIONS["manufacturing.orders_backlog"],
        "How are capacity, utilization, yield and product mix changing?": _QUESTIONS["manufacturing.capacity_utilization"],
        "Which raw-material or qualification constraints can limit margin recovery?": _QUESTIONS["manufacturing.raw_material_qualification"],
        "Is working capital converting to operating cash?": _QUESTIONS["manufacturing.cash_conversion"],
        "Is capex translating into productive capacity and capital returns?": _QUESTIONS["manufacturing.capex_productivity"],
        "Are receivables or inventory growing faster than operating activity?": _QUESTIONS["manufacturing.working_capital_growth"],
        "Are receivables and inventory growing faster than revenue?": _QUESTIONS["distributor.working_capital_growth"],
        "How are DSO, DIO, DPO and the cash-conversion cycle changing?": _QUESTIONS["distributor.cash_conversion_cycle"],
        "Does gross profit adequately compensate for working-capital intensity?": _QUESTIONS["distributor.working_capital_return"],
        "How much incremental working capital is debt funded?": _QUESTIONS["distributor.debt_funding"],
        "How large are financing costs relative to gross profit?": _QUESTIONS["distributor.financing_cost"],
        "How material are factoring or receivable-transfer exposures?": _QUESTIONS["distributor.factoring_exposure"],
        "How sensitive is profit to inventory or credit impairment?": _QUESTIONS["distributor.impairment_sensitivity"],
    }

    @staticmethod
    def _confidence(value: Any) -> str | Any:
        if isinstance(value, (int, float)):
            return f"{float(value):.2f} / 1.00"
        return value

    @classmethod
    def _financial_interpretation(cls, fact_key: str, value: Any) -> str | None:
        if not isinstance(value, (int, float)):
            return None
        if fact_key == "margin_change":
            if value < 0:
                return "毛利率同比下降"
            if value > 0:
                return "毛利率同比提升"
            return "毛利率同比持平"
        if fact_key == "ar_growth":
            return "应收账款期末较期初上升" if value > 0 else "应收账款期末较期初下降" if value < 0 else "应收账款期末较期初持平"
        if fact_key == "inventory_growth":
            return "存货期末较期初上升" if value > 0 else "存货期末较期初下降" if value < 0 else "存货期末较期初持平"
        return None

    @classmethod
    def _financial_facts(cls, snapshot) -> list[HumanReadableFinancialFact]:
        if snapshot is None:
            return []
        rows = []
        for item in list(cls._get(snapshot, "facts", []) or []):
            fact_key = str(cls._get(item, "fact_key", ""))
            if not fact_key or fact_key not in cls._FINANCIAL_LABELS:
                continue
            value = cls._get(item, "value")
            rows.append(
                HumanReadableFinancialFact(
                    fact_key=fact_key,
                    label=cls._FINANCIAL_LABELS[fact_key],
                    value=value,
                    unit=cls._get(item, "unit"),
                    period=cls._get(item, "period"),
                    period_end=cls._get(item, "period_end"),
                    interpretation=cls._financial_interpretation(fact_key, value),
                    evidence_ids=list(cls._get(item, "evidence_ids", []) or []),
                )
            )
        return rows

    @classmethod
    def _localize_view_data(cls, data: dict[str, Any]) -> list[str]:
        diagnostics: list[str] = []
        for item in data.get("question_assessments", []):
            question_id = str(item.get("question_id", ""))
            mapped = cls._QUESTIONS.get(question_id)
            if mapped:
                item["question"] = mapped
            else:
                raw = str(item.get("question", ""))
                if raw and raw != cls._QUESTION_TEXT.get(raw):
                    item["question"] = "专业研究问题的中文展示尚未配置"
                    diagnostics.append(f"unmapped question localization: {question_id or raw}")
        for contribution in data.get("report_contributions", []):
            contribution["research_questions"] = [
                cls._QUESTION_TEXT.get(str(question), "专业研究问题的中文展示尚未配置")
                for question in contribution.get("research_questions", [])
            ]
        return diagnostics

    @classmethod
    def _harden_decision_summary(cls, data: dict[str, Any]) -> list[str]:
        diagnostics: list[str] = []
        summary = data.get("decision_summary") or {}
        summary["evidence_confidence"] = cls._confidence(summary.get("evidence_confidence"))
        safe_risks = []
        for risk in summary.get("top_risks", []):
            label = str(risk.get("label", ""))
            code = str(risk.get("code", ""))
            if "尚未配置中文说明" in label or label == "存在尚未配置中文说明的研究状态":
                diagnostics.append(f"unmapped material risk presentation: {code}")
                continue
            safe_risks.append(risk)
        summary["top_risks"] = safe_risks
        return diagnostics

    def build(
        self,
        result: ResearchRunResult,
        locale: str = _PreviousResearchViewPresenter._SUPPORTED_LOCALE,
    ) -> HumanReadableResearchView:
        previous = super().build(result, locale=locale)
        data = previous.model_dump(mode="python")
        diagnostics = self._localize_view_data(data)
        diagnostics.extend(self._harden_decision_summary(data))
        data.update(
            core_financial_facts=self._financial_facts(result.artifacts.get("financial.fact_snapshot")),
            presentation_diagnostics=list(dict.fromkeys(diagnostics)),
            presentation_version=self.version,
        )
        return HumanReadableResearchView.model_validate(data)
