# Research OS 1.6.02 Professional Research Semantic Closure 设计

## 1. 文档属性

| 属性 | 内容 |
|---|---|
| 仓库 | `zoucx80-rgb/Research-OS`（repository id `1350382205`） |
| 冻结基线 | `fd4ce2a83187a251ea60df0d203271e1778fff6b` |
| 基线提交 | `fix: complete v1.6.01 field acceptance closure` |
| 基线验证 | 用户确认最新 `main` CI run 802 成功；本设计重新执行 v1.6.01 三公司 Markdown / HTML / PDF field acceptance |
| 基线版本 | Research OS `1.6.01` / Core API `2.0` / Plugin API `2.0` / Snapshot Schema `2.0` / HTTP API `v1` |
| 目标版本 | Research OS `1.6.02` |
| 推荐契约版本 | Core API `2.0` / Plugin API `2.0` / Snapshot Schema `2.0` / HTTP API `v1`（均不升级） |
| 发布性质 | 1.6 系列 professional-research semantic closure |
| 研究验收样本 | 钢研高纳 `300034.SZ`、中电港 `001287.SZ`、君亭酒店 `301073.SZ` |
| 固定研究时点 | `decision_ts = 2026-08-30T00:00:00Z` |
| 文档状态 | 设计评审稿；经用户批准后才能生成实施计划或修改生产代码 |
| 核心原则 | Canonical-first、No Time Travel、Everything Has Lineage、Models Beat Simple Benchmarks、Fail-closed、Research Signal != Auto Trading |

## 2. 决策摘要

1.6.02 应收敛为“专业研究语义闭环 P0 修复版”，解决当前真实输出中直接限制投资研究结论的六个问题：

1. 单期 financial time series 被误判为时序充分；
2. `ForecastResearchModule` 未接入已经存在的 PIT/OOS benchmark engine；
3. Valuation 没有受控执行与 PIT market anchor / market gap；
4. Decision Context 过于粗糙，valuation state 当前恒为 `UNRELIABLE`；
5. Hospitality 已能被 Router 识别，但没有兼容行业插件；
6. Research Readiness 主要判断 artifact 是否存在，不能表达领域证据充分性。

推荐 1.6.02 包含以下六个里程碑：

```text
M1 Temporal Research Foundation + Research Sufficiency
M2 Executable Forecast Evidence + Benchmark Gate
M3 Valuation Execution + PIT Market Anchor + Market Gap
M4 Decision Context v2 + Decision Derivation
M5 Hospitality Plugin + Targeted Industry Closure
M6 Reporting Projection + Three-company Field Acceptance + Release
```

以下能力明确后移到 1.6.03：

- 完整 DriverGraph-bound Base/Bull/Bear Scenario Engine；
- 自动 Previous Snapshot / Research Delta / verification-event 跨 Run 闭环；
- 制造业订单、产能、转固、收入与 ROIC 的完整定量链；
- 分销行业更深的多期压力测试和归因；
- Investor Brief / Audit Appendix 独立信息架构与纯版式增强。

## 3. 设计输入与真实输出复核

### 3.1 复核方法

设计评审不是只读 fixture 或测试断言。基于冻结 SHA，重新执行：

```bash
RESEARCH_OS_RUN_PDF_INTEGRATION=1 \
python scripts/render_field_acceptance_v1_6_01.py \
  --case-manifest tests/fixtures/field_acceptance/v1_6_01/cases.json \
  --output-dir <temporary-output-dir> \
  --repository-root . \
  --commit-sha fd4ce2a83187a251ea60df0d203271e1778fff6b
```

结果为：

```text
FIELD ACCEPTANCE VERIFIED: v1.6.01
```

三家公司均走过真实的最终链：

```text
ResearchRunCommand
  -> ResearchApplication
  -> ResearchRunResult / ArtifactSnapshot
  -> HumanReadableResearchView
  -> ResearchReportDocument
  -> Markdown
  -> HTML
  -> PDF
```

每家公司最终结果均包含 33 个 canonical artifact id，machine semantics 和 presentation 均为 `PASS`。评审同时检查了 Markdown 正文、HTML 和真实 A4 PDF 页面，不将 fixture 声明当作最终研究能力。

### 3.2 三公司最终输出

