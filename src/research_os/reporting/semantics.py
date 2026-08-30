from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from research_os.reporting.summary import DecisionSummary, DecisionSummaryBuilder
from research_os.runtime.result import ResearchRunResult


class SemanticValue(BaseModel):
    """Human-facing meaning with the canonical machine code retained as metadata."""

    model_config = ConfigDict(frozen=True)

    label: str
    explanation: str
    code: str


class HumanReadableDecisionSummary(BaseModel):
    """Read-only human presentation projected from a canonical DecisionSummary."""

    model_config = ConfigDict(frozen=True)

    company_id: str
    business_model: SemanticValue
    primary_thesis: str
    thesis_state: SemanticValue
    fundamental_state: SemanticValue
    expectation_state: SemanticValue
    valuation_state: SemanticValue
    evidence_confidence: str | float
    top_drivers: list[str] = Field(default_factory=list)
    top_risks: list[SemanticValue] = Field(default_factory=list)
    next_verification_event: str = ""
    research_os_version: str
    decision_state: SemanticValue | None = None
    final_status: SemanticValue
    blocking_modules: list[str] = Field(default_factory=list)
    module_statuses: dict[str, SemanticValue] = Field(default_factory=dict)
    expectation_evidence_status: SemanticValue
    valuation_execution_status: SemanticValue
    core_contradiction: str | None = None
    sections: list[str] = Field(default_factory=list)
    presentation_version: str = "semantic-report@1.0.0"


