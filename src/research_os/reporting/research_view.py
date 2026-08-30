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


class HumanReadableQuestionAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)
    question_id: str
    question: str
    status: SemanticValue
    answer: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    missing_evidence_keys: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)


class HumanReadableMetric(BaseModel):
    model_config = ConfigDict(frozen=True)
    metric_id: str
    label: str
    explanation: str
    value: Any = None
    formatted_value: str | None = None
    display_unit: str | None = None
    period_label: str | None = None
    period_days: int | None = None
    annualized: bool | None = None
    status: SemanticValue
    reason: SemanticValue | None = None
    formula_version: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class HumanReadableFundingLoop(BaseModel):
    model_config = ConfigDict(frozen=True)
    calculation_status: SemanticValue | None = None
    state: SemanticValue
    reasons: list[SemanticValue] = Field(default_factory=list)
    incremental_revenue: float | None = None
    incremental_nwc: float | None = None
    incremental_debt: float | None = None
    incremental_equity: float | None = None
    reported_equity_change: float | None = None
    operating_cash_flow: float | None = None
    factoring_balance: float | None = None
    derecognized_receivables: float | None = None
    receivable_transfer_balance: float | None = None
    other_working_capital_financing: float | None = None
    factoring_to_ar: float | None = None
    comparison_basis_status: SemanticValue | None = None
    comparison_basis_limitations: list[SemanticValue] = Field(default_factory=list)


