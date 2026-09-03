# Research OS 1.6.0 M5：工程质量、发布门禁与单提交交付计划

> **For agentic workers:** M5 按 RED → GREEN → refactor 推进。过程提交只存在于 M5 feature branch；最终交付只允许一个 M5 squash commit 进入 `main`。

**Goal:** 在 M1–M4 已完成的 v1.6.0 架构上补齐工程质量、Manifest-selected release gates、依赖安全、构建/安装包验证、发布文档和可验证交付包，并保持 M1–M4 已发布 squash 历史不变。

**M5 delivery parent:** `abd19bbc7e22d7958df853333e0ba8cedff39f6f` (`feat: complete v1.6.0 M4 reporting replay compatibility`)

**Architecture:** CI 各 Job 执行独立责任；Release Gate 聚合 Release Manifest 明确选择的 M1–M5 + governance Verification Packs。Historical replay 与当前运行物理隔离。最终交付包只能从新的 `main` HEAD 生成，且必须证明 `abd19bbc..HEAD` 的 commit count 精确为 `1`。

**Tech Stack:** Ruff、mypy、import-linter、pytest、Hypothesis、pytest-cov、pip-audit、build、twine、Alembic、Playwright、Git archive/format-patch/bundle、SHA-256。

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-6-0-architecture-convergence-design.md`

## Global Constraints

- M1–M4 已完成，不重做、不重写、不把各自 feature branch 的过程提交重新合入 `main`。
- M5 feature branch 可有多个 RED/GREEN/refactor/review commit；最终使用 squash 只向 M4 `main` 增加一个 M5 commit。
- 不在 squash 前后的不同代码状态之间复用完成结论；最终 commit 生成后必须重新跑全部门禁。
- `behavior_baseline_sha=72ab06c619678b35c31cf7edef7547849e803d16` 仅为 1.5.12 缺陷理解/历史 replay 参考，不是当前 v2 兼容门禁。
- `delivery_parent_sha=abd19bbc7e22d7958df853333e0ba8cedff39f6f` 是本次 M5 的直接父提交；最终交付前必须重新获取 `origin/main` 核验。远端漂移时先审查整合，禁止覆盖。
- 不 force-push，不重写 v1.5.12 及更早历史。
- 当前进程不恢复 Core/Plugin/Snapshot/Runtime/Reporting/Thesis/Presentation v1 compatibility surface。
- 历史 1.5.08–1.5.12 只能由 registry-pinned immutable commit + isolated worktree/interpreter replay。
- Reporting/Presentation 只能投影、翻译、编排、分页和导出，不得重算研究语义。
- No Time Travel、Lineage、typed Artifact、fail-closed、structured unsupported/incomplete、Research Signal ≠ Auto Trading 均为不可弱化边界。

---

### Task 1：Ruff、mypy 与 import-linter

**Files:**
- Modify: `pyproject.toml`
- Create: `.importlinter`
- Create: `tests/regression/architecture/test_dependency_rules_v1_6.py`

- [x] 将 Ruff / import-linter / release tooling 声明为测试/发布依赖。
- [x] 配置 Ruff formatter/linter 和核心 mypy 严格边界。
- [x] import-linter：Domain/Runtime Semantics 不依赖 API/Persistence/Reporting/Presentation/Release；Reporting 不依赖 Runtime Engine。
- [ ] 所有实际 lint/type/import violations 清零，不用全局 ignore 隐藏核心问题。

### Task 2：测试体系与 M3/M5 Release Pack

**Files:**
- Modify: `src/research_os/release/verification.py`
- Modify: `src/research_os/release/manifest.py`
- Modify: release-governance tests
- Create: `tests/regression/architecture/test_release_contract_v1_6_0.py`

- [x] M3 专业研究能力建立独立 `m3-professional-foundations` verification pack。
- [x] M5 工程/发布合同建立 `m5-quality-release` verification pack。
- [x] Stable Manifest 明确选择 M1、M2、M3、M4、M5、release-governance，避免只依赖 full pytest 偶然覆盖。
- [ ] 固定 profile 的 property tests、full pytest 和 release packs 全绿。
- [ ] 对 Core Contracts/Application 执行包级 coverage 门禁并保存结果。

### Task 3：CI 分层

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `scripts/verify_release_pipeline.py`

**Jobs:**

```text
quality
unit
integration
acceptance
security-package
release-gate
```

- [x] 设置 pip cache、job timeout、concurrency cancellation。
- [x] Historical replay 所在 acceptance Job 使用完整 Git history。
- [x] Playwright/Chromium 只安装在 acceptance Job。
- [x] acceptance 独立执行当前 v1.6.0 field acceptance + v1.5.08–v1.5.12 historical replay。
- [x] security-package 独立执行 pip-audit、build、twine、clean-venv wheel smoke test。
- [x] release-gate 依赖所有前置 Job，并执行 full pytest + Manifest-selected checks。
- [ ] 分层 CI 所有 Job 实际全绿。

### Task 4：依赖安全与构建产物

**Files:**
- Create: `scripts/verify_distribution.py`
- Create: `tests/integration/package/test_installed_distribution.py`

- [x] wheel inventory 拒绝 cache、secret key、field/historical output、tests/build 临时产物。
- [x] clean virtualenv 安装 wheel 并验证 Product/Core/Plugin/Snapshot/HTTP 版本。
- [x] clean virtualenv 运行最小 Core API 2.0 synthetic run 和 HTTP API v1 OpenAPI smoke。
- [ ] `python -m pip_audit` 通过；若出现不可修复 advisory，只允许期限明确、可审计且经架构评审的豁免。
- [ ] `python -m build`、`python -m twine check dist/*`、`verify_distribution.py` 全部通过。

### Task 5：数据库与 Snapshot 发布验证

M2 已将 Schema 2.0 / SQL Persistence / Runtime Transaction / tamper detection / HTTP PIT query 纳入正式 verification pack。M5 不复制第二套数据库验证实现，而是将整个 M2 pack 作为 stable Release Manifest 的强制依赖，并在最终 release pipeline 中重新执行。

- [ ] M2 persistence/snapshot verification pack 在 M5 最终 commit 上全绿。
- [ ] migration 文档与真实 upgrade/downgrade 行为一致；旧行不被推断、重写或冒充 v2 Snapshot。

### Task 6：版本、文档和 Release Manifest

**Files:**
- Modify: `src/research_os/release/manifest.py`
- Modify: `research_os_version.json`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Finalize: `docs/architecture/adr-0002-v1-6-0-controlled-breaking-contract-upgrade.md`
- Finalize: `docs/migrations/v1.6.0.md`
- Update: v1.6.0 master/M5 plans

- [x] Release Manifest / public metadata 状态切换为 `stable`，且版本投影一致。
- [x] ADR 状态转为 Accepted，并记录 M4→M5 单提交历史规则。
- [x] README 修正 ADR 路径并记录 stable release/分层门禁/M5-only delivery。
- [ ] CHANGELOG 增加 v1.6.0 clean-break、isolated historical replay、数据库迁移与 M5 工程发布说明。
- [ ] Migration / master plan 去除“重写整个 v1.6 为一个 commit”的过时表述。
- [ ] README 三个 executable examples 在 clean environment 中执行通过。

### Task 7：预 squash 完整验证

按顺序执行并保留 CI/verification evidence：

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy src
lint-imports
python -m pytest -q
RESEARCH_OS_RUN_PDF_INTEGRATION=1 python scripts/verify_release_pipeline.py
python -m pip_audit
python -m build
python -m twine check dist/*
python scripts/verify_distribution.py dist/*.whl
git diff --check
```

- [ ] 所有命令 exit code 0。
- [ ] 当前 v1.6.0 三个 acceptance fixture 通过且是真实 Chromium PDF。
- [ ] v1.5.08–v1.5.12 historical replay 5/5 通过。
- [ ] 无 current-process legacy compatibility 泄漏、公司身份生产分支、secret、cache、临时 field fixture 进入源码包。

### Task 8：最终审计与 M5 squash

- [ ] `git fetch origin main`，再次确认远端 `main == abd19bbc7e22d7958df853333e0ba8cedff39f6f`；若漂移，先审查冲突和整合，禁止覆盖。
- [ ] 对完整 M5 diff 做设计/实现审计，确认与 M1–M4 类型/执行/语义边界一致。
- [ ] feature branch 过程历史仅作为开发证据，不逐个进入 `main`。
- [ ] 通过 squash 形成一个最终 M5 commit。
- [ ] 验证 `git rev-list --count abd19bbc..HEAD == 1`，即 `main` 相对 M4 **ahead 1**。
- [ ] 验证最终 M5 commit 的直接父提交精确为 `abd19bbc7e22d7958df853333e0ba8cedff39f6f`。

### Task 9：最终 `main` commit 后重新验证

- [ ] 新 `main` push 触发独立 CI，不复用 feature branch 结论。
- [ ] quality/unit/integration/acceptance/security-package/release-gate 全绿。
- [ ] full pytest、mypy、release verification、M5 acceptance、历史 replay、package/security 均在最终 SHA 上重新执行。
- [ ] 记录最终 HEAD SHA、测试结果和产物 hash。

### Task 10：生成用户交付包

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

- [x] 实现 `scripts/build_release_delivery.py`，只接受单 commit delivery parent。
- [x] Source ZIP 使用 `git archive`，检查无 `.git`、cache、build/dist、key material。
- [x] Patch 使用 `git format-patch -1 --stdout --binary`。
- [x] Bundle 执行 `git bundle verify`。
- [x] `SHA256SUMS` 覆盖所有交付文件并自校验。
- [x] Push instructions 明确 fast-forward only；远端漂移停止。
- [ ] 最终 `main` release-gate 实际生成并上传 delivery artifact。

### Task 11：发布完成标准

只有以下条件全部满足才能宣布 M5 完成：

- [ ] M5 计划全部完成并与 Spec/ADR/Migration/README/CHANGELOG 同步。
- [ ] 无未关闭 P0/P1、无静默跳过。
- [ ] 当前包无 v1 Runtime/Reporting/Thesis/Presentation compatibility surface。
- [ ] 1.5.08–1.5.12 immutable replay 5/5 通过。
- [ ] 当前测试、full pytest、mypy、Ruff、import-linter、release verification、真实 PDF acceptance、安全/构建/安装包验证全绿。
- [ ] M1–M4 历史不变，`main` 相对 M4 只增加一个 M5 squash commit（ahead 1）。
- [ ] 新 `main` HEAD 的独立 CI 再次全绿。
- [ ] 最终交付包和 SHA256 校验实际生成成功。