| 公司 | 最终决策 | 执行完整度 | 研究就绪度 | Research depth | PDF |
|---|---|---|---|---|---:|
| 300034.SZ 钢研高纳 | `INSUFFICIENT_EVIDENCE` | `COMPLETE` | `NOT_READY` | `PASS` | 15 页 |
| 001287.SZ 中电港 | `RISK_REVIEW` | `COMPLETE` | `NOT_READY` | `LIMITED` | 16 页 |
| 301073.SZ 君亭酒店 | `INSUFFICIENT_EVIDENCE` | `INCOMPLETE` | `NOT_READY` | `LIMITED` | 11 页 |

### 3.3 钢研高纳

当前报告具备：

- 制造业 Business Model 与通用 KPI；
- 2026H1 收入、归母净利润、毛利率、OCF、Capex；
- 周期恢复与 economic moat 的语义边界；
- 单点原材料价格敏感性及其 assumption、boundary、applicability、caveat；
- DCF / PE ranges 与 `MODEL_DISAGREEMENT`；
- monitoring rule 与 next verification event。

直接缺口：

- 所谓“财务趋势”实际只有 2026H1 单期，但 readiness 的 `time_series` 仍为 `PASS`；
- 没有多年或多报告期的收入、毛利、现金流、产能、产品结构变化；
- Forecast 没有执行 OOS benchmark；
- Valuation execution 为空，只有外部提供的 ranges；
- 没有 PIT market price / market valuation anchor，无法判断模型价值与市场价格的差距；
- 当前 sensitivity 是合格的机械敏感性，不是结构化 Base/Bull/Bear scenario。

### 3.4 中电港

当前报告具备：

- Distributor Business Model 与较丰富的单期 KPI；
- CCC、DSO、DIO、DPO、保理/应收暴露、债务融资占比、融资成本/毛利；
- material funding risk 能进入 `RISK_REVIEW`；
- 下一定期报告的营运资金、融资成本和现金流验证事件。

直接缺口：

- KPI 主要是 2026H1 横截面，没有趋势与恶化/修复路径；
- `CapitalEfficiencyEngine.FundingLoopResult` 已计算 incremental revenue、NWC、debt、equity、OCF、factoring、comparison basis 等字段，但 application adapter 最终只保留 `funding_state` 和 `reason_codes`；
- 报告因此只能表达“有风险”，不能表达风险规模、比例、趋势和修复条件；
- Forecast、valuation execution、PIT market anchor 和 market gap 均缺失。

### 3.5 君亭酒店

当前报告具备：

- Router 正确识别 `hospitality`；
- core financial facts、现金流和租赁占比继续运行；
- `right_of_use_assets_to_assets`、`lease_liabilities_to_assets` 等 lease-heavy 证据；
- 无兼容行业插件时正确 fail-closed，不伪造 ADR、OCC、RevPAR 或同店增长；
- 方法限制和下一验证事件进入最终报告。

直接缺口：

- built-in plugin provider 只有 manufacturing / distributor；
- 缺少酒店数、房间数、成熟/爬坡酒店、直营/加盟/管理/租赁结构；
- 缺少 lease-adjusted capital efficiency 和 valuation fitness；
- no-plugin 直接导致执行 `INCOMPLETE`，专业研究深度有限；
- Forecast、valuation execution 和 market anchor 同样缺失。

### 3.6 Presentation 观察

PDF 可读性和第一页决策快照已经满足 1.6.01 目标，不应在 1.6.02 重做。

真实 PDF 中：

- 钢研高纳 investor body 约 6 页，audit appendix 约 9 页；
- 中电港 investor body 约 6 页，audit appendix 约 10 页；
- 君亭酒店 investor body 约 4 页，audit appendix 约 7 页；
- 正文末页存在较多空白，审计附录占比偏高。

这是 P2 信息架构问题。1.6.02 只投影新增 canonical research semantics，不重做 HTML/PDF 视觉体系，也不把 Reporting 变成第二研究引擎。

## 4. 当前代码能力审计