class HumanReadableFinancialSanity(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: SemanticValue
    explanation: str


class HumanReadableCapitalEfficiency(BaseModel):
    model_config = ConfigDict(frozen=True)
    calculation_status: SemanticValue
    roic: float | None = None
    incremental_roic: float | None = None
    iwcr: float | None = None
    iwcr_limitation: SemanticValue | None = None


class HumanReadableForecastDiscipline(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: SemanticValue
    reason: str


class HumanReadableNextVerificationEvent(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_name: str
    event_time: datetime | None = None
    evidence_ids: list[str] = Field(default_factory=list)


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


class HumanReadableThesisSignalAssessment(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: SemanticValue
    positive_signals: list[str] = Field(default_factory=list)
    negative_signals: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class HumanReadableExpectationQuality(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: SemanticValue
    reasons: list[SemanticValue] = Field(default_factory=list)
    source_count: int | None = None
    source_quality: float | None = None
    age_days: int | None = None
    latest_material_event_ts: datetime | None = None
    latest_material_event_label: str | None = None
    post_event_consensus: bool | None = None


class HumanReadableValuationModel(BaseModel):
    model_config = ConfigDict(frozen=True)
    model_id: str
    label: str
    explanation: str
    score: float
    status: SemanticValue
    reasons: list[SemanticValue] = Field(default_factory=list)


class HumanReadableValuationExecution(BaseModel):
    model_config = ConfigDict(frozen=True)
    selected_model: str
    executed_model: str
    selection_reason: str
    scenario_logic: str
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    lineage: dict[str, list[str]] = Field(default_factory=dict)
    driver_bridge: list[str] = Field(default_factory=list)


class HumanReadableStateProvenance(BaseModel):
    model_config = ConfigDict(frozen=True)
    dimension: str
    state: SemanticValue
    source: SemanticValue
    evidence_ids: list[str] = Field(default_factory=list)
    method: str | None = None


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
    question_assessments: list[HumanReadableQuestionAssessment] = Field(default_factory=list)
    financial_sanity: HumanReadableFinancialSanity | None = None
    kpi_metrics: list[HumanReadableMetric] = Field(default_factory=list)
    capital_efficiency: HumanReadableCapitalEfficiency | None = None
    funding_loop: HumanReadableFundingLoop | None = None
    driver_graph: HumanReadableDriverGraph | None = None
    theses: list[HumanReadableThesis] = Field(default_factory=list)
    thesis_signal_assessment: HumanReadableThesisSignalAssessment | None = None
    expectation_quality: HumanReadableExpectationQuality | None = None
    forecast_discipline: HumanReadableForecastDiscipline | None = None
    valuation_models: list[HumanReadableValuationModel] = Field(default_factory=list)
    valuation_execution: HumanReadableValuationExecution | None = None
    state_provenance: list[HumanReadableStateProvenance] = Field(default_factory=list)
    next_verification_event: HumanReadableNextVerificationEvent | None = None
    decision_summary: HumanReadableDecisionSummary
    presentation_version: str = "professional-research-view@1.2.0"


class ResearchViewPresenter:
    """One-way human-readable projection of one canonical ResearchRunResult."""

    version = "professional-research-view@1.2.0"
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
        "industry:manufacturing": ("制造业策略插件", "提供制造业务的经营指标、资本循环和专业问题覆盖结构。"),
        "industry:distributor": ("分销业务策略插件", "提供分销业务的营运资金、周转和融资质量研究结构。"),
    }
    _CAPABILITIES = {
        "industry_strategy": "专业行业策略",
        "business_model.profile": "业务模型识别",
        "kpi.metrics": "关键经营指标",
        "manufacturing.orders": "制造订单与在手任务研究能力",
        "manufacturing.capacity": "制造产能与利用率研究能力",
        "manufacturing.constraints": "制造原料与认证约束研究能力",
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
        "interest_to_gross_profit": ("利息费用对毛利比", "衡量利息费用对毛利空间的侵蚀程度。"),
        "total_financing_cost_to_gross_profit": ("总融资成本对毛利比", "衡量已披露融资相关成本对毛利空间的侵蚀程度。"),
        "factoring_to_ar": ("保理暴露对应收比", "衡量已披露保理或终止确认应收相对期末应收账款规模。"),
        "working_capital_financing_to_gross_profit": ("营运资金融资暴露对毛利比", "衡量保理、应收转让等营运资金融资暴露相对毛利规模。"),
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
        "COMPARISON_BASIS_REQUIRED": ("缺少可比期间基准", "增量指标需要为分子和分母提供明确且一致的比较期间，当前不会混用未声明基准的增量。"),
        "COMPARISON_BASIS_MISMATCH": ("比较期间基准不一致", "增量指标的分子和分母来自不同比较期间，当前不会形成该比率。"),
    }
    _COMPARISON_STATUS = {
        "PASS": ("比较期间基准一致", "用于当前融资判断的增量事实具有一致的比较期间基准。"),
        "INSUFFICIENT_EVIDENCE": ("比较期间证据不足", "一个或多个增量事实缺少比较期间基准，或基准彼此不一致。"),
        "NOT_APPLICABLE": ("当前无增量比较", "当前融资结果没有使用需要比较期间基准的增量比率。"),
    }
    _FUNDING_STATES = {
        "unknown": ("融资循环状态尚不明确", "当前证据不足以可靠判断营运资金的融资方式。"),
        "self_funded": ("内部现金自我支持", "当前营运资金需求主要由经营现金流支持，未依赖新增外部融资。"),
        "mixed": ("混合融资", "营运资金需求由经营现金流与外部融资共同支持。"),
        "equity_funded": ("股权融资驱动", "营运资金扩张主要依赖新增股权资本。"),
        "debt_funded": ("债务融资驱动", "营运资金扩张主要依赖新增债务融资。"),
        "stressed": ("融资循环承压", "经营现金流为负且债务融资对营运资金扩张的依赖较高。"),
    }
    _FUNDING_REASONS = {
        "MATERIAL_FACTORING_EXPOSURE": ("保理或终止确认应收暴露较大", "已披露保理或终止确认应收相对期末应收规模具有重要性；该暴露不自动等同于债务。"),
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
        "interest": ("融资成本", "债务及其他融资安排产生的财务成本。"),
        "net_profit": ("净利润", "经营与融资因素共同形成的最终利润。"),
        "ocf": ("经营现金流", "经营活动形成或消耗的现金。"),
        "margin": ("利润率", "收入转化为利润的经营效率。"),
        "capex": ("资本开支", "为制造能力与长期资产投入的现金。"),
        "fcf": ("自由现金流", "经营现金流扣除必要资本投入后的现金创造能力。"),
    }
    _RELATIONS = {
        "positive": ("正向关系", "前项上升通常推动后项上升，其他条件不变。"),
        "negative": ("反向关系", "前项上升通常压低后项，其他条件不变。"),
        "nonlinear": ("非线性关系", "两项之间存在非线性的响应关系。"),
        "conditional": ("条件关系", "两项关系依赖特定经营或市场条件。"),
    }
    _GRAPH_COVERAGE = {
        "specialized": ("专业驱动覆盖", "驱动图由已匹配的行业策略支持，但仍只代表当前插件具备的能力范围。"),
        "generic": ("通用驱动，仅供信息参考", "当前缺少专业行业策略覆盖，驱动图只用于保持通用因果结构，不代表完整行业研究。"),
    }
    _EXPECTATION_QUALITY = {
        "ADEQUATE": ("市场预期证据质量基本充分", "覆盖数量、来源质量与信息新鲜度未触发当前质量警示。"),
        "LOW": ("市场预期证据质量偏低", "覆盖数量、来源质量、日历时效或重大事件相对时效至少一项存在明显限制。"),
        "UNKNOWN": ("市场预期证据质量尚不明确", "缺少足够元数据评估市场预期证据质量。"),
    }
    _EXPECTATION_REASONS = {
        "THIN_CONSENSUS": ("覆盖机构数量较少", "当前参与市场预期的独立来源少于3个，应降低对一致预期代表性的确信度。"),
        "LOW_SOURCE_QUALITY": ("预期来源质量偏低", "当前来源质量评分低于既定最低质量阈值。"),
        "STALE_CONSENSUS": ("预期数据距离决策时点较久", "市场预期快照距离决策时点超过90天，可能未吸收最新经营信息。"),
        "CONSENSUS_PREDATES_MATERIAL_EVENT": ("一致预期尚未吸收最新重大信息", "当前一致预期形成于最近一次重大财报或经营事件之前，应降低其作为当前市场预期基准的权重。"),
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
    _VALUATION_REASONS = {
        "CASH_FUNDING_RISK_PE_PENALTY": ("现金与融资风险限制PE适用性", "该分销业务的营运资金由债务驱动且经营现金流为负，PE不能作为主要估值方法。"),
    }
    _FORECAST_REASONS = {
        "no promoted forecast methodology": "当前没有通过样本外证据与基准检验后获准进入生产链的预测方法，因此不形成系统预测。",
    }
    _QUESTION_STATUS = {
        "ANSWERED": ("当前问题具备规范化覆盖", "所需能力和证据已经进入当前研究运行，可结合对应模块查看结论。"),
        "EVIDENCE_MISSING": ("当前问题缺少必要证据", "已有研究能力，但当前运行缺少回答该问题所需的一个或多个证据字段。"),
        "CAPABILITY_MISSING": ("当前问题缺少专业研究能力", "即使存在部分证据，当前版本仍缺少回答该专业问题所需的能力。"),
        "NOT_APPLICABLE": ("当前问题不适用", "该专业研究问题在当前业务或研究范围内不适用。"),
    }
    _SIGNAL_STATUS = {
        "SUPPORTED": ("方向性经营信号得到支持", "至少两个独立正向信号且没有重大反向矛盾支持当前方向判断。"),
        "MIXED": ("经营信号混合", "正向与反向经营证据同时存在，不应形成单向改善叙事。"),
        "INSUFFICIENT": ("方向性经营证据不足", "当前缺少足够独立方向性信号形成可靠经营趋势判断。"),
    }
    _STATE_SOURCES = {
        "derived": ("Research OS 推导", "该状态由当前 Research OS 模块根据规范化证据推导。"),
        "analyst_assumption": ("分析师输入假设", "该状态来自研究输入，Research OS 未把它重新表述为系统自行推导的结论。"),
        "external_model": ("外部模型输入", "该状态来自外部模型，并保留其方法和证据血缘。"),
        "manual_override": ("人工覆盖", "该状态由人工明确覆盖，需要结合覆盖原因和证据查看。"),
    }
    _MODULE_EXECUTION_STATUS = {
        "PASS": ("研究模块已完成计算", "该模块已经按当前输入完成规范化计算；这不表示公司经济状态健康。"),
        "FAIL": ("研究模块执行未通过", "该模块存在执行或一致性问题。"),
        "INSUFFICIENT_EVIDENCE": ("研究模块证据不足", "当前证据不足以完成该模块要求。"),
        "NOT_APPLICABLE": ("研究模块不适用", "该模块在当前研究条件下不适用。"),
    }
    _SECTIONS = {
        "Industry / Competitive Context": "行业与竞争环境",
        "Capital Efficiency & Funding Loop": "资本效率与融资循环",
        "Financial Quality": "财务质量",
    }
    _CONTRIBUTIONS = {
        "manufacturing.operating_engine": (
            "制造经营引擎",
            "把生产经济性、产能投放和产品结构与利润率及现金创造联系起来。",
        ),
        "manufacturing.capital_cycle": (
            "制造资本循环",
            "评估营运资金现金转化、资本开支强度和制造资产产生的回报。",
        ),
        "distributor.working_capital": (
            "分销营运资金引擎",
            "把应收、存货和应付与现金转换和增长质量联系起来。",
        ),
        "distributor.financing_quality": (
            "分销融资质量",
            "评估营运资金扩张依赖内部现金、债务、保理或其他外部融资的程度。",
        ),
    }
    _THESIS_TEXT = {
        "Growth converts to cash": "增长转化为现金",
        "Growth should improve cash generation rather than depend indefinitely on external funding.": "收入增长应改善现金创造能力，而不能长期依赖外部融资。",
        "Revenue growth must translate through working-capital efficiency into operating cash flow.": "收入增长必须通过营运资金效率改善，最终转化为经营现金流。",
        "Growth remains dependent on inventory, receivables and external financing, so cash quality deteriorates.": "增长持续依赖存货、应收和外部融资，导致现金质量恶化。",
        "Fundamentals improve": "基本面改善",
        "Operating fundamentals improve based on multiple directional signals.": "多个独立方向性信号共同支持经营基本面改善。",
        "Revenue, margin, capital-efficiency or cash signals consistently point toward improving operating quality.": "收入、利润率、资本效率或现金信号一致指向经营质量改善。",
        "The apparent improvement reverses or fails to convert into sustainable cash returns.": "表面改善出现逆转，或不能转化为可持续现金回报。",
        "Operating signals mixed": "经营信号混合",
        "Operating signals are mixed; wait for further confirmation before asserting directional improvement.": "经营信号存在分化，在宣称方向性改善前应等待进一步确认。",
        "Positive operating or cash signals are offset by contradictory margin or working-capital evidence.": "正向经营或现金信号被利润率或营运资金方面的反向证据抵消。",
        "The contradictory indicators resolve consistently in one direction and establish a reliable operating trend.": "相互矛盾的指标最终一致指向同一方向，并形成可靠经营趋势。",
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
        label, explanation = self._PLUGINS.get(
            plugin_id,
            ("扩展研究插件", "该插件来自可扩展研究插件体系；当前中文名称尚未单独配置。"),
        )
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
            reason = SemanticValue(label="研究覆盖存在限制", explanation=reason_text, code=str(reason_code or reason_text))
        else:
            reason = SemanticValue(label="研究覆盖存在限制", explanation="当前研究存在未进一步说明的覆盖限制。", code=str(reason_code or ""))
        model = self._get(gap, "business_model")
        return HumanReadableCoverageGap(
            gap_type=self._semantic(gap_type, self._GAP_TYPES, "研究覆盖缺口"),
            business_model=self._business_model(model) if model else None,
            reason=reason,
            affected_capabilities=[self._CAPABILITIES.get(str(item), "其他研究能力") for item in list(self._get(gap, "affected_capabilities", []) or [])],
            fallback_available=self._get(gap, "fallback_available"),
            missing_capability=self._get(gap, "missing_capability"),
        )

    def _contribution(self, item) -> HumanReadableReportContribution:
        contribution_id = str(self._get(item, "contribution_id", ""))
        mapped = self._CONTRIBUTIONS.get(contribution_id)
        title = mapped[0] if mapped else str(self._get(item, "title", "") or "研究贡献")
        description = mapped[1] if mapped else str(self._get(item, "description", "") or "该扩展提供结构化研究信息。")
        return HumanReadableReportContribution(
            contribution_id=contribution_id,
            section=self._SECTIONS.get(str(self._get(item, "section", "")), "其他研究章节"),
            title=title,
            description=description,
            research_questions=list(self._get(item, "research_questions", []) or []),
        )

    def _question(self, item) -> HumanReadableQuestionAssessment:
        return HumanReadableQuestionAssessment(
            question_id=str(self._get(item, "question_id", "")),
            question=str(self._get(item, "text", "")),
            status=self._semantic(self._get(item, "status", ""), self._QUESTION_STATUS, "专业问题覆盖状态尚未配置中文说明"),
            answer=self._get(item, "answer"),
            evidence_ids=list(self._get(item, "evidence_ids", []) or []),
            missing_evidence_keys=list(self._get(item, "missing_evidence_keys", []) or []),
            missing_capabilities=[self._CAPABILITIES.get(str(value), str(value)) for value in list(self._get(item, "missing_capabilities", []) or [])],
        )

    @staticmethod
    def _format_metric(value: Any, unit: str | None) -> tuple[str | None, str | None]:
        if value is None:
            return None, None
        if not isinstance(value, (int, float)):
            return str(value), unit
        if unit == "percent":
            return f"{value * 100:.2f}%", "%"
        if unit == "days":
            return f"{value:.2f}天", "天"
        if unit == "x":
            return f"{value:.2f}x", "x"
        if unit == "currency":
            return f"{value:,.2f}元", "元"
        return f"{value:.4g}", unit

    def _metric(self, item) -> HumanReadableMetric:
        metric_id = str(self._get(item, "metric_id", ""))
        label, explanation = self._METRICS.get(metric_id, ("其他研究指标", "当前版本尚未为该扩展指标配置专门中文说明。"))
        reason_code = self._get(item, "reason_code")
        value = self._get(item, "value")
        unit = self._get(item, "unit")
        formatted, display_unit = self._format_metric(value, unit)
        return HumanReadableMetric(
            metric_id=metric_id,
            label=label,
            explanation=explanation,
            value=value,
            formatted_value=formatted,
            display_unit=display_unit,
            period_label=self._get(item, "period_label"),
            period_days=self._get(item, "period_days"),
            annualized=self._get(item, "annualized"),
            status=self._semantic(self._get(item, "status", ""), self._METRIC_STATUS, "指标状态尚未配置中文说明"),
            reason=(self._semantic(reason_code, self._METRIC_REASONS, "指标缺失原因尚未配置中文说明") if reason_code else None),
            formula_version=self._get(item, "formula_version"),
            evidence_ids=list(self._get(item, "evidence_ids", []) or []),
        )

    def _financial_sanity(self, item, module_status: str | None) -> HumanReadableFinancialSanity | None:
        if item is None and module_status is None:
            return None
        status = module_status or self._get(item, "status", "INSUFFICIENT_EVIDENCE")
        return HumanReadableFinancialSanity(
            status=self._semantic(status, self._MODULE_EXECUTION_STATUS, "财务一致性校验状态尚未配置中文说明"),
            explanation="该状态仅表示财务口径、单位、比例与已声明关系的一致性校验结果，不代表经营状况健康。",
        )

    def _capital_efficiency(self, item, module_status: str | None) -> HumanReadableCapitalEfficiency | None:
        if item is None:
            return None
        limitation = self._get(item, "iwcr_reason_code")
        return HumanReadableCapitalEfficiency(
            calculation_status=self._semantic(
                module_status or "INSUFFICIENT_EVIDENCE",
                self._MODULE_EXECUTION_STATUS,
                "资本效率模块状态尚未配置中文说明",
            ),
            roic=self._get(item, "roic"),
            incremental_roic=self._get(item, "incremental_roic"),
            iwcr=self._get(item, "iwcr"),
            iwcr_limitation=(
                self._semantic(limitation, self._METRIC_REASONS, "增量营运资金指标限制尚未配置中文说明")
                if limitation
                else None
            ),
        )

    def _funding_reason(self, code: Any) -> SemanticValue:
        raw = str(code)
        if raw in self._FUNDING_REASONS:
            return self._semantic(raw, self._FUNDING_REASONS, "融资风险说明")
        return self._decision.semantic(raw, category="reason")

    def _funding(self, funding, module_status: str | None = None) -> HumanReadableFundingLoop | None:
        if funding is None:
            return None
        return HumanReadableFundingLoop(
            calculation_status=(self._semantic(module_status, self._MODULE_EXECUTION_STATUS, "融资模块执行状态") if module_status else None),
            state=self._semantic(self._get(funding, "funding_state", "unknown"), self._FUNDING_STATES, "融资循环状态尚未配置中文说明"),
            reasons=[self._funding_reason(item) for item in list(self._get(funding, "reason_codes", []) or [])],
            incremental_revenue=self._get(funding, "incremental_revenue"),
            incremental_nwc=self._get(funding, "incremental_nwc"),
            incremental_debt=self._get(funding, "incremental_debt"),
            incremental_equity=self._get(funding, "incremental_equity"),
            reported_equity_change=self._get(funding, "reported_equity_change"),
            operating_cash_flow=self._get(funding, "operating_cash_flow"),
            factoring_balance=self._get(funding, "factoring_balance"),
            derecognized_receivables=self._get(funding, "derecognized_receivables"),
            receivable_transfer_balance=self._get(funding, "receivable_transfer_balance"),
            other_working_capital_financing=self._get(funding, "other_working_capital_financing"),
            factoring_to_ar=self._get(funding, "factoring_to_ar"),
            comparison_basis_status=self._semantic(
                self._get(funding, "comparison_basis_status", "NOT_APPLICABLE"),
                self._COMPARISON_STATUS,
                "比较期间状态尚未配置中文说明",
            ),
            comparison_basis_limitations=[
                self._semantic(item, self._METRIC_REASONS, "比较期间限制尚未配置中文说明")
                for item in list(self._get(funding, "comparison_basis_errors", []) or [])
            ],
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
            nodes.append(HumanReadableDriverNode(driver_id=driver_id, label=label, explanation=explanation, critical=bool(self._get(node, "critical", False)), evidence_ids=list(self._get(node, "evidence_ids", []) or [])))
        edges = []
        for edge in list(self._get(graph, "edges", []) or []):
            from_id = str(self._get(edge, "from_driver", ""))
            to_id = str(self._get(edge, "to_driver", ""))
            edges.append(HumanReadableDriverEdge(from_driver=from_id, from_label=labels.get(from_id, self._driver_label(from_id)[0]), to_driver=to_id, to_label=labels.get(to_id, self._driver_label(to_id)[0]), relation=self._semantic(self._get(edge, "relation", ""), self._RELATIONS, "驱动关系尚未配置中文说明")))
        scope = str(self._get(graph, "coverage_scope", "specialized"))
        reason = self._get(graph, "coverage_reason")
        if reason == "primary industry strategy coverage is unavailable; generic drivers are informational fallback only":
            reason = "主要业务模型缺少专业行业策略覆盖；当前通用驱动图仅用于信息参考。"
        return HumanReadableDriverGraph(coverage=self._semantic(scope, self._GRAPH_COVERAGE, "驱动覆盖状态尚未配置中文说明"), coverage_limited=bool(self._get(graph, "coverage_limited", False)), coverage_reason=reason, nodes=nodes, edges=edges)

    def _falsifier(self, item) -> HumanReadableFalsifier:
        metric = str(self._get(item, "metric", ""))
        metric_label = {
            "cfo": "经营现金流",
            "ocf": "经营现金流",
            "ccc_days": "现金转换周期",
            "funding_loop_debt_share": "新增营运资金的债务融资占比",
            "revenue_growth": "收入增速",
            "margin_change": "利润率变化",
        }.get(metric, "其他验证指标")
        operator = str(self._get(item, "operator", ""))
        threshold = float(self._get(item, "threshold", 0.0))
        description = self._get(item, "description")
        explanation = str(description) if description else f"当{metric_label}{operator}{threshold:g}时，触发该证伪条件。"
        return HumanReadableFalsifier(metric=metric, metric_label=metric_label, operator=operator, threshold=threshold, explanation=explanation)

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
            falsifiers=[self._falsifier(value) for value in list(self._get(item, "falsifiers", []) or [])],
            confidence=self._get(item, "confidence"),
            next_check_date=(str(self._get(item, "next_check_date")) if self._get(item, "next_check_date") is not None else None),
        )

    def _thesis_signals(self, item) -> HumanReadableThesisSignalAssessment | None:
        if item is None:
            return None
        return HumanReadableThesisSignalAssessment(
            state=self._semantic(self._get(item, "status", "INSUFFICIENT"), self._SIGNAL_STATUS, "经营信号状态尚未配置中文说明"),
            positive_signals=list(self._get(item, "positive_signals", []) or []),
            negative_signals=list(self._get(item, "negative_signals", []) or []),
            evidence_ids=list(self._get(item, "evidence_ids", []) or []),
        )

    def _expectation_quality(self, item, latest_material_event_label: str | None = None) -> HumanReadableExpectationQuality | None:
        if item is None:
            return None
        return HumanReadableExpectationQuality(
            state=self._semantic(self._get(item, "status", "UNKNOWN"), self._EXPECTATION_QUALITY, "市场预期证据质量状态尚未配置中文说明"),
            reasons=[self._semantic(code, self._EXPECTATION_REASONS, "市场预期质量限制尚未配置中文说明") for code in list(self._get(item, "reason_codes", []) or [])],
            source_count=self._get(item, "source_count"),
            source_quality=self._get(item, "source_quality"),
            age_days=self._get(item, "age_days"),
            latest_material_event_ts=self._get(item, "latest_material_event_ts"),
            latest_material_event_label=latest_material_event_label,
            post_event_consensus=self._get(item, "post_event_consensus"),
        )

    def _valuation_models(self, routing) -> list[HumanReadableValuationModel]:
        if routing is None:
            return []
        values = self._get(routing, "models", {}) or {}
        items = values.items() if isinstance(values, dict) else []
        result = []
        for model_id, model in items:
            label, explanation = self._VALUATION_MODELS.get(str(model_id), ("其他估值方法", "当前版本尚未为该扩展估值模型配置专门中文说明。"))
            result.append(HumanReadableValuationModel(
                model_id=str(model_id),
                label=label,
                explanation=explanation,
                score=float(self._get(model, "score", 0.0)),
                status=self._semantic(self._get(model, "status", ""), self._VALUATION_ROUTES, "估值模型状态尚未配置中文说明"),
                reasons=[
                    self._semantic(item, self._VALUATION_REASONS, "估值适用性限制尚未配置中文说明")
                    for item in list(self._get(model, "reason_codes", []) or [])
                ],
            ))
        return sorted(result, key=lambda value: value.score, reverse=True)

    def _forecast_discipline(self, item, module_status: str | None) -> HumanReadableForecastDiscipline | None:
        if item is None:
            return None
        reason = str(self._get(item, "reason", "") or "")
        return HumanReadableForecastDiscipline(
            status=self._semantic(
                module_status or self._get(item, "status", "NOT_APPLICABLE"),
                self._MODULE_EXECUTION_STATUS,
                "预测纪律状态尚未配置中文说明",
            ),
            reason=self._FORECAST_REASONS.get(reason, reason or "当前没有可展示的预测纪律说明。"),
        )

    def _next_verification_event(self, item) -> HumanReadableNextVerificationEvent | None:
        if item is None:
            return None
        return HumanReadableNextVerificationEvent(
            event_name=str(self._get(item, "event_name", "")),
            event_time=self._get(item, "event_time"),
            evidence_ids=list(self._get(item, "evidence_ids", []) or []),
        )

    def _valuation_execution(self, execution) -> HumanReadableValuationExecution | None:
        if execution is None:
            return None
        return HumanReadableValuationExecution(
            selected_model=str(self._get(execution, "selected_model", "")),
            executed_model=str(self._get(execution, "executed_model", "")),
            selection_reason=str(self._get(execution, "selection_reason", "")),
            scenario_logic=str(self._get(execution, "scenario_logic", "")),
            assumptions=list(self._get(execution, "assumptions", []) or []),
            lineage=dict(self._get(execution, "lineage", {}) or {}),
            driver_bridge=list(self._get(execution, "driver_bridge", []) or []),
        )

    def _state_provenance(self, items) -> list[HumanReadableStateProvenance]:
        if not items:
            return []
        result = []
        categories = {"fundamental": "fundamental_state", "valuation": "valuation_state", "expectation": "expectation_state"}
        labels = {"fundamental": "基本面状态", "valuation": "估值状态", "expectation": "市场预期状态"}
        for key in ("fundamental", "valuation", "expectation"):
            item = self._get(items, key)
            if item is None:
                continue
            result.append(HumanReadableStateProvenance(
                dimension=labels[key],
                state=self._decision.semantic(self._get(item, "value", ""), category=categories[key]),
                source=self._semantic(self._get(item, "source", ""), self._STATE_SOURCES, "状态来源尚未配置中文说明"),
                evidence_ids=list(self._get(item, "evidence_ids", []) or []),
                method=self._get(item, "method"),
            ))
        return result

    def _decision_summary(self, result: ResearchRunResult) -> HumanReadableDecisionSummary:
        summary = self._decision.build(result, locale=self._SUPPORTED_LOCALE)
        translated_thesis = self._translate_thesis_text(summary.primary_thesis)
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
            "Capital Expenditure": "资本开支",
            "Free Cash Flow": "自由现金流",
        }
        translated_drivers = [reverse.get(name, name) for name in summary.top_drivers]
        event = summary.next_verification_event
        if event.startswith("next check: "):
            event = "下一次验证日期：" + event.removeprefix("next check: ")
        elif event == "next material disclosure":
            event = "下一次重大信息披露"
        return summary.model_copy(update={"primary_thesis": translated_thesis, "top_drivers": translated_drivers, "next_verification_event": event})

    def build(self, result: ResearchRunResult, locale: str = _SUPPORTED_LOCALE) -> HumanReadableResearchView:
        if locale != self._SUPPORTED_LOCALE:
            raise ValueError(f"unsupported presentation locale: {locale}")
        if not isinstance(result, ResearchRunResult):
            raise TypeError("ResearchViewPresenter.build requires ResearchRunResult")

        profile = result.business_model
        resolution = result.strategy_resolution
        artifacts = result.artifacts
        financial_result = result.module_results.get("core:financial-sanity")
        capital_result = result.module_results.get("core:capital-efficiency")
        funding_result = result.module_results.get("core:funding-loop")
        forecast_result = result.module_results.get("core:forecast-discipline")
        classification_reason = profile.classification_reason
        return HumanReadableResearchView(
            company_id=result.company.company_id,
            decision_ts=result.decision_ts,
            repository=result.baseline.repository_full_name,
            commit_sha=result.baseline.commit_sha,
            research_os_version=result.baseline.research_os_version,
            core_api_version=result.baseline.core_api_version,
            business_model=self._business_model(profile.primary_model),
            classification_status=self._semantic(profile.classification_status, self._CLASSIFICATION, "业务模型识别状态尚未配置中文说明"),
            classification_reason=(self._semantic(classification_reason, self._CLASSIFICATION_REASON, "业务模型识别原因尚未配置中文说明") if classification_reason else None),
            secondary_business_models=[self._business_model(item) for item in profile.secondary_models],
            industry_plugins=[self._plugin(item) for item in resolution.industry_plugins],
            methodology_plugins=[self._plugin(item) for item in resolution.methodology_plugins],
            coverage_gaps=[self._gap(item) for item in resolution.coverage_gaps],
            report_contributions=[self._contribution(item) for item in list(artifacts.get("report.contributions", []) or [])],
            question_assessments=[self._question(item) for item in list(artifacts.get("report.question_assessments", []) or [])],
            financial_sanity=self._financial_sanity(
                artifacts.get("validation.financial"),
                getattr(financial_result, "status", None),
            ),
            kpi_metrics=[self._metric(item) for item in list(artifacts.get("kpi.metrics", []) or [])],
            capital_efficiency=self._capital_efficiency(
                artifacts.get("capital.efficiency"),
                getattr(capital_result, "status", None),
            ),
            funding_loop=self._funding(artifacts.get("capital.funding_loop"), getattr(funding_result, "status", None)),
            driver_graph=self._driver_graph(artifacts.get("drivers.graph")),
            theses=[self._thesis(item) for item in list(artifacts.get("thesis.items", []) or [])],
            thesis_signal_assessment=self._thesis_signals(artifacts.get("thesis.signal_assessment")),
            expectation_quality=self._expectation_quality(artifacts.get("expectation.quality"), artifacts.get("expectation.latest_material_event_label")),
            forecast_discipline=self._forecast_discipline(
                artifacts.get("forecast.discipline"),
                getattr(forecast_result, "status", None),
            ),
            valuation_models=self._valuation_models(artifacts.get("valuation.routing")),
            valuation_execution=self._valuation_execution(artifacts.get("valuation.execution")),
            state_provenance=self._state_provenance(artifacts.get("decision.state_provenance")),
            next_verification_event=self._next_verification_event(artifacts.get("temporal.event")),
            decision_summary=self._decision_summary(result),
            presentation_version=self.version,
        )
