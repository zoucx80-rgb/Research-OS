# Research OS 1.6.01 Professional Research Closure 设计

## 1. 文档属性

| 属性 | 内容 |
|---|---|
| 仓库 | `zoucx80-rgb/Research-OS` |
| 冻结基线 | `1cb163b38ac971dfc045e6adfe31e67efdd87af7` |
| 基线版本 | Research OS `1.6.0` / Core API `2.0` / Plugin API `2.0` / Snapshot Schema `2.0` / HTTP API `v1` |
| 目标版本 | Research OS `1.6.01` |
| 契约版本 | Core API `2.0` / Plugin API `2.0` / Snapshot Schema `2.0` / HTTP API `v1`（不升级） |
| 发布性质 | 1.6 系列 correctness / professional-completeness patch |
| 研究验收样本 | 钢研高纳 `300034.SZ`、中电港 `001287.SZ`、君亭酒店 `301073.SZ` |
| 固定研究时点 | `decision_ts = 2026-08-30T00:00:00Z` |
| 核心原则 | Canonical-first、No Time Travel、Everything Has Lineage、Fail-closed、Reporting ≠ Research Engine |

## 2. 背景与问题定义

1.6.0 完成了 Core API 2.0、Plugin API 2.0、typed Artifact、Snapshot 2.0、HTTP API v1、历史 replay、release gate 和单向 Presentation pipeline 的架构收敛，但真实公司回归显示“架构存在”与“专业研究闭环可用”之间仍有明显断层。

对三家真实公司用 1.6.0 canonical `ResearchApplication` 重新运行后，出现以下确定问题：

1. `ResearchRunCommand` 已声明 `financial / thesis / expectations / valuation / monitoring / forecasting / peers / readiness` typed inputs，但 `ResearchPlanCompiler` 当前只编排 Strategy、KPI、ThesisPortfolio、Decision；rich typed input 与 facts-only 对三家公司得到字节级相同的 View/Markdown 和相同 Semantic Fingerprint。
2. `PortfolioDecisionModule()` 以 `UNCERTAIN / UNRELIABLE / UNKNOWN` 默认状态启动，Decision provenance 主要只引用 thesis portfolio，无法消费 Funding Loop、Valuation、Expectation 等 canonical professional states。
3. v1.6.0 field acceptance 的 `research_depth` 会直接读取 fixture 的 `valuation_ranges` 旁路调用 `ValuationReconciler`；因此 fixture 可以标记 `PASS/INTERSECTION`，即使最终 `ResearchRunResult` 与报告完全没有 valuation artifact。
4. `ResearchViewPresenter → ResearchReportComposer → ResearchReportMarkdownRenderer` 将 BaseModel 泛化为 JSON 后递归 dump；真实报告正文出现 Schema、raw enum、reason code、URL、fingerprint、20+ 位小数和大段 `evidence.pit`。
5. v2 Composer 的 section title 已改变，但 HTML renderer 仍按旧中文标题匹配布局，已知正文 section 全部 fallback 到 generic `standard-section`。
6. 君亭酒店 no-plugin fail-closed 是正确行为，但当前退化为“没有 KPI 就没有研究”，没有把 core financial facts、lease-heavy limitation、coverage gap 和下一验证需求组织成可用研究结论。

量化回归（同一批 PIT 证据，对照 immutable v1.5.09 replay）：

| 公司 | v1.6.0 investor body | v1.5.09 body | 膨胀 |
|---|---:|---:|---:|
| 钢研高纳 | 1135 行 | 173 行 | 6.6x |
| 中电港 | 1212 行 | 189 行 | 6.4x |
| 君亭酒店 | 579 行 | 122 行 | 4.7x |

这说明 1.6.01 的首要任务不是“PDF 美化”，而是完成 **Professional Research Closure**：让 Core API 2.0 已存在的专业输入真正进入 canonical ArtifactSnapshot，再让 Decision/Readiness、Reporting、Presentation 和 Acceptance 全部围绕同一个最终结果闭环。