| 方向 | 已有能力 | 部分已有或真正缺失 | 优先级 | 1.6.02 决策 |
|---|---|---|---:|---|
| Multi-period Financial/KPI | `FinancialTimeSeriesSet`、`ReportingPeriod`、PIT lineage | 当前 series point 只有 period/end/value；无 frequency、comparison basis、YoY/QoQ/TTM、覆盖跨度和异常规则 | P0 | 纳入 |
| Forecast Evidence / Benchmark | `TimeSeriesBacktester`、两个 naive benchmark、MAE/RMSE/方向/覆盖率、PIT 防泄漏、promotion gate | Professional module 固定 `INSUFFICIENT_EVIDENCE`；public artifact 丢失大部分回测结果 | P0 | 纳入 |
| Valuation + PIT Market Anchor | Model fitness、routing、method execution domain、execution validator、ranges、reconciliation | Application 不执行 method；无 market anchor / market gap；Decision valuation 恒不可靠 | P0 | 纳入 |
| Structural Scenario | `DriverGraph`、`SensitivityCase`、scenario range role | 无成组 scenario、driver binding、内部一致性、scenario valuation 和现金流联动 | P1 | 后移 1.6.03 |
| Decision Context v2 | Thesis、funding、expectation、reconciliation、semantic signals 已部分进入 Decision | 缺 trend、capital efficiency、forecast quality、market gap、sufficiency；provenance 只列维度，不表达规则推导 | P0 | 纳入 |
| Prior Run / Research Delta | Snapshot 2.0、company/as-of 查询、历史 replay | Application 不自动读取 previous snapshot；无 evidence/thesis/valuation/decision delta | P1 | 后移 1.6.03 |
| Hospitality Plugin | Router 能识别 hospitality；Plugin API 有 KPI/valuation/forecast/report services | 无 built-in hospitality plugin 和酒店 KPI pack | P0 | 纳入 |
| Manufacturing / Distributor depth | 两个插件、行业问题、KPI packs、FundingLoop engine | 制造业所需 operating capabilities 未实现；FundingLoop 定量字段在 canonical adapter 丢失 | P0/P1 | 只纳入 Funding Loop bridge 和 capability gap；完整深化后移 |
| Research Sufficiency | `ResearchReadinessAssessment` 有九个维度和 fail-closed | 主要判断 artifact 非空；无 temporal/benchmark/model executability/material gap；单期时序假阳性 | P0 | 纳入 |
| Investor Report Depth | 严格单向链、artifact-specific projectors、audit appendix、PDF semantic gate | 正文密度不足、审计占比高、部分术语未本地化 | P2 | 只投影新增语义；布局后移 |

## 5. 优先级定义

### 5.1 P0 — 直接限制专业投资研究结论

- 多期财务/KPI 与 comparison basis；
- 可执行 Forecast benchmark evidence；
- 受控 Valuation execution；
- PIT market anchor 与 market gap；
- Decision Context v2；
- Research Sufficiency；
- HospitalityIndustryPlugin；
- Funding Loop quantitative bridge。

### 5.2 P1 — 显著提高研究深度

- Structural Scenario Engine；
- Prior Run / Research Delta；
- 制造业完整经营因果链；
- 分销业多期归因和压力测试。

### 5.3 P2 — 报告体验与工程增强

- Investor Brief / Audit Appendix 双层信息架构；
- PDF 空白、分页和密度优化；
- 术语本地化与标签统一；
- 专门的 trend chart 或 presentation enhancement。

## 6. Scope 方案

### 6.1 Conservative

范围：Temporal/Sufficiency、Forecast、Market Anchor、Decision Context。

优点：

- 变更最小；
- 优先修复通用研究内核。

缺点：

- 君亭酒店仍因无 compatible plugin 而 `INCOMPLETE`；
- 中电港 Funding Loop 仍缺少定量桥；
- 不能关闭全部真实 P0。

### 6.2 Recommended

范围：全部通用 P0，加 Hospitality Plugin 和 Funding Loop Bridge；完整 Scenario、Research Delta 与纯报告重构后移。

优点：

- 关闭三家公司真实输出中的直接阻塞项；
- 复用已有 backtest、valuation methods、Plugin API、Snapshot API；
- 不引入第二套 runtime、reporting calculation 或 snapshot schema；
- 保持版本范围和回归面受控。

缺点：

- Decision 中 scenario dimension 在本版本只能使用现有 sensitivity 或明确标为 unavailable；
- 跨 Run 状态变化仍需 1.6.03 才能闭环。

### 6.3 Aggressive

范围：Recommended 加完整 Scenario、Research Delta、制造/分销全链和报告双层重构。

不推荐原因：

- 同时改变单次研究语义、跨 Run 状态机、插件体系与报告信息架构；
- 需要更多真实公司数据和长时间序列；
- 难以在一个 patch 中建立清晰的失败归因和 release evidence。

### 6.4 推荐决策

采用 **Recommended**。

版本边界是：

