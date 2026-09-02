# Research OS 1.6.0 总体实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于重新核验的 `delivery_parent_sha`，完成 Core API 2.0、Plugin API 2.0、Snapshot Schema 2.0、HTTP API v1、专业研究基础模型与工程门禁，并将全部变更压缩为一个可由用户 fast-forward 到 `main` 的 Research OS 1.6.0 release commit。

**Architecture:** 保持模块化单体。Phase A/Phase B 模块计划都由唯一 `ResearchEngine` 执行；类型化 Artifact Snapshot 是运行结果、快照和报告投影的统一语义边界；插件提供领域服务；数据库、HTTP、Git 历史重放和浏览器 PDF 位于适配器层。

**Tech Stack:** Python 3.12、Pydantic 2、SQLAlchemy 2、Alembic、FastAPI、packaging、Ruff、mypy、import-linter、pytest、Hypothesis、pip-audit、Playwright、现有 statsmodels/scikit-learn。

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-6-0-architecture-convergence-design.md`

## Global Constraints

- 行为基线：`72ab06c619678b35c31cf7edef7547849e803d16`（仅为缺陷理解和历史 replay 的参考证据，不是当前 v2 兼容门禁）。
- 交付父提交：实际最新 `main` HEAD；M1 启动和最终交付前都必须重新核验并记录精确 SHA。评审时 main 为 `812b6212410723bc80ed6222b5c78bbc74917390`。
- 产品版本：`1.6.0`；Core API：`2.0`；Plugin API：`2.0`；Snapshot Schema：`2.0`；HTTP API：`v1`。
- 当前 v2 必须保留 Semantic Preservation、Claim Strength、Threshold Context 与 Valuation Reconciliation 的定义边界；历史实现和结果只在其各自提交中 replay。
- 历史 1.5.08–1.5.12 fixtures、结果和提交不得被改写。
- `src/research_os` 不得包含验收公司身份特例。
- 除 `ResearchEngine` 外，生产代码不得调用 `ResearchModule.run()`。
- Engine 返回后不得新增或覆盖 canonical semantic Artifact。
- Phase A 创建绑定 `company_id + decision_ts` 的不可变 FactView，所有 EvidenceRef 固定具体 revision 和 content fingerprint。
- M1 冻结正式 KPI Provider 签名及 ReportingPeriod/AccountingScope/MetricResult/PolicySnapshot/Registry 最小形状，M3 只能实现不改形状。
- Completion 在 Engine 末端先评估，Readiness 随后消费 Completion 和内容 Artifact；合法不完整结果为 `INCOMPLETE + NOT_READY`。
- Presentation 不得重算财务、Thesis、估值、Decision、Completion 或 Readiness。
- 不引入微服务、内部事件总线、通用工作流框架或重量级 DI 容器。
- 每个生产行为执行 RED → GREEN → REFACTOR；每个里程碑结束运行对应集成与架构测试。
- 开发可使用隔离 worktree 和本地检查点，但最终交付相对基线只能有一个 commit。

## 里程碑依赖

```text
M1 Core Runtime & Contracts
          │
          ├──────────────┐
          ▼              ▼
M2 Persistence/API   M3 Professional Foundations
          │              │
          └──────┬───────┘
                 ▼
       M4 Reporting & Replay
                 │
                 ▼
       M5 Quality & Release
```

## 交付分解

| 里程碑 | 核心输出 | 进入条件 | 退出条件 |
|---|---|---|---|
| M1 | Core API 2.0、类型化 Artifact、唯一 Engine、Plugin API 2.0、RunCommand/Result、Completion/Readiness | delivery parent 与 CI 已确认 | 只公开 v2 入口，所有 Core 契约测试和单执行器架构测试通过 |
| M2 | Snapshot 2.0、SQL Repository、UnitOfWork、HTTP API v1 | M1 ArtifactSnapshot/Result 稳定 | 重启持久化、篡改检测、保留事实的 SQL 升级、PIT 查询和 OpenAPI 契约通过 |
| M3 | 财务值对象、Metric/Policy Registry、Router、Thesis Portfolio、Valuation、Forecast、Peers、Postmortem | M1 类型化 Artifact/Plugin 服务稳定 | 专业领域单元/属性/集成测试通过，缺失与不可比继续失败关闭 |
| M4 | 稳定当前 Reporting、语义指纹、commit-addressed 历史 replay、1.6 acceptance | M1–M3 结果合同稳定 | 1.5.08–1.5.12 replay 与 1.6 Markdown/HTML/PDF 通过 |
| M5 | 工程门禁、发布元数据、单提交和完整交付包 | M1–M4 全绿 | release pipeline、包安装、安全检查和单提交验证全部通过 |

## 计划文件

- `2026-08-31-research-os-v1-6-0-m1-core-runtime-contracts.md`
- `2026-08-31-research-os-v1-6-0-m2-persistence-http-api.md`
- `2026-08-31-research-os-v1-6-0-m3-professional-research-foundations.md`
- `2026-08-31-research-os-v1-6-0-m4-reporting-replay-compatibility.md`
- `2026-08-31-research-os-v1-6-0-m5-quality-release-delivery.md`

## 全局验证命令

里程碑期间使用针对性命令；最终必须执行：

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy src/research_os/contracts src/research_os/application \
  src/research_os/runtime src/research_os/plugins src/research_os/snapshots
lint-imports
python -m pytest -q
python scripts/verify_release_pipeline.py
python -m pip_audit
python -m build
```

PDF 集成：

```bash
RESEARCH_OS_RUN_PDF_INTEGRATION=1 \
python -m pytest -q tests/unit/presentation tests/integration/presentation
```

数据库迁移：

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

## 单提交发布检查

```bash
git fetch origin main
DELIVERY_PARENT_SHA="$(git rev-parse origin/main)"
git reset --soft "$DELIVERY_PARENT_SHA"
git commit -m \
  "release: architecture convergence and professional research foundation v1.6.0"

test "$(git rev-list --count \
  "$DELIVERY_PARENT_SHA..HEAD")" = "1"
```

## Definition of Done

- [ ] 设计文档、ADR、Migration 和五个详细计划均在仓库中。
- [ ] 当前包只公开 Core API 2.0、Plugin API 2.0、Snapshot 2.0 和新的 application command/result，不含 v1 compatibility surface。
- [ ] 所有运行语义只由 Engine Module 产生。
- [ ] Snapshot 可持久化、重启读取、规范哈希和检测篡改。
- [ ] HTTP API v1 使用 Query Port 与标准 Problem Details。
- [ ] 专业研究基础合同均保留 Evidence/Assumption/Basis/Applicability。
- [ ] 当前 Reporting 不依赖补丁版本继承。
- [ ] 历史 replay 在各自 commit 中执行。
- [ ] 完整测试、静态检查、安全检查、构建和真实 PDF 通过。
- [ ] 最终相对基线只有一个 release commit。
- [ ] 交付包含 source ZIP、binary patch、git bundle、SHA256SUMS、验证报告和推送说明。