class DecisionSummaryPresenter:
    """Translate canonical machine semantics without recalculating research state."""

    version = "semantic-report@1.0.0"
    _SUPPORTED_LOCALE = "zh-CN"

    _SEMANTICS: dict[str, dict[str, tuple[str, str]]] = {
        "module_status": {
            "PASS": ("通过", "本模块已满足当前研究流程要求。"),
            "FAIL": ("未通过", "本模块存在阻断研究流程的错误或一致性问题。"),
            "INSUFFICIENT_EVIDENCE": ("证据不足", "当前证据不足以形成该模块要求的可靠结论。"),
            "NOT_APPLICABLE": ("不适用", "该模块在当前研究条件下不适用。"),
        },
        "final_status": {
            "COMPLETE": ("研究流程完整", "当前研究已经满足 Research Completion Gate 的完成条件。"),
            "INCOMPLETE": ("研究流程未完成", "当前仍有一个或多个模块未满足 Research Completion Gate 的完成条件。"),
        },
        "business_model": {
            "manufacturing": ("制造业务", "公司主要通过生产制造活动创造经济价值。"),
            "distributor": ("分销业务", "公司主要通过采购、库存、销售与渠道周转创造经济价值。"),
            "hospitality": ("酒店与住宿服务", "公司主要通过酒店运营、住宿服务或相关管理输出创造经济价值。"),
            "software": ("软件与订阅业务", "公司主要通过软件、云服务或订阅模式创造经济价值。"),
            "consumer": ("消费与零售业务", "公司主要面向消费者提供品牌、零售或消费产品与服务。"),
            "resource": ("资源品业务", "公司主要依赖资源开采、加工或大宗商品经营创造经济价值。"),
            "project": ("项目制业务", "公司主要通过工程、系统集成或项目交付创造经济价值。"),
            "financial": ("金融业务", "公司主要通过金融资产、负债或金融服务创造经济价值。"),
            "unknown": ("业务模型尚未完成识别", "当前证据或现有业务模型分类体系不足以形成可靠分类。"),
        },
        "thesis_state": {
            "STRENGTHENING": ("投资逻辑增强", "新增证据正在增强核心投资逻辑。"),
            "ACTIVE": ("投资逻辑仍然成立", "现有证据尚未推翻核心投资逻辑。"),
            "WEAKENING": ("投资逻辑减弱", "新增证据正在削弱核心投资逻辑。"),
            "FALSIFIED": ("投资逻辑已被证伪", "关键反证已经触发，核心投资逻辑不再成立。"),
            "UNKNOWN": ("投资逻辑状态尚不明确", "当前没有足够结构化证据确定投资逻辑状态。"),
        },
        "fundamental_state": {
            "IMPROVING": ("基本面改善", "当前证据指向经营或资本效率正在改善。"),
            "STABLE": ("基本面稳定", "当前证据未显示基本面发生显著方向性变化。"),
            "DETERIORATING": ("基本面恶化", "当前证据指向经营或资本效率正在恶化。"),
            "UNCERTAIN": ("基本面方向尚不确定", "现有证据不足以可靠判断基本面方向。"),
        },
        "expectation_state": {
            "UNDER_EXPECTED": ("低于市场预期", "实际或前瞻证据低于已识别的市场预期。"),
            "IN_LINE": ("大致符合市场预期", "实际或前瞻证据与已识别市场预期大体一致。"),
            "OVER_EXPECTED": ("高于市场预期", "实际或前瞻证据高于已识别的市场预期。"),
            "MIXED": ("市场预期信号混合", "不同预期证据方向不一致，暂不形成单一方向判断。"),
        },
        "valuation_state": {
            "CHEAP": ("估值偏低", "在当前适用估值模型与证据范围内，估值处于偏低状态。"),
            "FAIR": ("估值大致合理", "在当前适用估值模型与证据范围内，估值接近合理区间。"),
            "EXPENSIVE": ("估值偏高", "在当前适用估值模型与证据范围内，估值处于偏高状态。"),
            "UNRELIABLE": ("估值结果可靠性不足", "当前模型适用性、输入证据或估值执行不足以支持可靠估值判断。"),
        },
        "decision_state": {
            "HIGH_CONVICTION_WATCH": ("高确信度跟踪", "研究逻辑较强，但仍以持续验证为主。"),
            "ACCUMULATION_CANDIDATE": ("具备进一步配置研究价值", "当前研究状态支持进入更高优先级的配置评估，但不等同于自动交易信号。"),
            "WAIT_FOR_CONFIRMATION": ("等待进一步确认", "关键证据尚未充分，当前应等待后续验证事件。"),
            "HOLD_AND_MONITOR": ("继续持有研究结论并跟踪", "核心逻辑仍成立，但需要持续监测关键驱动与风险。"),
            "RISK_REVIEW": ("进入风险复核", "当前出现需要优先复核的重大风险或矛盾证据。"),
            "THESIS_BROKEN": ("核心投资逻辑已失效", "关键证伪条件已经触发。"),
            "INSUFFICIENT_EVIDENCE": ("证据不足，暂不形成研究决策", "当前证据不足以形成可靠研究决策状态。"),
        },
        "reason": {
            "HIGH_IWCR": ("营运资金占用增速偏高", "新增营运资金占用相对收入增量偏高，需要关注增长质量与现金转换。"),
            "DEBT_FUNDS_NWC": ("新增债务主要支持营运资金", "营运资金扩张主要依赖新增债务融资，需要关注融资成本与偿债压力。"),
            "NEGATIVE_OCF": ("经营现金流为负", "经营活动产生的现金流为负，需要核查应收、存货及经营性负债变化。"),
            "EQUITY_DILUTION": ("存在股权融资稀释", "增长或营运资金需求部分依赖新增股权资本，需关注股东稀释。"),
        },
    }

    _MODULE_NAMES = {
        "Repository Preflight": "仓库与研究基线预检",
        "PIT Validation": "时点一致性校验",
        "Evidence Lineage": "证据来源与血缘",
        "Financial Sanity": "财务一致性检查",
        "Business Model Router": "业务模型识别",
        "KPI Pack": "关键经营指标",
        "Capital Efficiency": "资本效率",
        "Funding Loop": "融资与营运资金循环",
        "Driver Graph": "核心驱动关系",
        "Thesis": "核心投资逻辑",
        "Anti-Thesis": "反向投资逻辑",
        "Falsifiers": "证伪条件",
        "Expectation Evidence": "市场预期证据",
        "Forecast Discipline": "预测纪律",
        "Valuation Fitness": "估值模型适用性",
        "Valuation Execution": "估值执行",
        "Decision State": "研究决策状态",
        "Next Verification Event": "下一验证事件",
        "Temporal Consistency": "时间一致性",
    }

    _SECTION_NAMES = {
        "Decision": "研究决策",
        "Drivers": "核心驱动",
        "FinancialCapital": "财务与资本",
        "ExpectationsForecast": "市场预期与预测",
        "Valuation": "估值",
        "Evidence": "证据",
    }

    @staticmethod
    def _looks_like_machine_code(value: str) -> bool:
        return bool(re.fullmatch(r"[A-Z][A-Z0-9_]*", value))

    def semantic(self, code, *, category: str) -> SemanticValue:
        raw = "" if code is None else str(code)
        entry = self._SEMANTICS.get(category, {}).get(raw)
        if entry is not None:
            return SemanticValue(label=entry[0], explanation=entry[1], code=raw)

        if category == "reason" and raw and not self._looks_like_machine_code(raw):
            return SemanticValue(
                label=raw,
                explanation="该风险说明来自规范化研究结果，当前按原始可读文本展示。",
                code=raw,
            )

        return SemanticValue(
            label="存在尚未配置中文说明的研究状态",
            explanation="当前版本尚未为该内部状态配置中文解释；原始代码仅作为技术元数据保留。",
            code=raw,
        )

    def _module_name(self, name: str) -> str:
        return self._MODULE_NAMES.get(name, "其他研究模块（中文名称尚未配置）")

    def _section_name(self, name: str) -> str:
        return self._SECTION_NAMES.get(name, "其他研究章节（中文名称尚未配置）")

    def present(
        self,
        summary: DecisionSummary,
        locale: str = _SUPPORTED_LOCALE,
    ) -> HumanReadableDecisionSummary:
        if locale != self._SUPPORTED_LOCALE:
            raise ValueError(f"unsupported presentation locale: {locale}")
        if not isinstance(summary, DecisionSummary):
            raise TypeError("DecisionSummaryPresenter.present requires DecisionSummary")

        translated_statuses = {
            self._module_name(module): self.semantic(status, category="module_status")
            for module, status in summary.module_statuses.items()
        }
        return HumanReadableDecisionSummary(
            company_id=summary.company_id,
            business_model=self.semantic(summary.business_model, category="business_model"),
            primary_thesis=summary.primary_thesis,
            thesis_state=self.semantic(summary.thesis_state, category="thesis_state"),
            fundamental_state=self.semantic(summary.fundamental_state, category="fundamental_state"),
            expectation_state=self.semantic(summary.expectation_state, category="expectation_state"),
            valuation_state=self.semantic(summary.valuation_state, category="valuation_state"),
            evidence_confidence=summary.evidence_confidence,
            top_drivers=list(summary.top_drivers),
            top_risks=[self.semantic(item, category="reason") for item in summary.top_risks],
            next_verification_event=summary.next_verification_event,
            research_os_version=summary.research_os_version,
            decision_state=(
                self.semantic(summary.decision_state, category="decision_state")
                if summary.decision_state is not None
                else None
            ),
            final_status=self.semantic(summary.final_status, category="final_status"),
            blocking_modules=[self._module_name(item) for item in summary.blocking_modules],
            module_statuses=translated_statuses,
            expectation_evidence_status=self.semantic(
                summary.expectation_evidence_status,
                category="module_status",
            ),
            valuation_execution_status=self.semantic(
                summary.valuation_execution_status,
                category="module_status",
            ),
            core_contradiction=summary.core_contradiction,
            sections=[self._section_name(item) for item in summary.sections],
            presentation_version=self.version,
        )

    def build(
        self,
        result: ResearchRunResult,
        locale: str = _SUPPORTED_LOCALE,
    ) -> HumanReadableDecisionSummary:
        if not isinstance(result, ResearchRunResult):
            raise TypeError("DecisionSummaryPresenter.build requires ResearchRunResult")
        canonical = DecisionSummaryBuilder().build(result)
        return self.present(canonical, locale=locale)