> 1.6.02 负责把“当前单次研究运行”需要的 P0 语义闭环做实；1.6.03 再使用稳定的 1.6.02 artifacts 建设跨 Run Delta 和结构化 Scenario。

## 7. 推荐目标架构

```text
Revision-bound PIT evidence
  -> Period-normalized financial / operating observations
  -> Temporal Analysis + Funding Loop Bridge
  -> Forecast Benchmark Evidence
  -> Valuation Execution + Reconciliation
  -> PIT Market Anchor + Market Gap
  -> Research Sufficiency
  -> Decision Context Builder
  -> Decision Engine + Decision Derivation
  -> ArtifactSnapshot
  -> Presentation-only reporting chain
```

必须保持：

- Research semantics 只在 domain/application modules 中形成；
- Presenter、Composer、Markdown、HTML、PDF 只投影；
- 所有趋势、误差、估值差、状态变化均携带 evidence/assumption lineage；
- missing data 保持 missing；
- Decision 输出 research state，不输出自动交易指令。

## 8. M1 — Temporal Research Foundation & Research Sufficiency

### 8.1 Goal

从“存在一个 series artifact”升级为“存在足够、可比较、PIT 合规的多期证据”，并按领域表达研究充分性。

### 8.2 Canonical artifacts/contracts

新增建议类型：

```text
FinancialPeriodObservation
  metric_id
  reporting_period: ReportingPeriod
  period_kind
  value / unit
  accounting_scope
  value_kind: reported | derived
  annualized
  comparison_basis
  available_ts
  evidence_refs / assumption_refs

MetricTemporalAssessment
  metric_id
  comparable_point_count
  temporal_span
  yoy_change / qoq_change / ttm_value
  trend_state
  turning_point_state
  anomaly_flags
  comparison_status / reason_codes
  lineage

FinancialTemporalAnalysis
  assessments
  temporal_coverage
  unresolved_gaps
```

新增 artifact：

- `financial.temporal_analysis@2.0`；
- `research.sufficiency@2.0`。

`research.sufficiency` 至少包含：

- domain id；
- coverage；
- evidence quality；
- temporal coverage；
- benchmark coverage；
- peer coverage；
- model executability；
- unresolved material gaps；
- upgrade evidence requirements；
- status/reason/lineage。

保留现有 `financial.time_series` 和 `research.readiness`。Readiness 表达“能否完成流程”，Sufficiency 表达“证据是否足以支撑专业结论”。

### 8.3 Modules/services

- `TemporalAnalysisService`；
- `ComparisonBasisValidator`；
- `ResearchSufficiencyEvaluator`；
- `FinancialResearchModule` 写 raw/normalized series 与派生 temporal analysis；
- Readiness 不再用 collection 非空代表 temporal PASS。

禁止：

- 从半年累计值伪造单季度；
- 用插值补缺失季度；
- 跨会计范围或跨 reporting basis 直接计算变化；
- 将 annualized 值伪装为 reported 值；
- 使用 `available_ts > decision_ts` 的数据。

### 8.4 Reporting changes

增加：

- 报告期、口径和是否 reported/derived；
- YoY/QoQ/TTM 的明确 basis；
- 趋势、持续性、拐点和异常状态；
- 已知什么、不知道什么、为什么不知道、补什么证据。

所有计算来自 `financial.temporal_analysis`，projector 不自行计算变化率。

### 8.5 Tests

- 单点 series 的 temporal coverage 必须为 insufficient；
- mismatched basis 不得计算同比/环比；
- 累计半年数据不得拆季度；
- future availability 必须触发 PIT failure；
- derived trend 必须拥有输入 evidence/assumption lineage；
- 输入顺序变化不得改变 canonical fingerprint；
- 旧 Snapshot 2.0 必须继续 decode/replay。

### 8.6 Three-company field acceptance

- 300034：收入、毛利率、OCF 至少形成可比较趋势，或逐项给出不足原因；
- 001287：收入、AR、Inventory、NWC、OCF、Debt 的期间与 comparison basis 可审计；
- 301073：租赁、收入、现金流的 temporal coverage 独立评估；
- 三家公司任何单点时序均不得显示 temporal coverage `PASS`。

### 8.7 Release gate

新增 verification pack：`v1-6-02-temporal-sufficiency`。

## 9. M2 — Executable Forecast Evidence & Benchmark Gate

### 9.1 Goal

让 `ForecastResearchModule` 调用现有 forecasting domain engine，形成真正可执行、可审计的 forecast evaluation。