## 3. 产品目标

1.6.01 的发布标准不再是“synthetic architecture fixture 能 PASS”，而是：

> 同一组 PIT 证据交给 Research OS 后，系统必须能产出不低于优秀人工/LLM 分析基本研究深度的专业研究结果，同时保持 PIT、lineage、可重复、可审计和 fail-closed 优势。

三家真实公司必须分别覆盖不同能力边界：

### 3.1 钢研高纳

至少形成：

- Business Model + KPI；
- Financial Time Series / Cash Flow；
- Capital Efficiency；
- Driver / Cycle / Moat semantic boundary；
- Thesis / Anti-Thesis / Falsifier；
- Forecast evidence discipline；
- Valuation Model Fitness / ranges / reconciliation；
- Sensitivity；
- Monitoring / Next Verification Event；
- Decision State + provenance；
- Research gaps。

### 3.2 中电港

必须把核心因果链变为系统产物，而不是报告层解释：

```text
Revenue growth
  -> AR / Inventory expansion
  -> Cash conversion
  -> OCF pressure
  -> Short-term debt / factoring
  -> Financing cost vs gross profit
  -> Funding Loop sustainability
  -> Growth quality / balance-sheet risk
  -> Valuation / Decision
```

### 3.3 君亭酒店

- 不得在无兼容 industry plugin 时伪造 RevPAR / ADR / OCC；
- core financial facts / cash flow / capital structure 仍应继续研究；
- `lease_heavy` 与租赁证据应进入 typed material limitation / methodology disclosure；
- 应明确“core capability 可用”与“hotel-specific KPI capability 不可用”；
- Valuation Fitness 必须能表达哪些模型因行业数据缺失而不可用；
- Next Verification Event 明确下一步需要补什么数据。

## 4. 非目标

1.6.01 不做：

- 不升级 Core API 2.0 / Plugin API 2.0 / Snapshot Schema 2.0；
- 不恢复 v1 Runtime / Reporting / Thesis / Presentation compatibility shim；
- 不把 v1.5 renderer 直接搬回 v2；
- 不在 Reporting / Presentation 重算 KPI、Funding Loop、Driver、Thesis、Expectation Gap、Valuation 或 Decision；
- 不建设新的商业数据连接器；
- 不因为缺行业插件而生成 unsupported 行业 KPI；
- 不引入 company-specific hard code；
- 不为了显示格式改变 canonical numeric value；
- 不修改历史 replay commit 或历史验收事实。

## 5. 目标架构

### 5.1 单一 canonical 研究链

```text
ResearchRunCommand
  -> BootstrapPlan
  -> ArtifactSnapshot A
  -> Strategy Resolution
  -> Professional Plan
       Strategy
       KPI
       Financial / Operating / Cash Flow
       Capital Efficiency / Funding Loop
       Drivers
       Thesis / Semantic Claims
       Expectations
       Forecast
       Peers
       Valuation Routing / Execution / Reconciliation
       Decision
       Monitoring
  -> ArtifactSnapshot B
  -> Completion
  -> Readiness
  -> ResearchRunResult
  -> HumanReadableResearchView
  -> ResearchReportDocument
  -> Markdown
  -> HTML
  -> PDF
```

Research semantics 只能在 Engine 执行的 Module 中产生。Finalizer、Presenter、Composer、Renderer 都只能投影。

### 5.2 Command-to-Artifact ownership

