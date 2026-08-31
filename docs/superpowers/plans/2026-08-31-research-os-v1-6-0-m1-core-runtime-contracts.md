# Research OS 1.6.0 M1：Core Runtime 与类型化契约实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 Core API 2.0 的类型化运行边界，使 `ResearchEngine` 成为唯一 Module 执行器，并完成 Plugin API 2.0、分领域 Run Command、Result、Completion 与 Readiness 的基础迁移。

**Architecture:** 先冻结 1.5.12 行为测试，再以 `ArtifactKey[T]`、`ArtifactCatalog`、`ArtifactStore`、`ArtifactSnapshot` 改造 Module/State/Engine；采用 Bootstrap + Professional 两阶段计划，但两个阶段都由同一 Engine 执行。插件提供领域服务，不执行嵌套模块。

**Tech Stack:** Python 3.12、Pydantic 2、dataclasses/generics、packaging、importlib.metadata、pytest、Hypothesis、mypy。

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-6-0-architecture-convergence-design.md`

## Global Constraints

- 基线：`72ab06c619678b35c31cf7edef7547849e803d16`。
- 本阶段不修改报告正文语义和数据库 Schema。
- 当前 v1.5.12 语义结果先通过 characterization tests 固定。
- 活跃实现不新增 `*_v2.py` 或 `*_v1_6_0.py`；Core API 版本由合同字段表达。
- Engine 返回后不允许语义后处理。

---

### Task 1：版本身份和 Release Manifest 契约

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `src/research_os/release/manifest.py`
- Modify: `src/research_os/__init__.py`
- Create: `tests/unit/release/test_v1_6_version_contract.py`
- Create: `tests/regression/architecture/test_version_authority_v1_6.py`

**Interfaces:**

```python
RESEARCH_OS_VERSION = "1.6.0"
CORE_API_VERSION = "2.0"
PLUGIN_API_VERSION = "2.0"
SNAPSHOT_SCHEMA_VERSION = "2.0"
HTTP_API_VERSION = "v1"
```

- [ ] 写 RED 测试：五个版本常量准确、`version.py` 无 import、Manifest 与常量一致。
- [ ] 写 RED 测试：调用方提供的 `versions` 不得覆盖 Research OS 自有组件版本。
- [ ] 运行：`python -m pytest -q tests/unit/release/test_v1_6_version_contract.py tests/regression/architecture/test_version_authority_v1_6.py`，确认因 1.5.12/1.0 失败。
- [ ] 扩展 `ReleaseManifest`：增加 `plugin_api_version`、`snapshot_schema_version`、`http_api_version`。
- [ ] 保持 `research_os.version` 为 build-safe import-free leaf。
- [ ] GREEN 后运行现有 release governance tests。

### Task 2：类型化 Artifact 合同

**Files:**
- Create: `src/research_os/contracts/__init__.py`
- Create: `src/research_os/contracts/artifacts.py`
- Create: `src/research_os/contracts/errors.py`
- Create: `src/research_os/runtime/core_artifacts.py`
- Create: `tests/unit/contracts/test_artifacts.py`
- Create: `tests/property/contracts/test_artifact_store_properties.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class ArtifactKey(Generic[T]):
    artifact_id: str
    schema_version: str
    value_type: type[T]

class ArtifactMode(StrEnum):
    EXCLUSIVE = "exclusive"
    COLLECTION = "collection"

@dataclass(frozen=True, slots=True)
class ArtifactWrite(Generic[T]):
    key: ArtifactKey[T]
    value: T
    producer_id: str
    evidence_ids: tuple[str, ...] = ()