### 9.2 Canonical artifacts/contracts

新增 command input：

```text
ForecastExperimentInput
  hypothesis
  target_metric / horizon
  feature_names
  timestamped observations
  benchmark_id
  evaluation_ts
  n_splits
  current_model_stage
  applicability / model_boundary / caveats
```

继续写入现有 `forecast.evaluation@2.0` 的高层状态，并新增：

- `forecast.benchmark_evidence@2.0`：
  - model / benchmark identity and versions；
  - MAE / RMSE；
  - direction accuracy；
  - interval coverage；
  - benchmark MAE 与 improvement；
  - sample count / folds；
  - stability windows；
  - OOS / PIT status；
  - promotion decision；
  - applicability、boundary、caveats、lineage。

使用新增 artifact 而不是破坏性扩展已冻结的历史 payload。

### 9.3 Modules/services

`ForecastResearchModule` 复用：

- `TimeSeriesBacktester`；
- `builtin_benchmark_registry()`；
- `decide_promotion()`；
- 现有 forecast promotion policies。

不得复制第二套回测或 promotion 规则。

### 9.4 Reporting changes

展示：

- 模型与 benchmark；
- 样本数、fold 数；
- MAE/RMSE、方向准确率和覆盖率；
- 是否稳定、是否击败 benchmark；
- 未晋级理由；
- applicability、model boundary、caveats。

### 9.5 Tests

- training/test 必须按时间排序；
- feature availability 和 label maturity 必须满足 PIT；
- target/realized outcome 不得进入 feature；
- 无 OOS、无注册 benchmark、无预注册假设、fold 不足均不得晋级；
- 未击败简单 benchmark 不得给强预测结论；
- canonical artifacts 必须逐字段映射底层 backtest result。

### 9.6 Three-company field acceptance

- 至少一家真实公司必须完成 OOS benchmark evaluation，不能只由 synthetic test 证明；
- 其他公司如果样本不足，必须返回明确的 sample/temporal/feature gap；
- 三家公司均不得因 forecast evidence 不足产生强方向性预测；
- 报告必须显示 benchmark、误差、样本、稳定性和边界。

### 9.7 Release gate

新增 verification pack：`v1-6-02-forecast-benchmark`。

## 10. M3 — Valuation Execution, PIT Market Anchor & Market Gap

### 10.1 Goal

建立：

```text
Model Fitness
  -> Controlled Execution
  -> Reconciliation
  -> PIT Market Anchor
  -> Market Gap
  -> Decision valuation state
```

现有 `scenario` range role 继续允许作为可选输入，但完整 Scenario Engine 不属于本里程碑。

### 10.2 Canonical artifacts/contracts

新增：

```text
PitMarketAnchor
  company_id / security_id / share_class
  observed_ts / available_ts
  price / currency / unit
  corporate_action_basis
  source identity
  evidence_refs

ValuationMarketGap
  reconciliation identity
  market anchor identity
  model_low / model_high / market_value
  gap_low / gap_high
  state: UNDERVALUED | FAIR | OVERVALUED | UNKNOWN
  comparison_status / reason_codes
  evidence_refs / assumption_refs
```

新增 artifacts：

- `valuation.market_anchor@2.0`；
- `valuation.market_gap@2.0`。

### 10.3 Modules/services

- `ValuationResearchModule` 调用现有 valuation methods；
- execution 必须经过现有 `ValuationExecutionValidator`；
- externally supplied execution 必须明确标记来源并经过相同验证；
- `MarketAnchorValidator` 检查 PIT、币种、per-share/total-value、share class 和 corporate action basis；
- `ValuationMarketGapService` 只比较口径兼容的 reconciliation 与 market anchor。

Market anchor 不得混入 model reconciliation 的数学区间；模型一致性与市场高低估是两个不同概念。

### 10.4 Reporting changes

展示：

- model fitness 与 routing；
- execution result；
- reconciliation；
- market anchor 时点和口径；
- market gap 与不可比较原因。

Reporting 不重新执行模型、不选择价格、不计算 gap。

### 10.5 Tests

- market observation 必须满足 `observed_ts <= available_ts <= decision_ts`；
- 非交易日使用最后一个 PIT 合规且可获得的观测；
- future price 必须拒绝；
- currency/share/corporate-action basis 不一致时必须不可比较；
- model disagreement 不得被 market anchor 掩盖；
- market anchor 不得进入 reconciliation intersection；
- execution/result/range/market gap lineage 完整。