| Command domain | Canonical artifact | 责任模块 |
|---|---|---|
| `financial.time_series` | `financial.time_series` | `FinancialResearchModule` |
| `financial.operating_observations` | `research.operating_evidence` | `FinancialResearchModule` |
| `financial.cash_flow_quality` | `cash_flow.quality_bridge` | `FinancialResearchModule` |
| financial facts / KPI | `capital.efficiency`, `capital.funding_loop` | `CapitalResearchModule` |
| thesis inputs | `drivers.graph`, `thesis.portfolio`, `thesis.semantic_signal_assessment`, `semantic.claims` | Thesis/semantic modules |
| expectations | `expectation.snapshot`, `expectation.quality`, `expectation.gap`, `expectation.consensus_distribution` | `ExpectationResearchModule` |
| forecasting | `forecast.evaluation` | `ForecastResearchModule` |
| peers | `peers.normalized` | `PeerResearchModule` |
| valuation | `valuation.routing`, `valuation.execution`, `valuation.result`, `valuation.reconciliation` | valuation modules |
| readiness sensitivities | `scenario.sensitivities` | `SensitivityResearchModule` |
| monitoring | `monitoring.plan`, `monitoring.prior_run_review` | `MonitoringResearchModule` |
| methodology / limitations | `methodology.disclosure` | `MethodologyDisclosureModule` |
| all professional states | `decision.record`, `decision.state_provenance` | `PortfolioDecisionModule` |

模块只写自己的 artifact，不直接修改别的 domain 的结果。

## 6. M1 — Professional Runtime Completion

### 6.1 Command projection modules

优先采用“typed projection module + 已有 domain service”模式，而不是把所有逻辑堆入 `application/plan.py`。

新增 `src/research_os/application/professional_modules.py`，每个模块：

- 明确 `ModuleSpec.requires/provides`；
- 只读取对应 `ResearchRunCommand` domain input 与上游 `ResearchStateView`；
- 调已有 domain service/typed model；
- 将结果写入 `ArtifactWrite`；
- preserve evidence_refs / assumption_refs；
- 无输入时输出 `INSUFFICIENT_EVIDENCE` 或不适用的 typed value，不能虚构值。

`ResearchPlanCompiler.compile()` 负责按稳定顺序组装模块；不得把 domain 计算写在 compiler 中。

### 6.2 Financial / Capital

- `FinancialResearchModule` 投影 command 中已存在的 financial time series、operating evidence、cash-flow quality。
- `CapitalResearchModule` 消费 canonical KPI + financial/cash-flow artifacts，通过现有 capital domain service 计算 `capital.efficiency` / `capital.funding_loop`。
- 如果必要输入缺失，Artifact 必须用 typed missingness/domain_status 表达，而不是输出默认 0。

### 6.3 Thesis / Semantic

- 现有 `ThesisPortfolioModule` 保留 prior thesis portfolio 构建职责；
- cycle/moat/comparison rules 必须形成 `thesis.semantic_signal_assessment` / `semantic.claims`；
- DriverGraph 只从 canonical inputs/artifacts 组装，不在 Reporting 推导；
- Thesis/Anti-Thesis/Falsifier 必须保留 evidence/assumption lineage。

### 6.4 Expectation / Forecast / Peers

- consensus vintage/evidence/gap 必须进入 expectation artifacts；
- consensus observations 进入 `expectation.consensus_distribution`；
- forecast hypotheses 必须通过 benchmark discipline 产生 `forecast.evaluation`；
- peer comparables 归一化后写 `peers.normalized`；
- 无数据时保持 fail-closed。

### 6.5 Valuation

Valuation 必须是：

```text
Model Fitness
 -> Routing
 -> optional typed Execution
 -> Result / Ranges
 -> Reconciliation
```

- fixture/command 中已有 valuation ranges 不允许只在 acceptance 旁路使用；
- reconciliation 必须成为 `valuation.reconciliation` artifact；
- model downgrade rationale 只能使用经济适用性理由，不能引用软件版本/renderer；
- 无可比较模型时返回 typed `NOT_COMPARABLE`，不强行给区间。

### 6.6 Decision

移除当前默认状态主导的行为。

`PortfolioDecisionModule` 必须从 canonical artifacts 构造 `DecisionContext`：

- Fundamental state：来自 financial/capital/thesis typed state；
- Valuation state：来自 valuation routing/reconciliation；
- Expectation state：来自 expectation quality/gap；
- Thesis state：来自 thesis portfolio / semantic claims；
- Funding risk：来自 `capital.funding_loop`；
- Evidence confidence：来自 canonical evidence/claim inputs，而不是任意常量。

