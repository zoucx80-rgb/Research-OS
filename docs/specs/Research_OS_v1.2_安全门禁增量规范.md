# Research OS v1.2 安全门禁增量规范

**版本：** 1.2.0  
**日期：** 2026-08-29  
**基线：** `Research_OS_v1.1_完整规范.md`  
**性质：** 向后兼容的 MINOR 增量规范；未被本文件修改的 v1.1 规范继续有效。

## 1. 升级目标

v1.2 将真实研究运行中暴露的“流程完成但研究不完整、财务数量级污染、预期证据缺失、估值声明与执行不一致、非法决策状态、证据 lineage 不能持久化”等问题，从提示词约束升级为可测试、可拒绝、可追踪的运行时契约。

核心原则不变：

- No Time Travel
- No Fabricated Data
- Facts ≠ Calculations ≠ Statistical Evidence ≠ Assumptions
- Everything Has Lineage
- Models Beat Simple Benchmarks
- Research Signal ≠ Auto Trading
- 历史 snapshot 与历史 release tag 不可改写

## 2. Repository Preflight

研究运行必须绑定唯一仓库身份：

- `repository_full_name = zoucx80-rgb/Research-OS`
- `repository_id = 1350382205`
- `branch = main`

运行前冻结真实 40-hex HEAD SHA，并校验 `AGENTS.md` 与 canonical research prompt 的 blob SHA/读取 ref。占位 SHA、仓库错配、分支错配、文件 ref 未绑定冻结 HEAD 均为硬失败。

## 3. Evidence Lineage

`Evidence` 在保留 v1.1 `value` 的同时新增并持久化：

- `raw_value`
- `normalized_value`
- `period`
- `version`

新增：

- `CalculationLineage(formula, input_evidence_ids, output, unit, calculation_version)`
- `AssumptionLineage(label="ASSUMPTION", value, unit, rationale, source_evidence_ids)`

Alembic `0003_v1_2_evidence_lineage` 在 `evidence` 表增加 `raw_value_json`、`normalized_value_json`、`period`、`version`，并要求数据库 round-trip 不丢失这些字段。

## 4. Financial Sanity Gate

统一归一化 `元 / 千元 / 万元 / 百万元 / 亿元`，并对关键财务关系执行硬校验，包括：

- Gross Profit = Revenue - COGS
- Gross Margin = Gross Profit / Revenue
- YoY = Current / Previous - 1
- Market Cap = Shares Outstanding × Price
- Target Price = Scenario Market Cap / Shares Outstanding
- 同一 metric / period / scope / version 的数值冲突
- 常见 ×10 / ×100 / ×10000 数量级污染

Financial Sanity 为 valuation、decision、final completion 的前置硬门禁；FAIL 不得降级为 warning。

## 5. Expectation Evidence Gate

任何 beat / miss / priced-in / expectation-gap 等市场预期结论必须具备可审计 baseline，至少包含：来源、发布时间、预期周期、metric、expected、actual、surprise、vintage id，且 expectation publish timestamp 不得晚于 `decision_ts`。

缺少 baseline 且未声称预期结论时，状态为 `INSUFFICIENT_EVIDENCE`，不得用增长率或叙事推断替代。

## 6. Valuation Execution Gate

估值执行必须记录：

- selected model
- model fitness score / selection reason
- executed model
- inputs / assumptions / scenario logic
- lineage
- driver bridge

硬规则：`selected_model == executed_model`。Distributor 场景应能追踪主要因果链：

`Revenue → Gross Profit → Working Capital → Financing Requirement → Financing Cost → Credit / Inventory Loss → Net Profit / Cash Economics → Valuation`

不兼容估值模型不得机械平均；证据不足必须降低 fitness 或显式标注不足。

## 7. Decision State Gate

唯一合法决策状态来自现有 `ResearchDecisionState`：