### 10.6 Three-company field acceptance

- 三家公司都有 PIT market anchor，或可验证的明确缺失原因；
- 至少一家产生 `SUPPORTED` 且 basis-compatible 的 market gap；
- valuation state 不再因代码常量而全部 `UNRELIABLE`；
- 报告显示 anchor 的实际观测时点，不将 decision date 伪装为交易日。

### 10.7 Release gate

新增 verification pack：`v1-6-02-valuation-market-gap`。

## 11. M4 — Decision Context v2 & Decision Derivation

### 11.1 Goal

让 Portfolio Decision 消费完整的 P0 canonical states，并解释“哪些输入通过哪条规则形成当前决策”。

### 11.2 Canonical artifacts/contracts

新增：

- `decision.input_assessment@2.0`；
- `decision.derivation@2.0`。

Decision input assessment 至少包含：

- financial trend；
- capital efficiency；
- funding loop / funding bridge；
- thesis / anti-thesis / falsifiers；
- semantic signals / claims；
- expectation gap；
- forecast quality；
- valuation reconciliation / market gap；
- sensitivity/scenario availability；
- evidence confidence；
- research sufficiency blockers。

Decision derivation 至少包含：

- rule id/version；
- normalized input states；
- output decision state；
- blocking / supporting reason codes；
- used thesis/claim/artifact identities；
- evidence/assumption lineage。

保留现有 `decision.record@2.0` 和 `decision.state_provenance@2.0`。跨 Run 的“上次决策 A -> 本次决策 B”属于 1.6.03；本版本的 A -> B 指“输入研究状态 -> 当前决策状态”。

### 11.3 Modules/services

- 新增 `DecisionContextBuilder`；
- `PortfolioDecisionModule` 不再自行从少量 artifact ad-hoc 推断；
- `DecisionEngine` 消费 builder 的 typed context；
- scenario 不可用时形成显式 unavailable dimension；
- material funding risk 必须能覆盖乐观估值或高 thesis confidence；
- 输出 research state，不输出买卖、下单或仓位指令。

### 11.4 Reporting changes

Decision Snapshot 增加：

- 当前状态；
- 关键支持因素；
- 关键阻塞因素；
- 状态推导规则；
- 哪些证据可以升级 conviction。

### 11.5 Tests

- valuation state 必须来自 market gap，不再恒定；
- funding risk 不得被乐观 valuation 覆盖；
- forecast 未通过 benchmark gate 不得强化决策；
- research sufficiency blocker 不得被高 thesis confidence 绕过；
- 缺失 scenario 必须显式记录，而不是静默忽略；
- 所有实际使用的输入进入 provenance/derivation；
- 相同 canonical input 得到确定性相同 decision fingerprint。

### 11.6 Three-company field acceptance

- 300034：区分周期改善、估值模型分歧、market gap 和证据不足；
- 001287：Funding Loop 风险继续能够触发 risk review，但原因必须包含定量来源；
- 301073：缺行业证据时继续 fail-closed；插件生效后按完整 context 重新评估；
- 验收不硬编码一定要产生买入、卖出或某个乐观状态。

### 11.7 Release gate

新增 verification pack：`v1-6-02-decision-context`。

## 12. M5 — Hospitality Plugin & Targeted Industry Closure

### 12.1 Goal

关闭君亭酒店因缺少 compatible plugin 导致的执行不完整，同时保留中电港 Funding Loop 已经计算但尚未进入 canonical result 的定量信息。

### 12.2 Canonical artifacts/contracts

新增：

- `industry.capability_assessment@2.0`；
- `capital.funding_loop_bridge@2.0`。

Funding Loop Bridge 至少保留：

- incremental revenue；
- incremental NWC；
- incremental debt/equity；
- operating cash flow；
- factoring / derecognized receivables / transfer balance；
- factoring-to-AR；
- comparison basis status/errors；
- funding state、risk reasons；
- deterioration/repair conditions；
- lineage。

酒店领域优先复用已有 `kpi.metrics` 和 `research.operating_evidence`：

- ADR；
- OCC；
- RevPAR；
- same-store growth；
- hotel count / room count；
- mature / ramp-up mix；
- managed / franchised / leased mix；
- lease liabilities / right-of-use assets；
- lease-adjusted capital efficiency；
- lease-adjusted valuation fitness。

### 12.3 Modules/services