`decision.state_provenance` 必须记录实际使用的 dimension、thesis/claim keys 和 lineage。

### 6.7 Readiness

Readiness 继续由 `ResearchReadinessEvaluator` 在 Engine finalize 阶段统一评估，但专业 modules 接通后：

- substantive artifact + evidence_refs/assumption_refs 才能 PASS；
- rich input 对应维度应从 INCOMPLETE 变 PASS；
- facts-only 不得因为默认空 model 被误判 PASS；
- no-plugin 不代表 core financial dimensions 全部 INCOMPLETE。

## 7. M2 — Human-readable Reporting & Presentation

### 7.1 Presenter 不再等于 JSON serializer

保留 `HumanReadableResearchView` 为 presentation-safe typed view，但新增 artifact-specific projection registry：

```text
PresentedArtifact
  -> ArtifactPresentationProjectorRegistry
  -> curated human block
```

每个 projector 只能：

- 选择 canonical fields；
- 中文 label；
- 排序/分组；
- display formatting；
- canonical enum -> human label；
- 引用 source artifact identity/fingerprint。

禁止计算新的研究结论。

### 7.2 HumanValueFormatter

统一展示规则：

- CNY：元 / 万元 / 亿元；
- `ratio + percent`：0.050095 -> 5.01%；
- days / x：默认 2 位；
- percentage point：使用“个百分点”；
- confidence / score 按 model definition 控制精度；
- canonical Decimal/float 不变。

现有 `format_cny()` 合并到统一 formatter，不允许 renderer 内散落 ad-hoc 格式化。

### 7.3 正文结构

固定 section_id，不用中文标题做机器合同：

1. `decision-snapshot` — 投资决策快照
2. `core-judgment` — Thesis / Anti-Thesis / Falsifiers
3. `financial-kpi` — 财务与关键 KPI
4. `capital-funding` — 资本效率与 Funding Loop
5. `drivers` — Driver Graph
6. `expectation-forecast` — 市场预期与预测纪律
7. `valuation` — Valuation Fitness / Scenario / Reconciliation
8. `monitoring` — Monitoring / Next Verification
9. `research-gaps` — Evidence gaps / Material limitations
10. `audit-appendix`

没有 substantive artifact 的 section 不显示空壳。

### 7.4 Body / Audit 隔离

Investor body 禁止：

- `Schema:`；
- raw 64-char fingerprint/hash；
- raw `source_url`；
- raw `plugin_id` / Plugin API version；
- raw machine reason code；
- full `evidence.pit` recursive dump；
- full repository preflight dump。

Audit appendix 保留 canonical lineage、schema、producer、fingerprint、repository baseline。

### 7.5 HTML / PDF

- HTML layout 必须使用 `section_id`，不再按中文 title 字符串匹配；
- known section 不得 fallback `report-section-N / standard-section`；
- Markdown -> HTML -> PDF 仍为单向 deterministic presentation；
- PDF 第一页/前两页必须优先展示 decision snapshot、关键 KPI、material risks/limitations，而不是 Evidence dump。

## 8. M3 — Real-company Acceptance & Release Hardening

### 8.1 修复 acceptance oracle

`research_depth` 只能从最终 `ResearchRunResult.artifacts` 得出。

禁止：

```text
fixture -> helper reconciler -> PASS
```

必须：

```text
fixture -> ResearchApplication -> ArtifactSnapshot -> oracle
```

如果 fixture 声明 valuation depth，最终没有 valuation artifacts，则 FAIL。

### 8.2 Rich-vs-facts semantic sensitivity gate

对声明了 substantive typed input 的 fixture：

- rich 与 facts-only 的 expected affected artifact / Semantic Fingerprint 必须不同；
- 不相关字段变化不得导致不相关 artifact 漂移；
- no input 的 domain 保持 deterministic missingness。

### 8.3 Presentation quality gate

固定 real-company fixtures 的 investor body：

