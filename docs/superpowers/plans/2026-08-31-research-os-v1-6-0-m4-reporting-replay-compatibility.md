# Research OS 1.6.0 M4：当前 Reporting 与隔离历史重放实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Core API 2.0 的类型化结果无损投影为当前专业报告，移除活跃补丁版本继承，并在各自 release commit 中隔离重放 1.5.08–1.5.12 历史研究。

**Architecture:** 当前 Reporting 使用稳定文件名和组合策略；历史代码不被当前 Python import。HistoricalReplayExecutor 使用 Git detached worktree 运行历史提交。现有 Document→Markdown→HTML→PDF 哈希链保持不变。

**Tech Stack:** Pydantic 2、现有 Reporting/Presentation、Git worktree、Playwright、pytest。

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-6-0-architecture-convergence-design.md`

## Global Constraints

- Presentation 只格式化，不推导研究语义。
- 当前 v2 Semantic Fingerprint 保留所需研究语义；历史指纹仅由历史提交的 replay 验证。
- 历史 replay 不修改历史 fixtures，不读取 1.6 当前实现。
- 当前源码不复制完整历史实现。
- 历史 replay 必须隔离目标 worktree 的解释器、依赖和 `sys.path`，清理/绑定 `GITHUB_SHA`，并断言导入路径、产品/API 版本和 Git HEAD 与 Profile 一致；无依赖锁时不声称字节级重现。
- M1 clean-break 删除 v1 runtime 后，旧的当前进程 runtime/reporting/presentation 测试不属于 M1 development gate；M4 必须将其替换为 v2 测试或删除，禁止为恢复旧测试收集而添加兼容 shim，并在 M4 出口恢复当前完整测试集可收集。

---

### Task 1：登记历史 replay 参考证据

**Files:**
- Create: `tests/fixtures/historical_replay/v1_5_12/report_reference/*.json`
- Create: `tests/regression/replay/test_v1_5_12_reference.py`

- [ ] 读取 M1 Task 0 已生成的匿名 historical reference 及其来源 SHA；不得在 M4 重新生成或改变该参考。
- [ ] 将 Semantic Preservation、Claim、Threshold、Sensitivity、Valuation Reconciliation 和 Audit Appendix 关系用于解释历史重放偏差，不把它们作为当前 v2 输出等同性门禁。

### Task 2：稳定当前 ResearchViewPresenter

**Files:**
- Refactor: `src/research_os/reporting/research_view.py`
- Remove active imports from: `src/research_os/reporting/research_view_v1_5_*.py`
- Modify: `src/research_os/reporting/__init__.py`
- Create: `tests/unit/reporting/test_research_view_v1_6.py`

- [ ] 写 RED：Presenter 只接受 Core API 2.0 Result/ArtifactSnapshot。
- [ ] 写 RED：Presenter 只能消费 revision-bound Artifact lineage，不得通过 evidence ID 重新查询未来 revision。
- [ ] 写 RED：所有语义限定词、Schema、Provider、Evidence lineage 保留。
- [ ] 写 RED：不导入 Thesis/Decision/Valuation Engine。
- [ ] 在稳定 `research_view.py` 实现当前 v2 展示合同，不通过历史类继承或复制历史实现。

### Task 3：稳定 Composer 与 Markdown Renderer

**Files:**
- Refactor: `src/research_os/reporting/composer.py`
- Refactor: `src/research_os/reporting/markdown_renderer.py`
- Remove active exports from: `composer_v1_5_*.py`, `markdown_renderer_v1_5_*.py`
- Create: `tests/unit/reporting/test_composer_v1_6.py`
- Create: `tests/unit/reporting/test_markdown_v1_6.py`

- [ ] 写 RED：Composer 不接受 Raw Result 或 dict。
- [ ] 写 RED：Markdown 不计算交集、方向、阈值性质或 Decision。
- [ ] 写 RED：正文不泄漏 `None`，审计 ID 不污染投资者正文。
- [ ] 复用 Document Block，不为 1.6 复制整套 renderer。

### Task 4：Semantic Preservation 2.0

**Files:**
- Modify: `src/research_os/semantics/preservation.py`
- Modify: `src/research_os/runtime/semantic_preservation.py`
- Create: `tests/integration/reporting/test_semantic_fingerprint_v1_6.py`

- [ ] 指纹输入改为类型化 Artifact Envelope 的 ID/Schema/Provider/Evidence/Payload。
- [ ] Result/View/Document 三层指纹必须一致；任一缺失失败关闭。
- [ ] 写 RED：研究语义指纹排除 run_id/snapshot_id/created_at/展示格式；相同研究输入不同 run ID 指纹相同，完整性指纹覆盖完整 envelope。
- [ ] Display-only 格式化字段不进入语义指纹，避免格式变更污染研究语义。
- [ ] 验证当前 v2 sensitivity/monitoring qualifier 的 typed Artifact lineage。

### Task 5：Presentation Bundle 回归

**Files:**
- Modify only when required: `src/research_os/presentation/*`
- Create: `tests/integration/presentation/test_pipeline_v1_6.py`

- [ ] 验证 Document→Markdown→HTML→PDF source_hash 链。
- [ ] 验证 CJK 字体、A4 分页、长表和审计附录。
- [ ] 保持 HTML/PDF Adapter 版本不变，除非接口或输出合同实际改变。
- [ ] 使用真实 Chromium 执行 integration，不用假 PDF 替身作为发布证据。

### Task 6：Commit-addressed Historical Replay

**Files:**
- Modify: `src/research_os/release/replays.py`
- Create: `src/research_os/release/historical_executor.py`
- Modify: `scripts/verify_release_pipeline.py`
- Modify: `.github/workflows/ci.yml`
- Create: `tests/unit/release/test_historical_executor.py`
- Create: `tests/regression/architecture/test_historical_isolation_v1_6.py`

**Interfaces:**

```python
class ReplayProfile(BaseModel):
    profile_id: str
    source_commit_sha: str
    runner_script: str
    fixture_dir: str
    expected_product_version: str
    frozen: bool
```

- [ ] 为每个 1.5.08–1.5.12 Profile 登记 release commit SHA。
- [ ] 写 RED：历史 Profile 不能指向当前 working tree 或 current module builder。
- [ ] 写 RED：Executor 在 temp worktree 运行 runner、复制产物并清理。
- [ ] 写 RED：父进程已 editable 安装当前包且设置当前 `GITHUB_SHA` 时，历史 replay 仍从目标 worktree 导入并报告历史产品/API/Git SHA；导入不符时失败，异常时清理 worktree。
- [ ] CI checkout 改为 `fetch-depth: 0`，仅此架构升级允许调整 topology。
- [ ] Executor 显式传入 Profile SHA、解释器和依赖约束，启动后断言 `research_os.__file__` 位于目标 worktree。
- [ ] 删除当前运行对 `historical_professional_modules_v1_5_x.py` 的 import 依赖。
- [ ] 历史源码指纹由历史提交自身保证，不再要求当前源码与历史源码相同。

### Task 7：1.6.0 Field Acceptance

**Files:**
- Create: `scripts/render_field_acceptance_v1_6_0.py`
- Create: `tests/fixtures/field_acceptance/v1_6_0/manufacturing_typed_architecture.json`
- Create: `tests/fixtures/field_acceptance/v1_6_0/distributor_funding_and_valuation.json`
- Create: `tests/fixtures/field_acceptance/v1_6_0/coverage_limited_no_plugin.json`
- Create: `tests/integration/presentation/test_field_acceptance_v1_6_0.py`

- [ ] 三个匿名 fixture 覆盖 Manufacturing、Distributor、无插件覆盖。
- [ ] 验证 Core API 2.0 Artifact Schema、Plugin API 2.0、Snapshot 2.0 和 Readiness。
- [ ] 验证 Semantic Preservation、Thesis Portfolio、Valuation Reconciliation。
- [ ] 生成并检查 Markdown/HTML/真实 PDF。
- [ ] Field acceptance 同时记录 machine_semantics、research_depth、presentation 三类状态。

### Task 8：迁移文档和调用示例

**Files:**
- Create/Modify: `docs/migrations/v1.6.0.md`
- Create: `docs/architecture/plugin-authoring-v2.md`
- Modify: `README.md`
- Modify: `docs/prompts/stock_research.md`
- Create: `examples/core_api_v2_run.py`
- Create: `examples/plugin_api_v2.py`
- Create: `examples/http_api_v1.py`

- [ ] 示例使用匿名 synthetic 数据并可由测试执行。
- [ ] 文档明确 Product 1.6.0 与 Core/Plugin 2.0 的版本关系。
- [ ] 文档明确当前包不读取或转换旧 Snapshot，且历史 replay 与当前重新研究的区别。

### Task 9：M4 出口门禁

- [ ] 当前 Reporting/Presentation 单元和集成测试通过。
- [ ] Semantic Fingerprint 三层一致。
- [ ] 1.5.08–1.5.12 在各自 commit 的历史 replay 通过。
- [ ] 1.6.0 三个 acceptance fixture 通过。
- [ ] 当前源码不 import/继承历史 presenter/composer/renderer/runtime。
- [ ] 不创建 release commit。
