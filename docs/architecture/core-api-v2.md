# Research OS Core API 2.0 公共契约

## 1. 定位

Core API 2.0 是 Research OS 1.6.0 的 Python 应用调用合同。它定义一次研究运行的输入、执行结果、Artifact 读取、错误和版本边界，不定义数据库、HTTP、报告版式或插件内部实现。

## 2. 版本

```text
Research OS Product: 1.6.0
Core API:            2.0
```

Core API 与产品版本独立。调用方必须使用 `CORE_API_VERSION` 判断兼容性，不得仅根据产品 MINOR 猜测接口兼容。

## 3. 唯一入口

```python
from research_os.application import ResearchApplication, ResearchRunCommand

application = ResearchApplication.build(
    plugin_providers=(...),
)
result = application.run(command)
```

正式调用方不得直接构造 `ResearchEngine`、`ArtifactStore` 或内部 Module Plan。

## 4. ResearchRunCommand

Command 是冻结的、run-scoped 输入：

```python
class ResearchRunCommand(BaseModel):
    context: ResearchContext
    financial: FinancialResearchInput
    thesis: ThesisResearchInput
    expectations: ExpectationResearchInput
    valuation: ValuationResearchInput
    monitoring: MonitoringResearchInput
    forecasting: ForecastResearchInput
    peers: PeerResearchInput
    readiness: ResearchReadinessInput
    options: ResearchRunOptions
```

### 4.1 Context

`ResearchContext` 只保存：

- run/company identity；
- decision timestamp；
- repository baseline；
- Phase A 已冻结的 PIT Evidence/Fact View 与 Knowledge Port。

插件选择、持久化和外部版本等运行选项只存在于
`ResearchRunCommand.options`，不得在 Context 维护第二份可冲突配置。

`ResearchContext` 必须在进入任何业务模块前持有 Phase A 已构造的、不可变且公司绑定的 `EvidenceView` 与 `FactView`：

Repository Preflight 不能只检查调用方提供字段的格式；它必须将仓库全名、ID、分支、实际 checkout HEAD、产品版本和 Core API 版本与冻结 baseline 逐项核对，任一不符即在业务模块执行前失败关闭。

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

`EvidenceView` 只包含 `publish_ts <= decision_ts` 的具体 revision；`FactView` 冻结事实值、期间、范围和具体 `EvidenceRef` lineage。`ResearchContext` 校验两个视图的公司/cutoff 一致、引用可解析且原始事实值受引用证据支持。v2 模块和插件不得接收裸 evidence ID 或调用无 cutoff 的 `get(evidence_id)`；未来 revision、跨公司引用、cutoff 边界和同一 run 内数据变化必须拒绝或不改变结果。

`evidence.pit@2.0` 的值类型是 `EvidenceSet`，不是运行时只能检查外层的裸 `tuple`。`EvidenceSet` 逐条校验 Evidence ID、revision 与内容指纹均和对应 `EvidenceRef` 完全一致；Artifact Envelope 同时保留同一组引用。

Command 的全部领域子输入及注册到 Artifact Catalog 的全部值类型同样只允许显式 lineage 引用：证据使用绑定 revision 与内容指纹的 `EvidenceRef`；研究假设使用绑定假设 key、版本与内容指纹的 `AssumptionRef`。v2 类型图中不得出现 `evidence_ids`、`assumption_ids` 或其他仅凭字符串 ID 表示 lineage 的字段，也不得引用旧领域包中保留这类字段的模型。

### 4.2 版本输入

调用方只可提供外部数据集、解析器、外部模型和数据供应商版本。Research OS 自有组件版本由 Release Manifest 和实际选中组件决定。

## 5. ResearchRunResult

```python
class ResearchRunResult(BaseModel):
    run_id: str
    company: CompanyRef
    decision_ts: datetime
    baseline: BaselineFingerprint
    strategy_resolution: StrategyResolution
    artifacts: ArtifactSnapshot
    module_results: tuple[ModuleResult, ...]
    execution_completion: ExecutionCompletionResult
    research_readiness: ResearchReadinessAssessment
    component_fingerprints: tuple[ComponentFingerprint, ...]
    snapshot: ResearchSnapshotDescriptor | None
```

Result 和内部值均不可变。调用方不能通过修改 Result 改变已持久化 Snapshot。

## 6. Artifact 读取