```

- [ ] 写 RED 测试：空 ID、空 Schema、错误类型、重复定义均失败关闭。
- [ ] 写 RED 测试：Exclusive Artifact 禁止第二 Provider。
- [ ] 写 RED 测试：Collection Artifact 没有 Reducer 时 Plan 编译失败。
- [ ] 写 RED 测试：Reducer 顺序与输入注册顺序无关，并保留所有 Provider/Evidence IDs。
- [ ] 写 RED 属性测试：Freeze 后修改原对象、返回对象或输入顺序均不能改变 Snapshot。
- [ ] 实现 `ArtifactCatalog`、`ArtifactStore`、`ArtifactEnvelope`、`ArtifactSnapshot`。
- [ ] 在 `core_artifacts.py` 集中登记所有 1.5.12 durable Artifact。
- [ ] 运行：`python -m pytest -q tests/unit/contracts tests/property/contracts`。

### Task 3：Module API 与唯一 ResearchEngine

**Files:**
- Modify: `src/research_os/runtime/modules.py`
- Modify: `src/research_os/runtime/state.py`
- Modify: `src/research_os/runtime/engine.py`
- Create: `src/research_os/runtime/module_plan.py`
- Modify: `tests/unit/runtime/test_engine.py`
- Create: `tests/regression/architecture/test_single_executor_v1_6.py`

**Interfaces:**

```python
class ModuleSpec(BaseModel):
    requires: frozenset[ArtifactKey[Any]]
    provides: frozenset[ArtifactKey[Any]]

class ModuleResult(BaseModel):
    writes: tuple[ArtifactWrite[Any], ...]
```

- [ ] 先为现有 Engine 行为补 characterization tests：排序、循环、缺失依赖、异常归因、未声明输出。
- [ ] 写 RED 测试：输出 Artifact 的类型、Provider ID 和声明必须一致。
- [ ] 写 RED 架构测试：除 `runtime/engine.py` 与明确的 test helper 外，`src/research_os` 不得调用 Module `.run()`。
- [ ] 实现 `ModulePlan` 和 `ModulePlanCompiler`；Plan 编译期校验 Provider/Reducer/Dependency。
- [ ] Engine 通过一个私有 `_invoke_module()` 调用模块，并写入 `ArtifactStore`。
- [ ] `ResearchStateView` 只暴露 `get/require(ArtifactKey)`，不暴露可变字典。
- [ ] 删除 `IndustryKpiModule` 中直接执行插件模块的路径，暂以 RED 测试锁定，Task 5 完成 Provider 替换。
- [ ] 运行 runtime unit 与 architecture tests。

### Task 4：两阶段 Module Plan

**Files:**
- Create: `src/research_os/application/bootstrap.py`
- Create: `src/research_os/application/plan.py`
- Create: `tests/unit/application/test_plan_compilation.py`
- Create: `tests/integration/runtime/test_two_phase_execution.py`

**Interfaces:**

```python
class BootstrapPlanCompiler:
    def compile(self, command: ResearchRunCommand) -> ModulePlan: ...

class ResearchPlanCompiler:
    def compile(
        self,
        command: ResearchRunCommand,
        bootstrap: ArtifactSnapshot,
        strategy: ResolvedPluginSet,
    ) -> ModulePlan: ...
```

- [ ] 写 RED 测试：Phase A 仅含 Preflight、PIT、Financial Snapshot、Business Model。
- [ ] 写 RED 测试：Phase B 从不可变 Bootstrap Snapshot 启动，不重复执行 Phase A。
- [ ] 写 RED 测试：预计算 StrategyResolution 由 `ResolvedStrategyModule` 经 Engine 写入。
- [ ] 实现 Engine 的 `execute(plan, context, initial_snapshot=None)`。
- [ ] 证明两个阶段都只有 Engine 调用 Module。

### Task 5：Plugin API 2.0

**Files:**
- Modify: `src/research_os/plugins/models.py`
- Modify: `src/research_os/plugins/protocols.py`
- Modify: `src/research_os/plugins/registry.py`
- Modify: `src/research_os/plugins/resolver.py`
- Modify: `src/research_os/plugins/builtins.py`
- Create: `src/research_os/plugins/discovery.py`
- Create: `src/research_os/compat/v1/plugins.py`
- Create: `tests/unit/plugins/test_api_v2.py`
- Create: `tests/integration/runtime/test_plugin_services_v2.py`

**Interfaces:**

```python
@runtime_checkable
class IndustryPlugin(Protocol):
    manifest: PluginManifest
    def applicability(self, context, business_model) -> ApplicabilityResult: ...
    def services(self) -> PluginServices: ...

@runtime_checkable
class KpiProvider(Protocol):
    provider_id: str
    def calculate(self, facts: FactView, period: ReportingPeriod) -> MetricSet: ...