- `Schema:` = 0；
- raw URL = 0；
- raw 64-char hash = 0；
- raw reason code = 0；
- full evidence row dump = 0；
- known section HTML fallback = 0；
- body 行数目标 <= 350（审计附录不计；超阈值需显式 fixture waiver）；
- PDF 有效且通过 real Chromium/Playwright text/structure checks。

### 8.4 三公司研究深度 gate

#### 钢研高纳

至少验证 artifact presence/semantics：

- valuation routing/reconciliation；
- sensitivity；
- monitoring next event；
- cycle/moat semantic boundary；
- thesis/decision provenance。

#### 中电港

至少验证：

- Funding Loop；
- cash conversion / financing pressure；
- decision provenance 消费 funding risk；
- monitoring next event。

#### 君亭酒店

至少验证：

- no compatible industry plugin 仍 fail-closed；
- 不出现 unsupported hotel KPI；
- core financial facts 仍可展示；
- lease-heavy limitation 可见；
- methodology/coverage gap 可见。

### 8.5 Historical replay

v1.5.08–v1.5.12 继续 immutable isolated replay，不改变旧解释器、旧源码和旧输出。

## 9. 测试策略

### 9.1 TDD 顺序

1. 先写 RED：rich == facts-only 必须失败；synthetic valuation side-channel PASS 必须失败；
2. 接通 Professional modules；
3. Decision/Readiness RED→GREEN；
4. Human projection RED→GREEN；
5. Presentation body/audit 和 section_id RED→GREEN；
6. 三公司 real-company acceptance；
7. full release verification。

### 9.2 测试层级

- Unit：每个 module 输入/输出/lineage/missingness；
- Architecture：dependency rules、Reporting 不得导入 domain services；
- Integration：ResearchApplication full professional chain；
- Regression：三公司 artifacts/semantic fingerprint/presentation quality；
- Acceptance：current v1.6.01 + historical replay；
- Packaging：wheel install / imports / HTTP；
- Presentation：real Chromium/Playwright PDF。

## 10. 里程碑与合入边界

### M1 — Professional Runtime Completion

完成后必须：

- rich input 能产生对应 canonical artifacts；
- Decision/Readiness 消费 canonical professional artifacts；
- 三公司 machine-semantic tests 通过；
- full unit/integration/architecture tests 通过；
- 单独合入 `main`。

### M2 — Human-readable Reporting & Presentation

完成后必须：

- investor body 不再 Artifact dump；
- value formatting 统一；
- body/audit 分离；
- section_id HTML contract 生效；
- 三公司 Markdown/HTML/PDF 质量 gate 通过；
- 单独合入 `main`。

### M3 — Real-company Acceptance & Release Hardening

完成后必须：

- acceptance oracle 无 side-channel；
- 三公司真实/结构等价 fixture 进入 release gate；
- historical replay 5/5；
- full pytest / mypy / Ruff / import-linter / pip-audit / build / installed wheel / real PDF 全绿；
- 发布 Research OS `1.6.01`。

## 11. Definition of Done

1. Research OS 不再出现“直接让 LLM 写报告明显更完整，而系统只能输出 Artifact dump”的结构性失败。
2. 三公司研究深度来自 canonical Artifacts，不来自 renderer 或 acceptance helper。
3. 同一 decision_ts / evidence revision / policy / module version 可重复得到相同 semantic result。
4. 所有结论可从 Decision/Thesis/Valuation/Expectation 等反向追到 Evidence / Calculation / Assumption lineage。
5. 缺失信息继续 fail-closed；no-plugin 只限制行业专属能力，不让 core research 失效。
6. Investor report 与 Audit report 职责清晰：前者可读，后者可追溯。
7. 1.6.01 不恢复 v1 compatibility shim，不改变 Core API 2.0 public contract。

## 12. 设计约束总结

```text
Models beat simple benchmarks.
Research signal != auto trading.
No Time Travel.
Facts != Calculations != Statistical Evidence != Assumptions.
Everything Has Lineage.
Missingness is data.
Fail closed.
Canonical Artifact first; presentation never repairs missing research semantics.
```
