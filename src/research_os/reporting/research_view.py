from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from research_os.reporting.semantics import (
    DecisionSummaryPresenter,
    HumanReadableDecisionSummary,
    SemanticValue,
)
from research_os.runtime.result import ResearchRunResult


class HumanReadablePluginSelection(BaseModel):
    model_config = ConfigDict(frozen=True)
    label: str
    explanation: str
    plugin_id: str
    plugin_version: str
    plugin_type: str


class HumanReadableCoverageGap(BaseModel):
    model_config = ConfigDict(frozen=True)
    gap_type: SemanticValue
    business_model: SemanticValue | None = None
    reason: SemanticValue
    affected_capabilities: list[str] = Field(default_factory=list)
    fallback_available: bool | None = None
    missing_capability: str | None = None


class HumanReadableReportContribution(BaseModel):
    model_config = ConfigDict(frozen=True)
    contribution_id: str
    section: str
    title: str
    description: str
    research_questions: list[str] = Field(default_factory=list)


class HumanReadableMetric(BaseModel):
    model_config = ConfigDict(frozen=True)
    metric_id: str
    label: str
    explanation: str
    value: Any = None
    status: SemanticValue
    reason: SemanticValue | None = None
    formula_version: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class HumanReadableFundingLoop(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: SemanticValue
    reasons: list[SemanticValue] = Field(default_factory=list)
    incremental_revenue: float | None = None
    incremental_nwc: float | None = None
    incremental_debt: float | None = None
    incremental_equity: float | None = None
    operating_cash_flow: float | None = None


class HumanReadableDriverNode(BaseModel):
    model_config = ConfigDict(frozen=True)
    driver_id: str
    label: str
    explanation: str
    critical: bool = False
    evidence_ids: list[str] = Field(default_factory=list)


class HumanReadableDriverEdge(BaseModel):
    model_config = ConfigDict(frozen=True)
    from_driver: str
    from_label: str
    to_driver: str
    to_label: str
    relation: SemanticValue


class HumanReadableDriverGraph(BaseModel):
    model_config = ConfigDict(frozen=True)
    coverage: SemanticValue
    coverage_limited: bool = False
    coverage_reason: str | None = None
    nodes: list[HumanReadableDriverNode] = Field(default_factory=list)
    edges: list[HumanReadableDriverEdge] = Field(default_factory=list)


class HumanReadableFalsifier(BaseModel):
    model_config = ConfigDict(frozen=True)
    metric: str
    metric_label: str
    operator: str
    threshold: float
    explanation: str


class HumanReadableThesis(BaseModel):
    model_config = ConfigDict(frozen=True)
    title: str
    statement: str
    mechanism: str
    anti_thesis: str
    status: SemanticValue
    falsifiers: list[HumanReadableFalsifier] = Field(default_factory=list)
    confidence: float | None = None
    next_check_date: str | None = None


class HumanReadableExpectationQuality(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: SemanticValue
    reasons: list[SemanticValue] = Field(default_factory=list)
    source_count: int | None = None
    source_quality: float | None = None
    age_days: int | None = None


class HumanReadableValuationModel(BaseModel):
    model_config = ConfigDict(frozen=True)
    model_id: str
    label: str
    explanation: str
    score: float
    status: SemanticValue


class HumanReadableResearchView(BaseModel):
    model_config = ConfigDict(frozen=True)
    company_id: str
    decision_ts: datetime
    repository: str
    commit_sha: str
    research_os_version: str
    core_api_version: str
    business_model: SemanticValue
    classification_status: SemanticValue
    classification_reason: SemanticValue | None = None
    secondary_business_models: list[SemanticValue] = Field(default_factory=list)
    industry_plugins: list[HumanReadablePluginSelection] = Field(default_factory=list)
    methodology_plugins: list[HumanReadablePluginSelection] = Field(default_factory=list)
    coverage_gaps: list[HumanReadableCoverageGap] = Field(default_factory=list)
    report_contributions: list[HumanReadableReportContribution] = Field(default_factory=list)
    kpi_metrics: list[HumanReadableMetric] = Field(default_factory=list)
    funding_loop: HumanReadableFundingLoop | None = None
    driver_graph: HumanReadableDriverGraph | None = None
    theses: list[HumanReadableThesis] = Field(default_factory=list)
    expectation_quality: HumanReadableExpectationQuality | None = None
    valuation_models: list[HumanReadableValuationModel] = Field(default_factory=list)
    decision_summary: HumanReadableDecisionSummary
    presentation_version: str = "semantic-research-view@1.0.0"


class ResearchViewPresenter:
    """One-way human-readable projection of one canonical ResearchRunResult."""

    version = "semantic-research-view@1.0.0"
    _SUPPORTED_LOCALE = "zh-CN"

    _CLASSIFICATION = {
        "classified": ("业务模型已识别", "现有证据支持将公司归入当前业务模型分类。"),
        "unsupported_taxonomy": ("现有分类体系暂不能表示该业务", "业务描述具有有效信息，但当前业务模型分类体系无法可靠表示。"),
        "insufficient_evidence": ("业务模型识别证据不足", "当前可用证据不足以可靠识别主要业务模型。"),
    }
    _CLASSIFICATION_REASON = {
        "supported_business_model_signal": ("业务模型信号充分", "业务描述或适用的财务特征支持当前分类。"),
        "no_supported_business_model_match": ("现有分类体系未匹配", "有效业务描述未能匹配当前支持的业务模型分类。"),
        "no_usable_business_model_evidence": ("缺少可用业务模型证据", "没有足够的业务描述或其他可靠分类证据。"),
    }
    _GAP_TYPES = {
        "industry_strategy": ("缺少专业行业策略覆盖", "业务模型已识别，但当前版本没有兼容的专业行业策略插件。"),
        "methodology": ("缺少研究方法覆盖", "明确请求的研究方法当前无法满足。"),
        "capability": ("缺少研究能力", "当前运行缺少完成该专业问题所需的研究能力。"),
        "business_model_taxonomy": ("业务模型分类体系存在缺口", "有效业务描述无法由当前标准业务模型分类体系表示。"),
        "business_model_evidence": ("业务模型识别证据不足", "现有证据不足以可靠识别公司的主要业务模型。"),
    }
    _GAP_REASONS = {
        "NO_COMPATIBLE_INDUSTRY_PLUGIN": ("当前版本缺少兼容的行业策略插件", "已识别主要业务模型，但当前版本没有可用于该模型的专业行业策略插件。"),
        "UNSUPPORTED_BUSINESS_MODEL_TAXONOMY": ("当前分类体系无法表示该业务", "业务描述有效，但现有标准分类体系尚未覆盖该业务模型。"),
        "INSUFFICIENT_BUSINESS_MODEL_EVIDENCE": ("业务模型证据不足", "当前可用证据不足以支持可靠的业务模型判断。"),
    }
    _PLUGINS = {
        "industry:manufacturing": ("制造业策略插件", "提供制造业务的通用经营指标与研究结构。"),
        "industry:distributor": ("分销业务策略插件", "提供分销业务的营运资金、周转和融资质量研究结构。"),
    }
    _CAPABILITIES = {
        "industry_strategy": "专业行业策略",
        "business_model.profile": "业务模型识别",
        "kpi.metrics": "关键经营指标",
    }
    _METRICS = {
        "roe": ("净资产收益率", "衡量股东权益产生利润的效率。"),
        "net_margin": ("归母净利率", "衡量收入转化为归母净利润的比例。"),
        "asset_turnover": ("资产周转率", "衡量资产支持收入创造的效率。"),
        "equity_multiplier": ("权益乘数", "反映资产相对股东权益的杠杆程度。"),
        "cash_conversion_parent": ("归母利润现金转化率", "比较经营现金流与归母净利润。"),
        "ar_days": ("应收账款周转天数", "衡量制造业务收入转化为应收回款所占用的期间天数。"),
        "inventory_days": ("存货周转天数", "衡量制造业务存货占用的期间天数。"),
        "simple_fcf": ("简化自由现金流", "经营现金流扣除资本开支现金支出的简化结果。"),
        "fixed_asset_turnover": ("固定资产周转率", "衡量固定资产支持收入创造的效率。"),
        "capex_intensity": ("资本开支强度", "资本开支现金支出占收入的比例。"),
        "dso_days": ("应收账款周转天数", "衡量分销收入形成应收账款后的回收速度。"),
        "dio_days": ("存货周转天数", "衡量分销库存的资金占用时长。"),
        "dpo_days": ("应付账款周转天数", "衡量供应商信用对营运资金的支持时长。"),
        "ccc_days": ("现金转换周期", "综合应收、存货和应付后的营运资金现金占用周期。"),
        "inventory_turns": ("期间存货周转次数", "报告期内销售成本相对平均存货的周转次数。"),
        "inventory_turns_period": ("期间存货周转次数", "报告期内销售成本相对平均存货的周转次数。"),
        "inventory_turns_annualized": ("年化存货周转次数", "按真实报告期长度折算后的年化存货周转次数。"),
        "nwc_intensity": ("净营运资金强度", "应收加存货减应付相对收入的资金占用比例。"),
        "gross_profit_to_working_capital": ("毛利对营运资金覆盖", "衡量毛利相对营运资金占用的经济回报。"),
        "incremental_nwc_intensity": ("增量营运资金强度", "新增营运资金占新增收入的比例。"),
        "short_debt_to_inventory": ("短期债务对存货比", "衡量短期债务相对库存规模的融资压力。"),
        "short_debt_to_equity": ("短期债务对权益比", "衡量短期债务相对股东权益的杠杆程度。"),
        "interest_to_gross_profit": ("利息费用对毛利比", "衡量融资成本对毛利空间的侵蚀程度。"),
        "credit_impairment_to_gross_profit": ("信用减值对毛利比", "衡量信用损失对毛利的侵蚀程度。"),
        "inventory_impairment_to_gross_profit": ("存货减值对毛利比", "衡量存货跌价损失对毛利的侵蚀程度。"),
        "cash_conversion": ("利润现金转化率", "比较经营现金流与净利润，观察利润的现金质量。"),
        "revenue_growth_vs_working_capital_growth": ("收入与营运资金增速差", "比较收入增长与营运资金增长的相对速度。"),
        "funding_loop_debt_share": ("营运资金增量的债务融资占比", "衡量新增债务对新增营运资金的覆盖程度。"),
        "funding_loop_external_share": ("营运资金增量的外部融资占比", "衡量债务与股权外部融资对新增营运资金的覆盖程度。"),
        "roic": ("投入资本回报率", "衡量投入资本产生税后经营利润的效率。"),
        "incremental_roic": ("增量投入资本回报率", "衡量新增投入资本带来的新增经营回报。"),
    }
    _METRIC_STATUS = {
        "valid": ("指标有效", "当前输入证据足以计算该指标。"),
        "missing": ("指标缺失", "当前输入证据不足以可靠计算该指标。"),
    }
    _METRIC_REASONS = {
        "PERIOD_LENGTH_REQUIRED": ("缺少报告期长度", "该期间敏感指标需要明确的报告期长度，当前不会默认使用365天。"),
    }
    _FUNDING_STATES = {
        "unknown": ("融资循环状态尚不明确", "当前证据不足以可靠判断营运资金的融资方式。"),
        "self_funded": ("内部现金自我支持", "当前营运资金需求主要由经营现金流支持，未依赖新增外部融资。"),
        "mixed": ("混合融资", "营运资金需求由经营现金流与外部融资共同支持。"),
        "equity_funded": ("股权融资驱动", "营运资金扩张主要依赖新增股权资本。"),
        "debt_funded": ("债务融资驱动", "营运资金扩张主要依赖新增债务融资。"),
        "stressed": ("融资循环承压", "经营现金流为负且债务融资对营运资金扩张的依赖较高。"),
    }
    _DRIVERS = {
        "demand": ("需求", "终端需求与订单活动。"),
        "revenue": ("收入", "收入规模及其增长变化。"),
        "gross_margin": ("毛利率", "产品结构、价格与成本共同决定的毛利水平。"),
        "ar": ("应收账款", "客户信用与回款形成的资金占用。"),
        "inventory": ("存货", "库存与备货形成的资金占用。"),
        "ap": ("应付账款", "供应商信用对营运资金的支持。"),
        "nwc": ("净营运资金", "应收、存货与应付共同形成的经营资金占用。"),
        "debt": ("短期债务", "为经营和营运资金提供的短期债务融资。"),
        "interest": ("利息费用", "债务融资产生的财务成本。"),
        "net_profit": ("净利润", "经营与融资因素共同形成的最终利润。"),
        "ocf": ("经营现金流", "经营活动形成或消耗的现金。"),
        "margin": ("利润率", "收入转化为利润的经营效率。"),
        "fcf": ("自由现金流", "经营现金流扣除必要资本投入后的现金创造能力。"),
    }
    _RELATIONS = {
        "positive": ("正向关系", "前项上升通常推动后项上升，其他条件不变。"),
        "negative": ("反向关系", "前项上升通常压低后项，其他条件不变。"),
        "nonlinear": ("非线性关系", "两项之间存在非线性的响应关系。"),
        "conditional": ("条件关系", "两项关系依赖特定经营或市场条件。"),
    }
    _GRAPH_COVERAGE = {
        "specialized": ("专业驱动覆盖", "驱动图由已匹配的专业行业策略支持。"),
        "generic": ("通用驱动，仅供信息参考", "当前缺少专业行业策略覆盖，驱动图只用于保持通用因果结构，不代表完整行业研究。"),
    }
    _EXPECTATION_QUALITY = {
        "ADEQUATE": ("市场预期证据质量基本充分", "覆盖数量、来源质量与时效性未触发当前质量警示。"),
        "LOW": ("市场预期证据质量偏低", "覆盖数量、来源质量或时效性至少一项存在明显限制。"),
        "UNKNOWN": ("市场预期证据质量尚不明确", "缺少足够元数据评估市场预期证据质量。"),
    }
    _EXPECTATION_REASONS = {
        "THIN_CONSENSUS": ("覆盖机构数量较少", "当前参与市场预期的独立来源少于3个，应降低对一致预期代表性的确信度。"),
        "LOW_SOURCE_QUALITY": ("预期来源质量偏低", "当前来源质量评分低于既定最低质量阈值。"),
        "STALE_CONSENSUS": ("预期数据距离决策时点较久", "市场预期快照距离决策时点超过90天，可能未吸收最新经营信息。"),
        "CONSENSUS_METADATA_MISSING": ("市场预期质量元数据不完整", "缺少覆盖数量或来源质量信息，无法完整评估一致预期质量。"),
        "NO_CONSENSUS_VINTAGE": ("缺少可用市场预期快照", "截至决策时点没有可用于质量评估的市场预期快照。"),
    }
    _VALUATION_MODELS = {
        "pe": ("市盈率（PE）", "以盈利与可比估值倍数衡量股权价值。"),
        "pb": ("市净率（PB）", "以净资产与可比估值倍数衡量股权价值。"),
        "ev_ebitda": ("企业价值/EBITDA", "以企业价值相对经营利润代理指标进行估值。"),
        "dcf": ("现金流折现（DCF）", "以未来现金流折现衡量企业内在价值。"),
        "sotp": ("分部估值（SOTP）", "分别估值不同业务后汇总企业价值。"),
    }
    _VALUATION_ROUTES = {
        "PRIMARY": ("主要估值方法", "该模型在当前证据和业务条件下属于主要估值方法。"),
        "SECONDARY": ("辅助估值方法", "该模型适合作为主要估值方法的辅助验证。"),
        "SANITY_CHECK": ("估值合理性校验", "该模型仅用于检查主要估值结果是否明显失真。"),
        "LOW_CONFIDENCE": ("低置信度估值参考", "该模型适用性较低，只能作为低置信度参考。"),
        "NOT_APPLICABLE": ("当前不适用", "该估值模型在当前业务和证据条件下不适用。"),
    }
    _CONTRIBUTIONS = {
        "manufacturing.operating_engine": (
            "制造经营引擎",
            "把生产经营、产能投放和产品结构与利润率及现金创造联系起来。",
            ["订单、在手任务和客户验收节奏如何变化？", "产能、利用率、良率和产品结构如何变化？", "原材料或资格认证约束是否压制利润率修复？"],
        ),
        "manufacturing.capital_cycle": (
            "制造资本循环",
            "评估营运资金现金转化、资本开支强度和制造资产产生的回报。",
            ["营运资金是否转化为经营现金？", "资本开支是否形成有效产能和资本回报？", "应收或存货是否持续快于经营活动增长？"],
        ),
        "distributor.working_capital": (
            "分销营运资金引擎",
            "把应收、存货和应付与现金转换和增长质量联系起来。",
            ["应收和存货是否快于收入增长？", "应收、存货、应付及现金转换周期如何变化？", "毛利是否足以补偿营运资金占用？"],
        ),
        "distributor.financing_quality": (
            "分销融资质量",
            "评估营运资金扩张依赖内部现金、债务、保理或其他外部融资的程度。",
            ["新增营运资金中有多少由债务支持？", "融资成本相对毛利有多高？", "利润对存货或信用减值有多敏感？"],
        ),
    }
    _SECTIONS = {
        "Industry / Competitive Context": "行业与竞争环境",
        "Capital Efficiency & Funding Loop": "资本效率与融资循环",
        "Financial Quality": "财务质量",
    }
    _THESIS_TEXT = {
        "Growth converts to cash": "增长转化为现金",
        "Growth should improve cash generation rather than depend indefinitely on external funding.": "收入增长应改善现金创造能力，而不能长期依赖外部融资。",
        "Revenue growth must translate through working-capital efficiency into operating cash flow.": "收入增长必须通过营运资金效率改善，最终转化为经营现金流。",
        "Growth remains dependent on inventory, receivables and external financing, so cash quality deteriorates.": "增长持续依赖存货、应收和外部融资，导致现金质量恶化。",
        "Fundamentals improve": "基本面改善",
        "Operating fundamentals improve.": "经营基本面改善。",
        "Revenue and margins translate into cash.": "收入和利润率改善能够转化为现金。",
        "Reported growth fails to convert into sustainable cash returns.": "账面增长未能转化为可持续的现金回报。",
    }

    def __init__(self):
        self._decision = DecisionSummaryPresenter()

    @staticmethod
    def _get(value: Any, field: str, default=None):
        if value is None:
            return default
        if isinstance(value, dict):
            return value.get(field, default)
        return getattr(value, field, default)

    @staticmethod
    def _semantic(code: Any, table: dict[str, tuple[str, str]], fallback: str) -> SemanticValue:
        raw = "" if code is None else str(code)
        entry = table.get(raw)
        if entry is not None:
            return SemanticValue(label=entry[0], explanation=entry[1], code=raw)
        return SemanticValue(
            label=fallback,
            explanation="当前版本尚未为该内部状态配置专门中文说明；原始值仅作为技术元数据保留。",
            code=raw,
        )

    def _business_model(self, model: Any) -> SemanticValue:
        return self._decision.semantic(model, category="business_model")

    def _plugin(self, item) -> HumanReadablePluginSelection:
        plugin_id = str(self._get(item, "plugin_id", ""))
        entry = self._PLUGINS.get(plugin_id)
        if entry is None:
            label = "扩展研究插件"
            explanation = "该插件来自可扩展研究插件体系；当前中文名称尚未单独配置。"
        else:
            label, explanation = entry
        return HumanReadablePluginSelection(
            label=label,
            explanation=explanation,
            plugin_id=plugin_id,
            plugin_version=str(self._get(item, "plugin_version", "")),
            plugin_type=str(self._get(item, "plugin_type", "")),
        )

    def _gap(self, gap) -> HumanReadableCoverageGap:
        gap_type = str(self._get(gap, "gap_type", ""))
        reason_code = self._get(gap, "reason_code")
        reason_text = str(self._get(gap, "reason", "") or "")
        if reason_code in self._GAP_REASONS:
            reason = self._semantic(reason_code, self._GAP_REASONS, "研究覆盖存在限制")
        elif reason_text:
            reason = SemanticValue(
                label="研究覆盖存在限制",
                explanation=reason_text,
                code=str(reason_code or reason_text),
            )
        else:
            reason = SemanticValue(
                label="研究覆盖存在限制",
                explanation="当前研究存在未进一步说明的覆盖限制。",
                code=str(reason_code or ""),
            )
        model = self._get(gap, "business_model")
        return HumanReadableCoverageGap(
            gap_type=self._semantic(gap_type, self._GAP_TYPES, "研究覆盖缺口"),
            business_model=self._business_model(model) if model else None,
            reason=reason,
            affected_capabilities=[
                self._CAPABILITIES.get(str(item), "其他研究能力")
                for item in list(self._get(gap, "affected_capabilities", []) or [])
            ],
            fallback_available=self._get(gap, "fallback_available"),
            missing_capability=self._get(gap, "missing_capability"),
        )

    def _contribution(self, item) -> HumanReadableReportContribution:
        contribution_id = str(self._get(item, "contribution_id", ""))
        mapped = self._CONTRIBUTIONS.get(contribution_id)
        if mapped is not None:
            title, description, questions = mapped
        else:
            title = str(self._get(item, "title", "") or "研究贡献")
            description = str(self._get(item, "description", "") or "该扩展提供结构化研究信息。")
            questions = list(self._get(item, "research_questions", []) or [])
        return HumanReadableReportContribution(
            contribution_id=contribution_id,
            section=self._SECTIONS.get(str(self._get(item, "section", "")), "其他研究章节"),
            title=title,
            description=description,
            research_questions=questions,
        )

    def _metric(self, item) -> HumanReadableMetric:
        metric_id = str(self._get(item, "metric_id", ""))
        metric = self._METRICS.get(metric_id)
        if metric is None:
            label, explanation = "其他研究指标", "当前版本尚未为该扩展指标配置专门中文说明。"
        else:
            label, explanation = metric
        reason_code = self._get(item, "reason_code")
        return HumanReadableMetric(
            metric_id=metric_id,
            label=label,
            explanation=explanation,
            value=self._get(item, "value"),
            status=self._semantic(
                self._get(item, "status", ""),
                self._METRIC_STATUS,
                "指标状态尚未配置中文说明",
            ),
            reason=(
                self._semantic(reason_code, self._METRIC_REASONS, "指标缺失原因尚未配置中文说明")
                if reason_code
                else None
            ),
            formula_version=self._get(item, "formula_version"),
            evidence_ids=list(self._get(item, "evidence_ids", []) or []),
        )

    def _funding(self, funding) -> HumanReadableFundingLoop | None:
        if funding is None:
            return None
        return HumanReadableFundingLoop(
            state=self._semantic(
                self._get(funding, "funding_state", "unknown"),
                self._FUNDING_STATES,
                "融资循环状态尚未配置中文说明",
            ),
            reasons=[
                self._decision.semantic(item, category="reason")
                for item in list(self._get(funding, "reason_codes", []) or [])
            ],
            incremental_revenue=self._get(funding, "incremental_revenue"),
            incremental_nwc=self._get(funding, "incremental_nwc"),
            incremental_debt=self._get(funding, "incremental_debt"),
            incremental_equity=self._get(funding, "incremental_equity"),
            operating_cash_flow=self._get(funding, "operating_cash_flow"),
        )

    def _driver_label(self, driver_id: str, fallback_name: str = "") -> tuple[str, str]:
        item = self._DRIVERS.get(driver_id)
        if item is not None:
            return item
        if fallback_name and not re.fullmatch(r"[A-Z][A-Z0-9_]*", fallback_name):
            return fallback_name, "该驱动来自规范化研究结果，按原始可读名称展示。"
        return "其他经营驱动", "当前版本尚未为该扩展驱动配置专门中文说明。"

    def _driver_graph(self, graph) -> HumanReadableDriverGraph | None:
        if graph is None:
            return None
        nodes = []
        labels: dict[str, str] = {}
        for node in list(self._get(graph, "nodes", []) or []):
            driver_id = str(self._get(node, "driver_id", ""))
            label, explanation = self._driver_label(driver_id, str(self._get(node, "name", "")))
            labels[driver_id] = label
            nodes.append(
                HumanReadableDriverNode(
                    driver_id=driver_id,
                    label=label,
                    explanation=explanation,
                    critical=bool(self._get(node, "critical", False)),
                    evidence_ids=list(self._get(node, "evidence_ids", []) or []),
                )
            )
        edges = []
        for edge in list(self._get(graph, "edges", []) or []):
            from_id = str(self._get(edge, "from_driver", ""))
            to_id = str(self._get(edge, "to_driver", ""))
            edges.append(
                HumanReadableDriverEdge(
                    from_driver=from_id,
                    from_label=labels.get(from_id, self._driver_label(from_id)[0]),
                    to_driver=to_id,
                    to_label=labels.get(to_id, self._driver_label(to_id)[0]),
                    relation=self._semantic(
                        self._get(edge, "relation", ""),
                        self._RELATIONS,
                        "驱动关系尚未配置中文说明",
                    ),
                )
            )
        scope = str(self._get(graph, "coverage_scope", "specialized"))
        reason = self._get(graph, "coverage_reason")
        if reason == "primary industry strategy coverage is unavailable; generic drivers are informational fallback only":
            reason = "主要业务模型缺少专业行业策略覆盖；当前通用驱动图仅用于信息参考。"
        return HumanReadableDriverGraph(
            coverage=self._semantic(scope, self._GRAPH_COVERAGE, "驱动覆盖状态尚未配置中文说明"),
            coverage_limited=bool(self._get(graph, "coverage_limited", False)),
            coverage_reason=reason,
            nodes=nodes,
            edges=edges,
        )

    def _falsifier(self, item) -> HumanReadableFalsifier:
        metric = str(self._get(item, "metric", ""))
        metric_label = {
            "cfo": "经营现金流",
            "ocf": "经营现金流",
            "ccc_days": "现金转换周期",
        }.get(metric, "其他验证指标")
        operator = str(self._get(item, "operator", ""))
        threshold = float(self._get(item, "threshold", 0.0))
        return HumanReadableFalsifier(
            metric=metric,
            metric_label=metric_label,
            operator=operator,
            threshold=threshold,
            explanation=f"当{metric_label}{operator}{threshold:g}时，触发该证伪条件。",
        )

    def _translate_thesis_text(self, value: Any) -> str:
        text = "" if value is None else str(value)
        return self._THESIS_TEXT.get(text, text)

    def _thesis(self, item) -> HumanReadableThesis:
        status = str(self._get(item, "status", "UNKNOWN")).upper()
        return HumanReadableThesis(
            title=self._translate_thesis_text(self._get(item, "title", "")),
            statement=self._translate_thesis_text(self._get(item, "statement", "")),
            mechanism=self._translate_thesis_text(self._get(item, "mechanism", "")),
            anti_thesis=self._translate_thesis_text(self._get(item, "anti_thesis", "")),
            status=self._decision.semantic(status, category="thesis_state"),
            falsifiers=[self._falsifier(f) for f in list(self._get(item, "falsifiers", []) or [])],
            confidence=self._get(item, "confidence"),
            next_check_date=(
                str(self._get(item, "next_check_date"))
                if self._get(item, "next_check_date") is not None
                else None
            ),
        )

    def _expectation_quality(self, item) -> HumanReadableExpectationQuality | None:
        if item is None:
            return None
        return HumanReadableExpectationQuality(
            state=self._semantic(
                self._get(item, "status", "UNKNOWN"),
                self._EXPECTATION_QUALITY,
                "市场预期证据质量状态尚未配置中文说明",
            ),
            reasons=[
                self._semantic(code, self._EXPECTATION_REASONS, "市场预期质量限制尚未配置中文说明")
                for code in list(self._get(item, "reason_codes", []) or [])
            ],
            source_count=self._get(item, "source_count"),
            source_quality=self._get(item, "source_quality"),
            age_days=self._get(item, "age_days"),
        )

    def _valuation_models(self, routing) -> list[HumanReadableValuationModel]:
        if routing is None:
            return []
        values = self._get(routing, "models", {}) or {}
        items = values.items() if isinstance(values, dict) else []
        result = []
        for model_id, model in items:
            identity = self._VALUATION_MODELS.get(str(model_id))
            if identity is None:
                label, explanation = "其他估值方法", "当前版本尚未为该扩展估值模型配置专门中文说明。"
            else:
                label, explanation = identity
            result.append(
                HumanReadableValuationModel(
                    model_id=str(model_id),
                    label=label,
                    explanation=explanation,
                    score=float(self._get(model, "score", 0.0)),
                    status=self._semantic(
                        self._get(model, "status", ""),
                        self._VALUATION_ROUTES,
                        "估值模型状态尚未配置中文说明",
                    ),
                )
            )
        return sorted(result, key=lambda item: item.score, reverse=True)

    def _decision_summary(self, result: ResearchRunResult) -> HumanReadableDecisionSummary:
        summary = self._decision.build(result, locale=self._SUPPORTED_LOCALE)
        translated_thesis = self._translate_thesis_text(summary.primary_thesis)
        translated_drivers = []
        for name in summary.top_drivers:
            matched = next(
                (value[0] for key, value in self._DRIVERS.items() if name in {key, value[0]}),
                None,
            )
            if matched is None:
                reverse = {
                    "Revenue": "收入",
                    "Gross Margin": "毛利率",
                    "Accounts Receivable": "应收账款",
                    "Inventory": "存货",
                    "Accounts Payable": "应付账款",
                    "Net Working Capital": "净营运资金",
                    "Short-term Debt": "短期债务",
                    "Operating Cash Flow": "经营现金流",
                    "Margin": "利润率",
                    "Free Cash Flow": "自由现金流",
                }
                matched = reverse.get(name, name)
            translated_drivers.append(matched)
        event = summary.next_verification_event
        if event.startswith("next check: "):
            event = "下一次验证日期：" + event.removeprefix("next check: ")
        elif event == "next material disclosure":
            event = "下一次重大信息披露"
        return summary.model_copy(
            update={
                "primary_thesis": translated_thesis,
                "top_drivers": translated_drivers,
                "next_verification_event": event,
            }
        )

    def build(
        self,
        result: ResearchRunResult,
        locale: str = _SUPPORTED_LOCALE,
    ) -> HumanReadableResearchView:
        if locale != self._SUPPORTED_LOCALE:
            raise ValueError(f"unsupported presentation locale: {locale}")
        if not isinstance(result, ResearchRunResult):
            raise TypeError("ResearchViewPresenter.build requires ResearchRunResult")

        profile = result.business_model
        resolution = result.strategy_resolution
        artifacts = result.artifacts
        classification_reason = profile.classification_reason
        return HumanReadableResearchView(
            company_id=result.company.company_id,
            decision_ts=result.decision_ts,
            repository=result.baseline.repository_full_name,
            commit_sha=result.baseline.commit_sha,
            research_os_version=result.baseline.research_os_version,
            core_api_version=result.baseline.core_api_version,
            business_model=self._business_model(profile.primary_model),
            classification_status=self._semantic(
                profile.classification_status,
                self._CLASSIFICATION,
                "业务模型识别状态尚未配置中文说明",
            ),
            classification_reason=(
                self._semantic(
                    classification_reason,
                    self._CLASSIFICATION_REASON,
                    "业务模型识别原因尚未配置中文说明",
                )
                if classification_reason
                else None
            ),
            secondary_business_models=[self._business_model(item) for item in profile.secondary_models],
            industry_plugins=[self._plugin(item) for item in resolution.industry_plugins],
            methodology_plugins=[self._plugin(item) for item in resolution.methodology_plugins],
            coverage_gaps=[self._gap(item) for item in resolution.coverage_gaps],
            report_contributions=[
                self._contribution(item)
                for item in list(artifacts.get("report.contributions", []) or [])
            ],
            kpi_metrics=[self._metric(item) for item in list(artifacts.get("kpi.metrics", []) or [])],
            funding_loop=self._funding(artifacts.get("capital.funding_loop")),
            driver_graph=self._driver_graph(artifacts.get("drivers.graph")),
            theses=[self._thesis(item) for item in list(artifacts.get("thesis.items", []) or [])],
            expectation_quality=self._expectation_quality(artifacts.get("expectation.quality")),
            valuation_models=self._valuation_models(artifacts.get("valuation.routing")),
            decision_summary=self._decision_summary(result),
            presentation_version=self.version,
        )