```

- [ ] 写 RED 测试：Plugin API 1.0 Manifest 被明确拒绝并包含迁移错误代码。
- [ ] 写 RED 测试：版本范围由 `SpecifierSet` 判断，pre-release 行为明确。
- [ ] 写 RED 测试：内置 Manufacturing/Distributor 不公开 `_pack`，也不返回嵌套 Module。
- [ ] 写 RED 测试：Entry Point 加载按插件 ID 排序并拒绝重复。
- [ ] 迁移 Registry/Resolver；使用 `packaging.version.Version`。
- [ ] 为现有 KPI Pack 建立 Provider Adapter，保持公式与 v1.5.12 结果不变。
- [ ] 旧 Plugin API 1.0 仅保留迁移解析，不进入当前运行路径。

### Task 6：分领域 ResearchRunCommand

**Files:**
- Create: `src/research_os/application/__init__.py`
- Create: `src/research_os/application/command.py`
- Create: `src/research_os/compat/v1/inputs.py`
- Create: `tests/unit/application/test_command.py`
- Create: `tests/unit/compat/test_v1_input_migration.py`

- [ ] 为 1.5.12 `ResearchInputs` 的每个字段建立迁移矩阵测试。
- [ ] 写 RED 测试：领域子输入不可变，未知字段失败，产品版本覆盖被拒绝。
- [ ] 创建 Financial/Thesis/Expectation/Valuation/Monitoring/Forecast/Peer/Readiness 输入类型。
- [ ] 实现 `migrate_research_inputs()`；输出迁移告警但不执行旧 Runtime。
- [ ] 使用现有领域模型，不复制 Sensitivity、Threshold、Reconciliation 类型。

### Task 7：Application Service、Result 与 Finalizer

**Files:**
- Create: `src/research_os/application/result.py`
- Create: `src/research_os/application/finalizer.py`
- Create: `src/research_os/application/service.py`
- Modify: `src/research_os/runtime/__init__.py`
- Modify: `src/research_os/runtime/factory.py`
- Create: `tests/integration/runtime/test_research_application.py`
- Create: `tests/regression/architecture/test_no_post_engine_semantics_v1_6.py`

- [ ] 写 RED 测试：`ResearchApplication.run(command)` 产生不可变 Result。
- [ ] 写 RED 测试：Finalizer 只能组合 Metadata，不可创建语义 Artifact。
- [ ] 写 RED 测试：禁止在 Engine 后调用 ThesisService、Expectation Validator、Valuation Reconciler。
- [ ] 从 `runtime/factory.py` 删除 stale `_version_bundle()` 默认和语义后处理。
- [ ] `RunVersionSet` 由 Manifest、实际 Module/Plugin Fingerprint 和 ExternalVersionInputs 生成。
- [ ] 旧 `ResearchRuntimeFactory` 调用给出 `CORE_API_V1_REMOVED` 迁移错误；历史 replay 不使用当前 Factory。

### Task 8：Execution Completion 与 Research Readiness

**Files:**
- Rename/Refactor: `src/research_os/completion/` 保持执行完成权威
- Create: `src/research_os/readiness/__init__.py`
- Create: `src/research_os/readiness/models.py`
- Create: `src/research_os/readiness/service.py`
- Modify: `src/research_os/runtime/research_completeness.py`
- Create: `tests/unit/readiness/test_readiness.py`
- Create: `tests/integration/runtime/test_completion_readiness_separation.py`

- [ ] 写 RED 测试：Execution COMPLETE 与 Readiness NOT_READY 可以同时存在。
- [ ] 写 RED 测试：Readiness 不改变 Decision 或 Completion。
- [ ] 写 RED 测试：显式 NOT_APPLICABLE 不阻塞，隐式缺失仍阻塞。
- [ ] 将现有 completeness 九维逻辑迁入 `ResearchReadinessEvaluator`，保留同等结果。
- [ ] Result 同时公开两个独立字段。

### Task 9：M1 回归与出口门禁

- [ ] 运行 Core/Runtime/Plugin/Application/Completion/Readiness 全部单元和集成测试。
- [ ] 运行 v1.5.12 Semantic Preservation、Valuation Reconciliation 回归。
- [ ] 运行 mypy 严格检查 Core 边界。
- [ ] 扫描 `src/research_os`，确认只有 Engine 调用 Module。
- [ ] 生成 M1 变更说明，但不创建 release commit。
