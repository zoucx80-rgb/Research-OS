# Research OS 1.6.0 M5：工程质量、发布门禁与单提交交付计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将全部 1.6.0 变更纳入可重复验证的工程门禁，完成版本元数据、数据库/包/隔离历史回放/真实 PDF 验证，并生成相对重新核验的 `delivery_parent_sha` 只有一个 commit 的用户推送包。

**Architecture:** CI 各 Job 执行独立责任，Release Gate 只聚合已登记 Verification Packs。最终工作树先验证，再 squash 为一个 release commit，之后在该最终 commit 上重新完整验证并生成包。

**Tech Stack:** Ruff、mypy、import-linter、pytest、Hypothesis、pip-audit、build、twine check、Alembic、Playwright、Git format-patch/bundle、SHA-256。

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-6-0-architecture-convergence-design.md`

## Global Constraints

- 不以“单元测试通过”代替完整发布验证。
- 不在 squash 前后的不同代码状态之间复用测试结论。
- 最终 commit 生成后必须重新运行全部门禁。
- `behavior_baseline_sha=72ab06c619678b35c31cf7edef7547849e803d16` 仅为缺陷理解和历史 replay 的参考证据，不是当前 v2 兼容门禁；`delivery_parent_sha` 是实际 main 父提交，最终交付前必须重新核验，远端继续前进时先核对、整合并更新记录。
- 远端 main 漂移且未完成整合时停止，不覆盖新提交。
- 不 force-push，不重写 v1.5.12 及更早历史。

---

### Task 1：Ruff、mypy 与 import-linter

**Files:**
- Modify: `pyproject.toml`
- Create: `.importlinter`
- Create: `tests/regression/architecture/test_dependency_rules_v1_6.py`

- [ ] 配置 Ruff formatter/linter，排除生成/冻结历史 worktree 产物。
- [ ] mypy 对 contracts/application/runtime/plugins/snapshots 使用严格设置；其他包逐步启用。
- [ ] import-linter 合同：Domain 不依赖 API/Persistence/Reporting/Presentation/Release；Reporting 不依赖 Domain Engine；Release 不被 Research Semantics 依赖。
- [ ] 清除 lint/type/import violations，不通过全局 ignore 隐藏核心问题。

### Task 2：测试体系整理

**Files:**
- Reorganize only as required: `tests/unit`, `tests/contract`, `tests/property`, `tests/integration`, `tests/regression`
- Modify: `pyproject.toml`

- [ ] 删除只因版本字符串不同而复制的当前测试；历史行为由 replay 负责。
- [ ] 低层不变量只在最窄层测试，高层验证协作结果。
- [ ] 配置 coverage，Core 契约与 Application 设较高包级门槛，不以一个全局数字掩盖薄弱包。
- [ ] 所有 property tests 在固定 profile 下可重复运行。

### Task 3：CI 分层

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `scripts/verify_release_pipeline.py`
- Modify: `src/research_os/release/verification.py`
- Create/Modify: release tests

**Jobs:**

```text
quality
unit
integration
acceptance
security-package
release-gate
```

- [ ] 设置 pip/cache、job timeout、concurrency cancellation。
- [ ] Historical replay 所在 Job 使用完整 Git history。
- [ ] PDF 浏览器安装只在 acceptance Job。
- [ ] Release Gate 依赖前述 Job 成功并执行 Manifest-selected checks。
- [ ] 上传 1.6 acceptance、verification report、wheel/sdist 和 SBOM/依赖审计结果。

### Task 4：依赖安全与构建产物

**Files:**
- Modify: `pyproject.toml`
- Create: `scripts/verify_distribution.py`
- Create: `tests/integration/package/test_installed_distribution.py`

- [ ] `python -m pip_audit` 通过；无法修复的 advisory 必须有有期限的、可审计豁免文件。
- [ ] `python -m build` 生成 wheel/sdist。
- [ ] `python -m twine check dist/*` 通过。
- [ ] 在干净虚拟环境安装 wheel，验证 version、Core API、Plugin API、Snapshot Schema、API app import 和最小 synthetic run。
- [ ] 确认 package data 包含必要 Schema/资源，但不包含缓存、私钥或现场报告。

### Task 5：数据库和 Snapshot 发布验证

- [ ] 从真实 1.5.12 migration head 复制数据库，执行 upgrade。
- [ ] 验证旧 Evidence 行数、hash 和查询结果不变。
- [ ] 写入 1.6 Run/Snapshot，重启进程后读取和 verify。
- [ ] 篡改 payload、version、fingerprint 各一次，验证失败关闭。
- [ ] downgrade/upgrade 行为与 migration 文档一致。

### Task 6：版本、文档和 Release Manifest

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `src/research_os/release/manifest.py`
- Modify: `research_os_version.json`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Finalize: `docs/architecture/adr-0002-v1-6-0-controlled-breaking-contract-upgrade.md`
- Finalize: `docs/migrations/v1.6.0.md`
- Create: `tests/regression/architecture/test_release_contract_v1_6_0.py`

- [ ] ADR 状态转为 Accepted。
- [ ] Manifest 组件版本与实际类/模块版本一致。
- [ ] Public metadata 等于 Manifest projection。
- [ ] CHANGELOG 明确 clean-break 升级、isolated historical replay 和数据库迁移。
- [ ] README 示例全部可执行。

### Task 7：预提交完整验证

按顺序执行并保存完整输出：

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy src/research_os/contracts src/research_os/application \
  src/research_os/runtime src/research_os/plugins src/research_os/snapshots
lint-imports
python -m pytest -q
RESEARCH_OS_RUN_PDF_INTEGRATION=1 python scripts/verify_release_pipeline.py
python -m pip_audit
python -m build
python -m twine check dist/*
python scripts/verify_distribution.py dist/*.whl
```

- [ ] 每个命令 exit code 0；保存测试数、时间和 artifact 路径。
- [ ] 人工抽查三个 1.6 PDF 和每个历史 replay summary。
- [ ] `git diff --check` 和 secret scan 通过。

### Task 8：压缩为唯一 release commit

- [ ] `git fetch origin main` 并核对当前远端 HEAD 与 M1 记录的 delivery parent；若继续前进则先审查整合。
- [ ] 保存工作树备份和预 squash diff。
- [ ] 保留已发布设计提交，在核验后的 delivery parent 上整理 staged files；不得 reset 到 behavior baseline 或改写历史。
- [ ] 创建唯一 commit：

```text
release: architecture convergence and professional research foundation v1.6.0
```

- [ ] 验证 delivery parent 到 HEAD 的 commit count 精确为 1。
- [ ] 验证最终父提交精确为核验后的 delivery parent，历史 release SHA 不变且远端 main 是 HEAD 的祖先。

### Task 9：最终 commit 后重新验证

- [ ] 从最终 commit 创建全新临时 clone/worktree。
- [ ] 重新执行 Task 7 的所有命令，不能使用 squash 前结论。
- [ ] 记录最终 HEAD SHA、测试结果和产物 hash。

### Task 10：生成用户推送包

**Output:**

```text
Research-OS-v1.6.0-delivery/
  Research-OS-v1.6.0-source.zip
  Research-OS-v1.6.0.patch
  Research-OS-v1.6.0.bundle
  SHA256SUMS
  BASELINE.json
  VERIFICATION.md
  PUSH-INSTRUCTIONS.md
```

- [ ] Source ZIP 从最终 commit 导出，不包含 `.git`、cache、build 临时文件。
- [ ] Patch 使用 `git format-patch -1 --stdout --binary`。
- [ ] Bundle 包含基线和最终 commit，执行 `git bundle verify`。
- [ ] `SHA256SUMS` 覆盖所有交付文件并自校验。
- [ ] Push instructions 只允许 fast-forward；远端漂移时停止。
- [ ] 最终包再次解压并运行 manifest/hash 检查。

### Task 11：发布完成标准

- [ ] 所有需求可追溯到 Spec、Task、Test 和 Verification Evidence。
- [ ] 无未关闭的 P0/P1、无未完成占位标记、无静默跳过。
- [ ] 无 secret、公司特例、临时 fixture 或缓存进入源码包。
- [ ] 历史 1.5.08–1.5.12 不被修改且 replay 通过。
- [ ] 用户拿到包后只需应用一个 commit 并 `git push origin main`。