- `HospitalityIndustryPlugin`；
- `HospitalityKpiPack`；
- `IndustryCapabilityEvaluator`；
- Capital adapter 将完整 `FundingLoopResult` 投影到 bridge；
- manufacturing/distributor/hospitality 的 capability support 与 company evidence availability 分开建模。

“插件支持计算”不等于“该公司数据可用”。每个酒店 KPI 必须单独经过 capability、evidence、period、basis 和 lineage gate。

### 12.4 Reporting changes

- 酒店运营面板按 supported / missing / not applicable 展示；
- 明确哪些酒店 KPI 可算、哪些缺证据、需要什么数据；
- 分销 Funding Loop 展示规模、比例、趋势、恶化和修复条件；
- 不使用行业均值或零值填充缺失 ADR/OCC/RevPAR；
- 300034 未覆盖的订单、产能、良率等能力进入 capability gap，不生成无证据结论。

### 12.5 Tests

- 没有酒店运营数据时不得产生 ADR/OCC/RevPAR 数值；
- 任何酒店指标必须绑定 evidence refs；
- 租赁调整必须区分 fact/calculation/assumption；
- plugin applicability、failure isolation、fingerprint 和 snapshot replay；
- Funding Loop bridge 与 engine output 逐字段一致；
- comparison basis 不完整时，定量 bridge 保留值但不得输出不受支持的比较结论。

### 12.6 Three-company field acceptance

- 301073 解析到 hospitality plugin，不再因为 `NO_COMPATIBLE_INDUSTRY_PLUGIN` 导致 execution `INCOMPLETE`；
- 缺失的 ADR/OCC/RevPAR 等逐项 fail-closed；
- 有 lease evidence 时形成 lease-aware assessment，没有证据时不得给调整结果；
- 001287 最终报告包含 quantitative Funding Loop bridge；
- 300034 未覆盖 manufacturing operating evidence 进入 capability/sufficiency gaps。

### 12.7 Release gate

新增 verification pack：`v1-6-02-industry-closure`。

## 13. M6 — Reporting Projection, Field Acceptance & Release

### 13.1 Goal

将 M1-M5 的 canonical research semantics 无损投影到最终 Markdown / HTML / PDF，并完成 1.6.02 发布验证。

### 13.2 Canonical artifacts/contracts

本里程碑不新增研究语义。它冻结：

- M1-M5 artifact catalog；
- artifact decoder registry；
- component/module/plugin fingerprints；
- release manifest；
- field acceptance profile。

### 13.3 Modules/services

- 更新 `ResearchViewPresenter` artifact projection registry；
- 更新 `ResearchReportComposer` section composition；
- Markdown/HTML/PDF renderer 只显示已经投影的字段；
- `SemanticPreservationValidator` 覆盖新增 artifacts；
- 历史 v1.5.08-v1.5.12 replay 和 v1.6.01 gate 保持冻结。

### 13.4 Reporting changes

1.6.02 只提升以下研究内容的决策信息密度：

- temporal trends；
- benchmark evidence；
- valuation execution / market gap；
- decision derivation；
- research sufficiency；
- industry capability / funding bridge。

不重做：

- 1.6.01 sensitivity presentation；
- next verification event；
- PDF first-page semantic validation；
- professional canonical wiring；
- 已有通用 reporting projector 架构。

### 13.5 Tests

- projector 只能读取 canonical fields；
- no semantic recomputation in Presenter/Composer/Renderer；
- Markdown/HTML/PDF 语义一致；
- 第一页继续满足既有 v1.6.01 semantic gate；
- Snapshot 2.0 encode/decode/integrity/replay；
- HTTP API v1 generic artifact/read models；
- targeted unit/integration/regression；
- full pytest；
- build/install/package；
- secret scan；
- release pipeline 与 release gate。

### 13.6 Three-company field acceptance

每家公司必须重新生成 Markdown、HTML 和 PDF，并记录：

- machine semantics；
- research sufficiency/depth；
- presentation；
- execution completion；
- research readiness；
- decision state/derivation；
- PIT/lineage/snapshot integrity。

跨公司最低门槛：

- 至少一家真实公司完成 OOS benchmark evaluation；
- 至少一家产生 basis-compatible valuation market gap；
- 301073 不再因无 hospitality plugin 导致 execution incomplete；
- 001287 报告包含 quantitative Funding Loop；
- 单期 series 不得产生 temporal coverage PASS；
- 缺失数据继续显式缺失，不为了验收伪造数据。

