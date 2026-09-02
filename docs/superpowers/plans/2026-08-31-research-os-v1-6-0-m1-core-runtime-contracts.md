# Research OS 1.6.0 M1：Core Runtime 与类型化契约实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 Core API 2.0 的类型化运行边界，使 `ResearchEngine` 成为唯一 Module 执行器，并完成 Plugin API 2.0、分领域 Run Command、Result、Completion 与 Readiness 的基础迁移。

**Architecture:** 先冻结 1.5.12 行为测试，再以 `ArtifactKey[T]`、`ArtifactCatalog`、`ArtifactStore`、`ArtifactSnapshot` 改造 Module/State/Engine；采用 Bootstrap + Professional 两阶段计划，但两个阶段都由同一 Engine 执行。插件提供领域服务，不执行嵌套模块。

**Tech Stack:** Python 3.12、Pydantic 2、dataclasses/generics、packaging、importlib.metadata、pytest、Hypothesis、mypy。

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-6-0-architecture-convergence-design.md`

## Global Constraints

- 行为基线：`72ab06c619678b35c31cf7edef7547849e803d16`；交付父提交在 M1 启动时冻结为包含本次设计修订的最新 `main` HEAD，两者用途不得混淆（评审时 main 为 `812b6212410723bc80ed6222b5c78bbc74917390`）。
- 本阶段不修改报告正文语义和数据库 Schema。
- 当前 v1.5.12 输入、语义和报告 characterization 必须在任何公共契约改造前完成并冻结，M4 复用其结果。
- Phase A 必须创建绑定 `company_id + decision_ts` 的不可变 `FactView`；事实引用包含 `EvidenceRef(evidence_id, revision, content_fingerprint)`。移除运行边界内的 ID-only legacy get。
- M1 前置冻结 `ReportingPeriod`、`AccountingScope`、`MetricResult`、`PolicySnapshot` 和只读 `MetricDefinitionRegistry` 最小形状，M3 不得改变这些签名。
- 活跃实现不新增 `*_v2.py` 或 `*_v1_6_0.py`；Core API 版本由合同字段表达。
- Engine 返回后不允许语义后处理。

---

### Task 0：冻结 1.5.12 输入、语义与报告行为

**Files:**
- Create: `tests/fixtures/compat/v1_5_12/runtime_contract/*.json`
- Create: `tests/fixtures/compat/v1_5_12/report_contract/*.json`
- Create: `tests/regression/runtime/test_v1_5_12_characterization.py`
- Create: `tests/regression/reporting/test_v1_5_12_characterization.py`

- [ ] 从 `behavior_baseline_sha` 生成匿名输入、Artifact、Completion、报告字段和语义指纹 characterization；记录生成 SHA，不读取其他项目数据。
- [ ] 加入未来 revision 混入历史事实和 ID-only get 的失败复现，确认旧行为测试能暴露问题而不是把错误值固化为预期。
- [ ] 固定现有制造/分销 KPI 数值、missingness、lineage、Sensitivity、Monitoring 和 Valuation Reconciliation。
- [ ] M1-M4 只复用本任务的 characterization，不在 M3/M4 临时重建不同基线。

### Task 0A：Revision-bound PIT FactView

**Files:**
- Create: `src/research_os/contracts/evidence.py`
- Modify: `src/research_os/runtime/context.py`
- Modify: `src/research_os/runtime/financial_snapshot.py`
- Modify: `src/research_os/runtime/builtin_modules.py`
- Create: `tests/unit/contracts/test_evidence_ref.py`
- Create: `tests/integration/runtime/test_revision_bound_fact_view.py`

**Interfaces:**

```python
class EvidenceRef(BaseModel):
    evidence_id: str
    revision: int
    content_fingerprint: str

class FactView(Protocol):
    company_id: str
    decision_ts: datetime
    def get(self, ref: EvidenceRef) -> RawEvidence: ...
    def refs(self) -> tuple[EvidenceRef, ...]: ...
```

- [ ] 写 RED：revision 1 在 cutoff 前、revision 2 在 cutoff 后时，只能读取 revision 1；lineage 引用相同 revision/fingerprint。
- [ ] 写 RED：调换输入 revision 顺序结果不变；跨公司 ref、cutoff 边界错误和 content fingerprint 不匹配失败。
- [ ] 写 RED：FactView 构造后 Repository 新增 revision 不改变同一 run；旧输入迁移也必须经 FactView 验证。
- [ ] 移除 v2 运行边界内 `LegacyEvidenceView.get(evidence_id)` 的使用，Financial Snapshot 和内置模块只接收 `EvidenceRef`。

### Task 0B：冻结 Plugin API 最小领域类型

**Files:**
- Create: `src/research_os/contracts/values.py`
- Create: `src/research_os/contracts/metrics.py`
- Create: `src/research_os/contracts/policies.py`
- Create: `tests/contract/plugins/test_kpi_provider_contract.py`

- [ ] 冻结最小 `ReportingPeriod`、`AccountingScope`、`MetricResult`、`PolicySnapshot` 和只读 `MetricDefinitionRegistry` Protocol。
- [ ] 类型包含期间、范围、单位、missingness 和 EvidenceRef，不在 M3 更名或换返回形状。
- [ ] 同一 contract suite 可运行内置与 synthetic external Provider。

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
- [ ] 修改版本常量时同步 `research_os_version.json` 等生成元数据，使既有 release governance tests 在 M1 内保持一致；M5 只做最终核对。
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
    provider_version: str
    def metric_ids(self) -> frozenset[str]: ...
    def calculate(
        self,
        facts: FactView,
        definitions: MetricDefinitionRegistry,
        policy: PolicySnapshot,
    ) -> tuple[MetricResult, ...]: ...
```

- [ ] 写 RED 测试：同一 contract test 同时约束内置和外部 Provider；Plugin API 1.0 Manifest 被明确拒绝并返回稳定 `PLUGIN_API_V1_REMOVED` 迁移错误代码。
- [ ] 写 RED 测试：版本范围由 `SpecifierSet` 判断，pre-release 行为明确。
- [ ] 写 RED 测试：内置 Manufacturing/Distributor 不公开 `_pack`，也不返回嵌套 Module。
- [ ] 写 RED 测试：Entry Point 加载按插件 ID 排序并拒绝重复。
- [ ] 迁移 Registry/Resolver；使用 `packaging.version.Version`。
- [ ] 为现有 KPI Pack 建立正式签名的 Provider Adapter，委托现有计算实现并保持公式与 v1.5.12 结果不变；不得公开临时 `calculate(facts, period)`。
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

- [ ] 写 RED 测试：Engine 末端先评估 Completion，再由 Readiness 消费 Completion 和内容 Artifact；Execution COMPLETE 与 Readiness NOT_READY 可以同时存在。
- [ ] 写 RED 测试：Readiness 不改变 Decision 或 Completion。
- [ ] 写 RED 测试：显式 NOT_APPLICABLE 不阻塞，隐式缺失仍阻塞。
- [ ] 写 RED 测试：无插件/缺证据返回 `INCOMPLETE + NOT_READY`；未登记 Provider 或依赖循环在编译期失败；异常终止不生成有效 Result。
- [ ] 将现有 completeness 九维逻辑迁入 `ResearchReadinessEvaluator`，保留同等结果。
- [ ] Result 同时公开两个独立字段。

### Task 9：M1 回归与出口门禁

- [ ] 运行 Core/Runtime/Plugin/Application/Completion/Readiness 全部单元和集成测试。
- [ ] 运行 v1.5.12 Semantic Preservation、Valuation Reconciliation 回归。
- [ ] 运行 mypy 严格检查 Core 边界。
- [ ] 扫描 `src/research_os`，确认只有 Engine 调用 Module。
- [ ] 验证未来 revision 不影响历史结果、revision 顺序不改变结果、跨公司 Evidence 被拒绝、同一 run 数据变化被冻结。
- [ ] M2 的 Snapshot codec/schema 只能消费本阶段已冻结的公共形状。
- [ ] 生成 M1 变更说明，但不创建 release commit。