```python
from research_os.runtime.core_artifacts import KPI_METRICS

metrics = result.artifacts.require(KPI_METRICS)
optional = result.artifacts.get(VALUATION_RECONCILIATION)
metadata = result.artifacts.envelope(KPI_METRICS)
```

字符串索引不是 Core API 2.0 合同。Envelope 至少保留：

```text
artifact_id
schema_version
producer_ids
evidence_refs
value_fingerprint
```

## 7. Completion 与 Readiness

`execution_completion` 回答“运行是否完成”；`research_readiness` 回答“专业研究是否达到发布准备度”。

合法组合示例：

```text
COMPLETE + READY
COMPLETE + NOT_READY
INCOMPLETE + NOT_READY
```

`INCOMPLETE + READY` 被合同拒绝。

执行顺序固定为 `Module execution -> ExecutionCompletionEvaluator -> ResearchReadinessEvaluator -> Finalizer`。Completion 不依赖 Readiness，也不把 Readiness 计入自身完成集合；已登记能力的缺证据、无覆盖和 `NOT_APPLICABLE` 通过类型化状态返回，未登记 Provider/依赖循环才是编译错误。异常终止不产生可发布 Result，Finalizer 只投影既有语义。

Readiness 不得仅凭 Artifact 内容非空判定维度通过。每个参与 Readiness 的 Artifact 还必须满足以下之一：Envelope 含具体 `EvidenceRef`；类型化值含显式 `AssumptionRef`；类型化值将该领域明确标记为 `NOT_APPLICABLE`。内容中出现但未写入 Envelope 的 EvidenceRef 不构成 Artifact lineage；没有上述 lineage 或领域状态的 Artifact 必须产生 `NOT_READY`。

## 8. 异常

公共错误必须继承：

```python
class ResearchOSError(Exception):
    code: str
    context: Mapping[str, str]
```

主要错误：

```text
CORE_API_VERSION_MISMATCH
ARTIFACT_TYPE_MISMATCH
ARTIFACT_PROVIDER_CONFLICT
PLAN_DEPENDENCY_MISSING
PLAN_DEPENDENCY_CYCLE
MODULE_EXECUTION_FAILED
PLUGIN_VERSION_UNSUPPORTED
SNAPSHOT_SCHEMA_ERROR
PERSISTENCE_ERROR
```

错误不得吞掉原始 cause；用户报告和 HTTP Problem Details 不暴露堆栈。

## 9. 线程与生命周期

- `ResearchApplication` 可以持有不可变配置和 Provider Factory；
- `ArtifactStore`、Plugin Registry、Module 实例和 UnitOfWork 必须 run-scoped；
- Snapshot Repository 的并发语义由适配器明确；
- 禁止 import-time 全局可变 Registry。

## 10. 确定性

相同输入、相同基线、相同组件/Policy/数据版本必须产生相同：

- Module Plan；
- Artifact payload fingerprint；
- Completion/Readiness；
- Snapshot canonical payload hash。

`run_id`、`snapshot_id` 和 `created_at` 可不同，但不能进入研究语义指纹。

研究语义指纹覆盖公司、decision_ts、该次运行实际采用的方法论与代码基线、实际组件/Policy/Metric/外部数据版本、EvidenceRef（含 revision/fingerprint）、输入假设、类型化 Artifact、Completion 和 Readiness；完整性指纹覆盖完整持久化 envelope。历史 `behavior_baseline_sha` 仅是评审参考，不进入 v2 运行指纹。`SnapshotDescriptor` 不进入自身哈希输入。Artifact codec 由 `(artifact_id, schema_version)` 受控查表，未知 Schema/类型拒绝解码，不动态 import Python 路径；Decimal、UTC 时间、枚举、有序序列、无序集合和 missingness 的编码规则固定。

运行元数据中的 `ComponentFingerprint` 同时覆盖实际加载实现内容及 ID/version/API；仅对组件身份字符串做摘要不视为实现指纹。

## 11. Clean-break upgrade

Core API 2.0 是唯一当前 Python 合同。调用方必须重建为
`ResearchApplication.run(ResearchRunCommand(...))`，并重新生成类型化输入；
包内不提供 v1 输入转换器、v1 Runtime、旧 Snapshot Reader 或稳定的迁移错误代码。
历史运行只能由 HistoricalReplayExecutor 在对应不可变历史提交中执行，不能由当前
Core API 读取或执行旧合同。