### 13.7 Release gate

新增：

- verification pack：`v1-6-02-field-release`；
- current field profile：`field-v1.6.02`。

同时保留所有历史 verification packs、field replay profiles、release tags 和 historical snapshots。

## 14. API、Snapshot 与迁移决策

| 接口 | 决策 | 理由 |
|---|---|---|
| Core API `2.0` | 保持 | 通过 additive command inputs、new typed values 和 new artifact IDs 扩展；不删除或改变既有必填字段 |
| Plugin API `2.0` | 保持 | 现有 `KpiProvider`、valuation/forecast methods、policies、report contributions 已足够承载 hospitality |
| Snapshot Schema `2.0` | 保持 | Snapshot 已按 artifact id/schema/type 存储 payload 和 fingerprint；新增 artifact 可由 decoder registry 注册 |
| HTTP API `v1` | 保持 | 通用 run/artifact/snapshot/research-view endpoint 可暴露新增 artifacts，无需专用 endpoint |
| SQL migration | 预计不需要 | company + decision_ts snapshot query 已存在；1.6.02 不实现 previous-run linkage |

### 14.1 兼容策略

- 优先新增 artifact ID，不破坏性改变已发布 artifact 的 required payload；
- 老 Snapshot 2.0 必须继续 decode 和 replay；
- generic HTTP artifact response 保持结构不变；
- plugin manifest 继续声明 Plugin API 2.0；
- 只升级行为实际变化的 module/plugin/presenter/composer fingerprints；
- 不增加兼容 shim、第二套 runtime 或双写路径。

### 14.2 重新评审触发条件

实现阶段如果发现必须执行以下任一事项，必须暂停并重新做 contract/version review：

- 修改 Snapshot envelope 或 hash projection；
- 删除或重解释已有 artifact 字段；
- 改变 `ArtifactKey` identity 规则；
- 改变 Plugin service protocol；
- 改变 HTTP endpoint 或 response envelope；
- 需要持久化 previous snapshot foreign key 或跨 Run 状态机。

## 15. 1.6.03 明确后移项

### 15.1 Structural Scenario Engine

完整范围应包括：

- Base/Bull/Bear scenario set；
- DriverGraph node/edge binding；
- 多驱动假设与内部一致性；
- probability、applicability、boundary、caveats、lineage；
- financial/FCF/valuation 联动；
- manufacturing、distributor、lease-aware hospitality scenario templates。

它依赖 1.6.02 的 temporal、forecast 和 valuation execution，不应与基础闭环同时建设。

### 15.2 Prior Run / Research Delta

完整范围应包括：

- previous snapshot 自动解析；
- new/replaced evidence；
- KPI delta；
- thesis strengthening/weakening；
- falsifier hit；
- valuation/expectation/decision/confidence change；
- next verification event resolution；
- current/prior schema and integrity validation。

应在 1.6.02 artifacts 稳定后再定义 delta semantics，避免比较对象在同一版本内继续漂移。

### 15.3 Investor-facing information architecture

- Investor Brief 与 Audit Appendix 独立输出；
- page budget、空白控制、图表和术语本地化；
- 不改变 ArtifactSnapshot 的 semantic authority。

## 16. 总体验收标准

1. 设计批准后才生成实施计划；
2. 实现必须从最新 `main` 重新冻结 delivery SHA；
3. 不创建额外长期分支；
4. 所有研究派生值具备 lineage；
5. 所有市场数据和 forecast folds 满足 No Time Travel；
6. 没有 OOS benchmark evidence 不得晋级模型或形成强预测；
7. 无行业证据不得生成行业 KPI；
8. Decision 完整消费可用的 P0 canonical states，并披露缺失维度；
9. Reporting/PDF 不重新计算研究语义；
10. 三公司真实 pipeline 输出、历史 replay、full pytest、release pipeline 全部通过；
11. release commit 和远端 `main` 必须对应同一已验证 SHA；
12. 不改写历史 tag、historical snapshot 或旧 field acceptance 事实。

## 17. Approval Gate

本文件是 1.6.02 的设计边界，不是 implementation plan。

用户批准前：

- 不修改 production code；
- 不创建 implementation tasks；
- 不改变版本 metadata；
- 不更新 release gates；
- 不重新定义 1.6.01 已完成工作。

用户批准后，下一步才是基于本设计生成独立的 M1-M6 implementation plan，并按 TDD、阶段验收和 release evidence 执行。
