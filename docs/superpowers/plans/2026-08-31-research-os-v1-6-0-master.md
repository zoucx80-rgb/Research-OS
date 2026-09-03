# Research OS 1.6.0 总体实施计划

**Goal:** 完成 Core API 2.0、Plugin API 2.0、Snapshot Schema 2.0、HTTP API v1、专业研究基础、单向 Reporting/Presentation、隔离历史 replay 与工业级发布门禁。

**Architecture:** 模块化单体。Phase A/Phase B 模块计划都由唯一 `ResearchEngine` 执行；类型化 `ArtifactSnapshot` 是运行结果、快照和报告投影的统一语义边界；插件提供领域服务；数据库、HTTP、Git historical replay 和浏览器 PDF 位于适配器层。

**Target:** Research OS `1.6.0` / Core API `2.0` / Plugin API `2.0` / Snapshot Schema `2.0` / HTTP API `v1`。

## 不可变边界

- `behavior_baseline_sha=72ab06c619678b35c31cf7edef7547849e803d16` 仅用于 1.5.12 characterization 和 historical replay，不是 v2 兼容门禁。
- 所有事实读取经过绑定 `company_id + decision_ts` 的不可变 `FactView`；`EvidenceRef` 固定 revision + content fingerprint。
- 除 `ResearchEngine` 外，生产代码不得执行 `ResearchModule.run()`；Engine 返回后不得补写 canonical semantic Artifact。
- Completion 先于 Readiness；Finalizer 只投影，不产生研究语义。
- Presentation 不得重算财务、KPI、Funding Loop、Driver/Thesis、Expectation Gap、Forecast、Valuation、Decision、Completion、Readiness、Sensitivity 或 Monitoring。
- 当前包不含 v1 Runtime/Plugin/Snapshot/Reporting/Thesis/Presentation compatibility surface。
- historical v1.5.08–v1.5.12 只在 exact commit + detached worktree + isolated interpreter/environment 中 replay。
- 不引入微服务、内部 Event Bus、通用工作流框架或重量级 DI。
- No Time Travel、Facts/Calculations/Statistical Evidence/Assumptions 分层、Everything Has Lineage、Models Beat Simple Benchmarks、Research Signal ≠ Auto Trading、fail-closed、typed Artifact、structured unsupported/incomplete 均不可弱化。

## 里程碑状态与历史

```text
M1 Core Runtime & Contracts
    ↓ squash commit 3d41b080a53505621f8078139fdbb2b45c3dcf88
M2 Persistence & HTTP API
    ↓ squash commit 2848a7e768aa12edcdf2e7a90cb3ba5232646f55
M3 Professional Research Foundations
    ↓ squash commit 8b6e01bfbee06b6ae1a3fe1ac9c728769a2b19c9
M4 Reporting / Presentation / Historical Replay
    ↓ squash commit abd19bbc7e22d7958df853333e0ba8cedff39f6f
M5 Quality & Release
    ↓ exactly one final squash commit
stable v1.6.0 main
```

M1–M4 已完成并保持原历史。M5 不重新 squash 整个 v1.6.0，不把 M1–M4 feature branch 的过程提交重新合入 `main`。M5 的 direct delivery parent 固定为 `abd19bbc7e22d7958df853333e0ba8cedff39f6f`，最终 `main` 必须相对该 SHA **ahead 1**。

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

| 里程碑 | 核心输出 | 状态 |
|---|---|---|
| M1 | Core API 2.0、typed Artifact、唯一 Engine、Plugin API 2.0、Completion/Readiness | 完成 |
| M2 | Snapshot 2.0、SQL Repository/UoW、HTTP API v1、PIT query/tamper detection | 完成 |
| M3 | Financial values、Metric/Policy Registry、Router、Thesis Portfolio、Valuation、Forecast、Peers、Postmortem | 完成 |
| M4 | Current Reporting/Presentation、Semantic Preservation、commit-addressed replay、v1.6 field acceptance | 完成 |
| M5 | Ruff/mypy/import boundaries、M3/M5 release packs、分层 CI、security/package verification、stable metadata、single-commit delivery | 进行中，完成后发布 |

## 计划文件

- `2026-08-31-research-os-v1-6-0-m1-core-runtime-contracts.md`
- `2026-08-31-research-os-v1-6-0-m2-persistence-http-api.md`
- `2026-08-31-research-os-v1-6-0-m3-professional-research-foundations.md`
- `2026-08-31-research-os-v1-6-0-m4-reporting-replay-compatibility.md`
- `2026-08-31-research-os-v1-6-0-m5-quality-release-delivery.md`

## Stable release verification

最终 M5 commit 必须执行：

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

Release Manifest 必须明确选择 M1、M2、M3、M4、M5、release-governance packs。CI 分为 `quality`、`unit`、`integration`、`acceptance`、`security-package`、`release-gate`；真实 Chromium PDF 与 historical replay 位于 acceptance；wheel/sdist、dependency audit、twine 和 clean-venv installed-wheel smoke 位于 security-package；release-gate 依赖全部前置 job。

## M5 单提交发布检查

发布前重新获取远端：

```bash
git fetch origin main
test "$(git rev-parse origin/main)" = \
  "abd19bbc7e22d7958df853333e0ba8cedff39f6f"
```

feature branch 可有过程提交，但 merge 到 `main` 时只产生一个 squash commit。最终必须满足：

```bash
test "$(git rev-parse HEAD^)" = \
  "abd19bbc7e22d7958df853333e0ba8cedff39f6f"
test "$(git rev-list --count \
  abd19bbc7e22d7958df853333e0ba8cedff39f6f..HEAD)" = "1"
```

如果远端 `main` 已漂移，停止直接更新，先审查并整合；禁止 force-push 或覆盖外部提交。

## Definition of Done

- [x] M1–M4 各自完成并以单个 squash commit 保留在 `main`。
- [x] 当前包只公开 v2 Runtime/Plugin/Snapshot/Application 合同；historical replay 与当前运行物理隔离。
- [x] Snapshot persistence、HTTP API、professional foundations、Reporting/Presentation 和 historical replay 已由 M1–M4 建立。
- [ ] M5 quality/security/package/release gates 全绿。
- [ ] ADR/Migration/README/CHANGELOG/M5 plan 与最终实现一致。
- [ ] 当前 v1.6.0 真实 PDF acceptance 与 v1.5.08–v1.5.12 replay 全部通过。
- [ ] M5 最终仅一个 commit 进入 `main`，且直接父提交为 M4 SHA。
- [ ] 新 `main` HEAD 独立 CI 再次全绿。
- [ ] final delivery source ZIP、binary patch、bundle、SHA256SUMS、BASELINE、VERIFICATION、PUSH-INSTRUCTIONS 生成并自校验。