- HIGH_CONVICTION_WATCH
- ACCUMULATION_CANDIDATE
- WAIT_FOR_CONFIRMATION
- HOLD_AND_MONITOR
- RISK_REVIEW
- THESIS_BROKEN
- INSUFFICIENT_EVIDENCE

不得引入平行 enum。`NEUTRAL` 等未声明状态为非法。

## 8. Research Completion Gate

模块状态仅允许：

- PASS
- FAIL
- INSUFFICIENT_EVIDENCE
- NOT_APPLICABLE

最终状态仅允许：

- `FINAL_STATUS=COMPLETE`
- `FINAL_STATUS=INCOMPLETE`

工具、网页、agent 或 orchestration 的技术执行结束，不等于研究完成。Final completion 由 Completion Gate 独立决定。

必查模块覆盖 Repository Preflight、PIT、Evidence Lineage、Financial Sanity、Router/KPI、Capital/Funding、Driver/Thesis/Anti-Thesis/Falsifiers、Expectation Evidence、Forecast Discipline、Valuation Fitness/Execution、Decision State、Next Verification Event、Temporal Consistency。

## 9. Reporting Contract

`DecisionSummary` 增加：

- `decision_state`
- `final_status`
- `expectation_evidence_status`
- `valuation_execution_status`

当 `final_status=COMPLETE` 时：

- decision state 必须属于合法 `ResearchDecisionState`；
- expectation evidence 必须通过；
- valuation execution 必须通过。

`INCOMPLETE` 报告可以明确显示 `INSUFFICIENT_EVIDENCE`，但不得伪装成已验证结论。

## 10. Temporal Consistency

Next Verification Event 若带日期，必须晚于 reference time；本轮已使用的证据事件不能同时被描述为未来验证事件。已披露报告不得再次列为未来检查点。

## 11. Distributor KPI 增量

在输入存在时补充并保留 evidence dependencies：

- Inventory Turns
- Gross Profit / Working Capital
- Working Capital Intensity
- Financing Cost / Gross Profit
- Credit Impairment / Gross Profit
- Inventory Impairment / Gross Profit
- Revenue Growth vs Working Capital Growth
- Funding Loop linkage
- ROIC
- Incremental ROIC

缺失输入保持缺失，不生成伪数值。

## 12. Release Gate

v1.2 Release Gate 除既有 PIT/golden/router/thesis/ledger/valuation/decision/snapshot 测试外，必须包含：

- repository_preflight
- evidence_lineage
- financial_sanity
- expectation_evidence
- valuation_execution
- decision_validation
- completion_gate
- temporal_consistency
- distributor_kpi_safety
- research_completion_integration
- migration_lineage

CI 必须先显式执行 v1.2 lineage migration smoke，再执行完整 `pytest -q` 和 Release Gate。

## 13. 关键回归样本

必须持续阻断：

1. 655.25 亿元收入、634.01 亿元 COGS 却声明毛利 2.123 亿元；
2. 2.123 / 655.25 却声明毛利率 3.24%；
3. 759,900,097 股 × 23 元却声明市值约 16 亿元；
4. 当前/上期收入与声明 YoY 不一致；
5. 同一 metric/period/scope/version 出现 115.2 亿元与 11.52 亿元冲突；
6. 无 expectation baseline 却声称 beat expectations；
7. 缺 expectation evidence 且无强行结论时返回 `INSUFFICIENT_EVIDENCE`；
8. selected PS / executed PE；
9. decision state `NEUTRAL`；
10. 工具结束但 required valuation 未完成却声明 COMPLETE；
11. 已使用的 interim report 被列为未来 verification event；
12. placeholder SHA；
13. preflight 文件 ref 未绑定冻结 HEAD；
14. Evidence raw/normalized/period/version 数据库存取丢失。

## 14. 版本与迁移

本次新增公开运行时契约和方法论门禁，属于 SemVer MINOR：`1.2.0`。数据库迁移见 `docs/migrations/v1.1-to-v1.2.md`。历史 `v1.1.0`、历史 snapshot、历史事实保持不可变。
