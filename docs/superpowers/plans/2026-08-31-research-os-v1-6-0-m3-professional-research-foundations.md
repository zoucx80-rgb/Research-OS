# Research OS 1.6.0 M3：专业研究基础能力实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在类型化 Core 之上建立可复用的财务值、Metric Definition、Policy、业务模型路由、Thesis Portfolio、解释型估值、预测验证、同行可比和事后归因能力，使报告深度由规范研究 Artifact 支撑。

**Architecture:** 通用经济语义进入 shared contracts/registries；行业插件选择适用指标与方法，不复制基础公式。每项专业能力作为纯领域服务或 Engine Module 输出类型化 Artifact，缺失或不可比时失败关闭。

**Tech Stack:** Pydantic 2、Decimal、statsmodels、scikit-learn、pytest、Hypothesis。

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-6-0-architecture-convergence-design.md`

## Global Constraints

- 以当前 v2 Semantic Claims、Semantic Preservation 和 Valuation Reconciliation 为合同；`behavior_baseline_sha` 仅为缺陷理解和历史 replay 参考证据。
- 不在 Renderer 中补专业逻辑。
- 所有结论阈值来自版本化 Policy。
- 不将启发式 Rule Score 伪装为概率。
- 不因报告完整性需要而构造历史、同行、Benchmark 或 Realized Outcome。
- M1 已冻结 `ReportingPeriod`、`AccountingScope`、`MetricResult`、`PolicySnapshot`、`MetricDefinitionRegistry` Port 和正式 KPI Provider 签名；本里程碑实现值、公式和策略，不改变公共形状或 M2 Schema。

---

### Task 1：财务值对象与 Accounting Scope 实现

**Files:**
- Modify: `src/research_os/contracts/values.py`
- Modify: `src/research_os/domain/evidence.py`
- Modify: `src/research_os/domain/lineage.py`
- Create: `tests/unit/contracts/test_financial_values.py`
- Create: `tests/property/contracts/test_money_ratio_properties.py`

- [ ] 写 RED：Money 币种/尺度、Ratio 表示、Quantity 单位和 UTC 时间规则。
- [ ] 写 RED：Accounting Standard、Consolidation、Segment、Geography、Continuing Operations 可区分。
- [ ] 写 RED：不同币种或 Scope 不得直接相加/比较。
- [ ] 将所有当前财务 Artifact 替换为类型化值；不实现裸 scalar LegacyValue Adapter 或双读取表面。

### Task 2：MetricDefinitionRegistry

**Files:**
- Create: `src/research_os/metrics/__init__.py`
- Create: `src/research_os/metrics/models.py`
- Create: `src/research_os/metrics/registry.py`
- Create: `src/research_os/metrics/calculation.py`
- Modify: `src/research_os/kpi/finance_core.py`
- Modify: `src/research_os/kpi/manufacturing.py`
- Modify: `src/research_os/kpi/distributor.py`
- Create: `tests/unit/metrics/test_registry.py`
- Create: `tests/integration/metrics/test_existing_kpi_migration.py`

- [ ] 使用 M1 Task 0 的参考证据理解历史缺陷；当前 KPI contract tests 只验证 v2 公式、类型、missingness 和 lineage。
- [ ] 写 RED：同 ID 不同公式/单位/Kind/Scope 定义冲突。
- [ ] 写 RED：期间敏感 Metric 缺 ReportingPeriod 时返回 reason code。
- [ ] 注册 safe ratio、average、turnover、ROE/ROIC、working-capital 等通用定义。
- [ ] KPI Pack 改为选择 definition + 提供事实，不复制公共公式。
- [ ] 当前 v2 MetricResult 保留类型化 missingness 和 revision-bound lineage；不以 v1.5.12 API 或输出等同性作为兼容门禁。

### Task 3：PolicyRegistry

**Files:**
- Create: `src/research_os/policies/__init__.py`
- Create: `src/research_os/policies/models.py`
- Create: `src/research_os/policies/registry.py`
- Create: `src/research_os/policies/builtins.py`
- Create: `tests/unit/policies/test_registry.py`
- Create: `tests/property/policies/test_policy_fingerprint.py`

- [ ] 写 RED：Policy ID/Version 唯一，参数有类型/单位/范围。
- [ ] 写 RED：Override 必须有操作者、理由、时间和 base policy。
- [ ] 写 RED：Policy Fingerprint 与登记顺序无关。
- [ ] 迁移 Router、Expectation、Funding、Thesis、Valuation、Decision、Forecast Promotion 阈值。
- [ ] Snapshot 记录实际 Policy Fingerprint。

### Task 4：Business Model Router 2.0

**Files:**
- Modify: `src/research_os/router/models.py`
- Modify: `src/research_os/router/classifier.py`
- Create: `src/research_os/router/segments.py`
- Create: `tests/unit/router/test_classifier_v2.py`
- Create: `tests/integration/router/test_segment_routing.py`

- [ ] 固定当前支持类型的 characterization results。
- [ ] 写 RED：rule score、evidence coverage、counter evidence、ambiguity、confidence band 分开。
- [ ] 写 RED：候选差距不足时 `UNRESOLVED`，不是任意选第一名。
- [ ] 写 RED：没有校准模型时不得输出 probability 字段。
- [ ] 写 RED：Segment Profiles 不得让 secondary plugin 覆盖 primary Exclusive Artifact。
- [ ] 规则、阈值和理由由 `BusinessModelRoutingPolicy` 提供。

### Task 5：ThesisPortfolio

**Files:**
- Create: `src/research_os/thesis/portfolio.py`
- Modify: `src/research_os/thesis/models.py`
- Modify: `src/research_os/runtime/professional_modules.py`
- Create: `tests/unit/thesis/test_portfolio.py`
- Create: `tests/integration/runtime/test_thesis_portfolio_module.py`

- [ ] 写 RED：primary/supporting/conflicting/unresolved/falsified 分类。
- [ ] 写 RED：相同输入顺序变化不改变 primary selection。
- [ ] 写 RED：无足够证据时 primary 为 None。
- [ ] 复用 Claim Strength 和 Prior Thesis 生命周期，不新造第二套状态机。
- [ ] 输出 `thesis.portfolio`，旧 `thesis.items` 不再是 Core API 2.0 公共合同。

### Task 6：DecisionAggregationPolicy

**Files:**
- Create: `src/research_os/decision/aggregation.py`
- Modify: `src/research_os/decision/engine.py`
- Modify: `src/research_os/decision/models.py`
- Create: `tests/unit/decision/test_aggregation.py`
- Create: `tests/integration/runtime/test_portfolio_decision.py`

- [ ] 写 RED：Falsified Thesis 和 material funding risk 可否决高置信状态。
- [ ] 写 RED：冲突/未决 Thesis 降级到确认等待，不被取第一项覆盖。
- [ ] 写 RED：Decision Record 保存所有 used thesis/claim/evidence IDs。
- [ ] 删除 `theses[0]` 依赖。
- [ ] 时间只来自 `decision_ts`/Clock Port。

### Task 7：解释型 Valuation Method 与 Fitness

**Files:**
- Create: `src/research_os/valuation/methods.py`
- Modify: `src/research_os/valuation/fitness.py`
- Modify: `src/research_os/valuation/router.py`
- Modify: `src/research_os/valuation/execution.py`
- Modify: `src/research_os/valuation/reconciliation.py`
- Create: `tests/unit/valuation/test_method_fitness_v2.py`
- Create: `tests/integration/runtime/test_valuation_pipeline_v2.py`

- [ ] 为 v2 reconciliation 的统一估值状态和经济理由建立不可回归测试；历史结果仅由历史 replay 验证。
- [ ] 写 RED：`SUPPORTED`/`CONDITIONALLY_SUPPORTED`/`SANITY_CHECK_ONLY`/`CONTRAINDICATED`/`INSUFFICIENT_EVIDENCE` 状态。
- [ ] 写 RED：每个状态必须有经济 reason codes；版本号不得进入 analytical rationale。
- [ ] 写 RED：不同 basis/role 继续由 Reconciler 返回 disagreement/not comparable。
- [ ] 首批方法仅实现输入合同充分的 PE/PB/DCF/SOTP Adapter；缺输入时不生成数值。
- [ ] 保留 Bear/Base/Bull、Assumption、Sensitivity、Lineage 和 Limitation。

### Task 8：Forecast Evaluation 与 Benchmark Registry

**Files:**
- Create: `src/research_os/forecasting/benchmarks.py`
- Create: `src/research_os/forecasting/backtest.py`
- Create: `src/research_os/forecasting/model_card.py`
- Modify: `src/research_os/forecasting/promotion.py`
- Create: `tests/unit/forecasting/test_benchmarks.py`
- Create: `tests/integration/forecasting/test_time_series_backtest.py`

- [ ] 写 RED：记录 `train_cutoff`、每个 fold 的 feature availability、label maturity 和 `evaluation_ts`；post-cutoff observation 进入训练失败。
- [ ] 写 RED：realized outcome 仅在 label maturity 后进入历史 evaluation，不能成为当时 feature。
- [ ] 写 RED：没有登记 Benchmark 或样本外结果不能晋级。
- [ ] 写 RED：time-series split 保持时间顺序，禁止随机 shuffle。
- [ ] 写 RED：MAE/RMSE/方向准确率、interval coverage 和稳定性窗口有 evidence lineage。
- [ ] 复用 sklearn split/metrics 与 statsmodels，不自行实现统计模型。
- [ ] Model Card 保存 features、target、train cutoff、fold availability、label maturity、evaluation timestamp、environment、limitations。

### Task 9：Peer Comparability

**Files:**
- Create: `src/research_os/peers/comparability.py`
- Modify: `src/research_os/peers/models.py`
- Modify: `src/research_os/peers/normalization.py`
- Create: `tests/unit/peers/test_comparability.py`
- Create: `tests/integration/peers/test_peer_normalization.py`

- [ ] 写 RED：币种、财年、准则、Scope、租赁、一次性项目、股本、估值日期不一致。
- [ ] 区分 `COMPARABLE`、`ADJUSTMENT_REQUIRED`、`NOT_COMPARABLE`、`INSUFFICIENT_EVIDENCE`。
- [ ] 只有显式调整输入才能生成 Normalized Comparable；不能猜汇率或租赁调整。
- [ ] 保存选择理由和排除理由，避免生存偏差被隐藏。

### Task 10：Postmortem Attribution

**Files:**
- Create: `src/research_os/monitoring/attribution.py`
- Modify: `src/research_os/monitoring/postmortem.py`
- Create: `tests/unit/monitoring/test_attribution.py`
- Create: `tests/integration/monitoring/test_prior_run_postmortem.py`

- [ ] 写 RED：DATA/BASIS/FORMULA/MODEL/ASSUMPTION/DRIVER/TIMING/EXOGENOUS/PRESENTATION 分类。
- [ ] 每个归因引用 prior statement、realized evidence 和分析方法。
- [ ] 外生事件与模型误差分离；证据不足时 UNKNOWN。
- [ ] Process Change Candidate 必须指向具体 Policy/Metric/Procedure。

### Task 11：M3 出口门禁

- [ ] 现有 Manufacturing/Distributor golden 数值无意外漂移。
- [ ] v2 语义保持和估值对账测试全绿；历史 1.5.12 行为由 isolated replay 验证。
- [ ] 新值对象/Metric/Policy/Router/Thesis/Decision/Valuation/Forecast/Peer/Postmortem 测试全绿。
- [ ] 运行 Hypothesis 属性测试。
- [ ] 确认任何缺失、不可比或无 Benchmark 场景都不产生伪专业结论。
- [ ] 不创建 release commit。
