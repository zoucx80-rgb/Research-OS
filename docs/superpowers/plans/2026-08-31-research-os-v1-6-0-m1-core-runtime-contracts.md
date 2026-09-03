# Research OS 1.6.0 M1：Core Runtime 与类型化契约实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 建立 Core API 2.0 的类型化运行边界，使 `ResearchEngine` 成为唯一 Module 执行器，并完成 Plugin API 2.0、分领域 Run Command、Result、Completion 与 Readiness 的基础迁移。

**Architecture:** 先将 `behavior_baseline_sha` 冻结为缺陷理解和历史 replay 的参考证据，再以 `ArtifactKey[T]`、`ArtifactCatalog`、`ArtifactStore`、`ArtifactSnapshot` 替换 Module/State/Engine 的现有表面；采用 Bootstrap + Professional 两阶段计划，但两个阶段都由同一 Engine 执行。插件提供领域服务，不执行嵌套模块。

**Tech Stack:** Python 3.12、Pydantic 2、dataclasses/generics、packaging、importlib.metadata、pytest、Hypothesis、mypy。

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-6-0-architecture-convergence-design.md`

## Global Constraints

- 行为基线：`72ab06c619678b35c31cf7edef7547849e803d16`；M1 development milestone 的交付父提交冻结为 `d37e360cea3cd32f18cacc634ab7e5dec967c4db`，两者用途不得混淆（评审时 main 为 `812b6212410723bc80ed6222b5c78bbc74917390`）。
- 本阶段不修改报告正文语义和数据库 Schema。
- `behavior_baseline_sha` 的 characterization 只用于理解缺陷和历史 replay，不是当前 v2 兼容门禁；`delivery_parent_sha` 才是最终交付时重新核验的 main 父提交。
- Phase A 必须创建绑定 `company_id + decision_ts` 的不可变 `EvidenceView` 与 `FactView`；事实引用包含 `EvidenceRef(evidence_id, revision, content_fingerprint)`。移除运行边界内的 ID-only get。
- M1 前置冻结 `ReportingPeriod`、`AccountingScope`、`MetricResult`、`PolicySnapshot` 和只读 `MetricDefinitionRegistry` 最小形状，M3 不得改变这些签名。
- 活跃实现不新增 `*_v2.py` 或 `*_v1_6_0.py`；Core API 版本由合同字段表达。
- Engine 返回后不允许语义后处理。

---

### Task 0：冻结历史参考证据

**Files:**
- Create: `tests/fixtures/historical_replay/v1_5_12/runtime_reference/*.json`
- Create: `tests/fixtures/historical_replay/v1_5_12/report_reference/*.json`
- Create: `tests/regression/runtime/test_v1_5_12_characterization.py`
- Create: `tests/regression/reporting/test_v1_5_12_characterization.py`

- [x] 从 `behavior_baseline_sha` 生成匿名输入、Artifact、Completion、报告字段和语义指纹 characterization；记录生成 SHA，不读取其他项目数据。
- [x] 加入未来 revision 混入历史事实和 ID-only get 的失败复现，确认旧行为测试能暴露问题而不是把错误值固化为预期。
- [x] 记录制造/分销 KPI 数值、missingness、lineage、Sensitivity、Monitoring 和 Valuation Reconciliation，作为缺陷诊断和历史 replay 的参考，不作为 v2 输出等同性断言。
- [x] M1-M4 只复用本任务的 reference evidence，不在 M3/M4 临时重建不同基线。

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


class EvidenceView(Protocol):
    company_id: str
    decision_ts: datetime

    def get(self, ref: EvidenceRef) -> RawEvidence: ...
    def refs(self) -> tuple[EvidenceRef, ...]: ...


class FactView(Protocol):
    company_id: str
    decision_ts: datetime
    reporting_period: ReportingPeriod
    accounting_scope: AccountingScope

    def get(self, fact_id: str, default: object | None = None) -> object | None: ...
    def evidence_refs(self, fact_id: str) -> tuple[EvidenceRef, ...]: ...
```

- [x] 写 RED：revision 1 在 cutoff 前、revision 2 在 cutoff 后时，只能读取 revision 1；lineage 引用相同 revision/fingerprint。
- [x] 写 RED：调换输入 revision 顺序结果不变；跨公司 ref、cutoff 边界错误和 content fingerprint 不匹配失败。
- [x] 写 RED：FactView 构造后 Repository 新增 revision 不改变同一 run。
- [x] 移除 v2 运行边界内 ID-only evidence lookup；Financial Snapshot 和内置模块只通过 `EvidenceRef` 解析证据。

### Task 0B：冻结 Plugin API 最小领域类型

**Files:**
- Create: `src/research_os/contracts/values.py`
- Create: `src/research_os/contracts/metrics.py`
- Create: `src/research_os/contracts/policies.py`
- Create: `tests/contract/plugins/test_kpi_provider_contract.py`

- [x] 冻结最小 `ReportingPeriod`、`AccountingScope`、`MetricResult`、`PolicySnapshot` 和只读 `MetricDefinitionRegistry` Protocol。
- [x] 类型包含期间、范围、单位、missingness 和 EvidenceRef，不在 M3 更名或换返回形状。
- [x] 同一 contract suite 可运行内置与 synthetic external Provider。

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

- [x] 写 RED 测试：五个版本常量准确、`version.py` 无 import、Manifest 与常量一致。
- [x] 写 RED 测试：调用方提供的 `versions` 不得覆盖 Research OS 自有组件版本。
- [x] 运行：`python -m pytest -q tests/unit/release/test_v1_6_version_contract.py tests/regression/architecture/test_version_authority_v1_6.py`，确认因 1.5.12/1.0 失败。
- [x] 扩展 `ReleaseManifest`：增加 `plugin_api_version`、`snapshot_schema_version`、`http_api_version`。
- [x] 修改版本常量时同步 `research_os_version.json` 等生成元数据，使既有 release governance tests 在 M1 内保持一致；M5 只做最终核对。
- [x] 保持 `research_os.version` 为 build-safe import-free leaf。
- [x] GREEN 后运行现有 release governance tests。

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
    evidence_refs: tuple[EvidenceRef, ...] = ()
```

- [x] 写 RED 测试：空 ID、空 Schema、错误类型、重复定义均失败关闭。
- [x] 写 RED 测试：Exclusive Artifact 禁止第二 Provider。
- [x] 写 RED 测试：Collection Artifact 没有 Reducer 时 Plan 编译失败。
- [x] 写 RED 测试：Reducer 顺序与输入注册顺序无关，并保留所有 Provider/EvidenceRef lineage。
- [x] 写 RED 属性测试：Freeze 后修改原对象、返回对象或输入顺序均不能改变 Snapshot。
- [x] 实现 `ArtifactCatalog`、`ArtifactStore`、`ArtifactEnvelope`、`ArtifactSnapshot`。
- [x] 在 `core_artifacts.py` 集中登记纯 v2 durable Artifact；递归类型图不得引用含裸 `evidence_ids`/`assumption_ids` 的旧领域模型。
- [x] 建立绑定 revision/版本与内容指纹的 `EvidenceRef`、`AssumptionRef`，并以递归 contract test 禁止 v2 注册类型使用 ID-only lineage。
- [x] `evidence.pit@2.0` 使用逐元素校验的 `EvidenceSet`，拒绝仅验证外层 `tuple` 或未与 EvidenceRef 的 revision/content fingerprint 绑定的条目。
- [x] 运行：`python -m pytest -q tests/unit/contracts tests/property/contracts`。

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
    module_id: str
    module_version: str
    requires: frozenset[ArtifactKey[Any]]
    provides: frozenset[ArtifactKey[Any]]
    required_for_completion: bool


class ModuleResult(BaseModel):
    module_id: str
    status: ModuleStatus
    diagnostics: tuple[str, ...]
    writes: tuple[ArtifactWrite[Any], ...]
```

- [x] 将既有 `ModuleSpec`、`ModuleResult`、`ResearchStateView` 和 `ResearchEngine` 的字段与方法替换为本任务定义的 typed surfaces；删除旧 `dict` state、字符串 Artifact、旧 result 字段和并行入口，不保留双表面。
- [x] 先为当前 v2 Engine 语义补测试：排序、循环、缺失依赖、异常归因、未声明输出。
- [x] 写 RED 测试：输出 Artifact 的类型、Provider ID 和声明必须一致。
- [x] 写 RED 架构测试：除 `runtime/engine.py` 与明确的 test helper 外，`src/research_os` 不得调用 Module `.run()`。
- [x] 实现 `ModulePlan` 和 `ModulePlanCompiler`；Plan 编译期校验 Provider/Reducer/Dependency。
- [x] Engine 通过一个私有 `_invoke_module()` 调用模块，并写入 `ArtifactStore`。
- [x] `ResearchStateView` 只暴露 `get/require(ArtifactKey)`，不暴露可变字典。
- [x] 删除 `IndustryKpiModule` 中直接执行插件模块的路径，Task 5 以 Provider 服务替换。
- [x] 运行 runtime unit 与 architecture tests。

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

- [x] 写 RED 测试：Phase A 仅含 Preflight、PIT、Financial Snapshot、Business Model。
- [x] 写 RED 测试：Phase B 从不可变 Bootstrap Snapshot 启动，不重复执行 Phase A。
- [x] 写 RED 测试：预计算 StrategyResolution 由 `ResolvedStrategyModule` 经 Engine 写入。
- [x] 实现 Engine 的 `execute(plan, context, initial_snapshot=None)`。
- [x] 证明两个阶段都只有 Engine 调用 Module。

### Task 5：Plugin API 2.0

**Files:**
- Modify: `src/research_os/plugins/models.py`
- Modify: `src/research_os/plugins/protocols.py`
- Modify: `src/research_os/plugins/registry.py`
- Modify: `src/research_os/plugins/resolver.py`
- Modify: `src/research_os/plugins/builtins.py`
- Create: `src/research_os/plugins/discovery.py`
- Create: `tests/unit/plugins/test_api_v2.py`
- Create: `tests/integration/runtime/test_plugin_services_v2.py`

**Interfaces:**

```python
@runtime_checkable
class IndustryPlugin(Protocol):
    manifest: PluginManifest

    def applicability(self, context, business_model) -> ApplicabilityResult: ...
    def services(self) -> PluginServices: ...


class SupportAssessment(BaseModel):
    supported: bool
    rationale: tuple[str, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    limitations: tuple[str, ...] = ()


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

- [x] 写 RED 测试：同一 contract test 同时约束内置和外部 Provider；Registry 只接受 Plugin API 2.0 Manifest，不提供 v1 解析、adapter 或稳定迁移错误代码。
- [x] 写 RED 测试：版本范围由 `SpecifierSet` 判断，pre-release 行为明确。
- [x] 写 RED 测试：内置 Manufacturing/Distributor 不公开 `_pack`，也不返回嵌套 Module。
- [x] 写 RED 测试：Entry Point 加载按插件 ID 排序并拒绝重复。
- [x] 写 RED 测试：行业适用性与方法支持判断的 EvidenceRef 保留在对应 ResolvedPlugin，并汇总到 StrategyResolution Artifact lineage。
- [x] 迁移 Registry/Resolver；使用 `packaging.version.Version`。
- [x] 以正式签名的 Provider 封装当前内部计算引擎并返回类型化结果；该内部委托不是公共 adapter 或兼容表面。M3 可替换公式引擎，但不得改变本任务冻结的 Provider 签名；不得公开临时 `calculate(facts, period)` 或裸 scalar surface。

### Task 6：分领域 ResearchRunCommand

**Files:**
- Create: `src/research_os/application/__init__.py`
- Create: `src/research_os/application/command.py`
- Create: `tests/unit/application/test_command.py`

- [x] 写 RED 测试：领域子输入不可变，未知字段失败，产品版本覆盖被拒绝。
- [x] 创建 Financial/Thesis/Expectation/Valuation/Monitoring/Forecast/Peer/Readiness 输入类型。
- [x] 使用纯 v2 领域值类型；证据与假设 lineage 只接受 `EvidenceRef`/`AssumptionRef`，不复用含裸 lineage ID 的旧领域模型。
- [x] 只公开新的 `ResearchRunCommand`；不实现输入迁移器、v1 parser 或 adapter。

### Task 7：Application Service、Result 与 Finalizer

**Files:**
- Create: `src/research_os/application/result.py`
- Create: `src/research_os/application/finalizer.py`
- Create: `src/research_os/application/service.py`
- Modify: `src/research_os/runtime/__init__.py`
- Modify: `src/research_os/runtime/factory.py`
- Create: `tests/integration/runtime/test_research_application.py`
- Create: `tests/regression/architecture/test_no_post_engine_semantics_v1_6.py`

- [x] 写 RED 测试：`ResearchApplication.run(command)` 产生不可变 Result。
- [x] 写 RED 测试：Finalizer 只能组合 Metadata，不可创建语义 Artifact。
- [x] 写 RED 测试：禁止在 Engine 后调用 ThesisService、Expectation Validator、Valuation Reconciler。
- [x] 从 `runtime/factory.py` 删除 stale `_version_bundle()` 默认和语义后处理。
- [x] `RunVersionSet` 由 Manifest、实际 Module/Plugin Fingerprint 和 ExternalVersionInputs 生成。
- [x] 移除 `ResearchRuntimeFactory` 公共入口及其并行 runtime surface；历史 replay 不使用当前 Factory。

### Task 8：Execution Completion 与 Research Readiness

**Files:**
- Rename/Refactor: `src/research_os/completion/` 保持执行完成权威
- Create: `src/research_os/readiness/__init__.py`
- Create: `src/research_os/readiness/models.py`
- Create: `src/research_os/readiness/service.py`
- Modify: `src/research_os/runtime/research_completeness.py`
- Create: `tests/unit/readiness/test_readiness.py`
- Create: `tests/integration/runtime/test_completion_readiness_separation.py`

- [x] 写 RED 测试：Engine 末端先评估 Completion，再由 Readiness 消费 Completion 和内容 Artifact；Execution COMPLETE 与 Readiness NOT_READY 可以同时存在。
- [x] 写 RED 测试：Readiness 不改变 Decision 或 Completion。
- [x] 写 RED 测试：显式 NOT_APPLICABLE 不阻塞，隐式缺失仍阻塞。
- [x] 写 RED 测试：内容非空但 Envelope 无 `EvidenceRef`、值内无显式 `AssumptionRef` 且无 `NOT_APPLICABLE` 领域状态时不得 READY；仅在值内嵌 EvidenceRef 但未写入 Envelope 同样不得 READY。
- [x] 写 RED 测试：无插件/缺证据返回 `INCOMPLETE + NOT_READY`；未登记 Provider 或依赖循环在编译期失败；异常终止不生成有效 Result。
- [x] 将现有 completeness 维度重新建模到 `ResearchReadinessEvaluator`，以 v2 typed Artifact 和 Policy 评估，不将历史输出等同性作为当前门禁。
- [x] Result 同时公开两个独立字段。

### Task 9：M1 回归与出口门禁

- [x] 运行 Core/Runtime/Plugin/Application/Completion/Readiness 全部单元和集成测试。
- [x] 运行当前 v2 Semantic Preservation、Valuation Reconciliation 和 revision-bound lineage 回归。
- [x] 运行 mypy 严格检查 Core 边界。
- [x] 扫描 `src/research_os`，确认只有 Engine 调用 Module。
- [x] 验证未来 revision 不影响历史结果、revision 顺序不改变结果、跨公司 Evidence 被拒绝、同一 run 数据变化被冻结。
- [x] M2 的 Snapshot codec/schema 只能消费本阶段已冻结的公共形状。
- [x] 生成 M1 变更说明，但不创建 stable release commit；M1 可以按用户交付要求创建 development milestone commit。
