# Research OS 1.6.0 架构收敛与专业研究基础强化设计

## 1. 文档属性

| 属性 | 内容 |
|---|---|
| 仓库 | `zoucx80-rgb/Research-OS` |
| 冻结基线 | `72ab06c619678b35c31cf7edef7547849e803d16` |
| 基线版本 | Research OS `1.5.12` / Core API `1.0` |
| 目标版本 | Research OS `1.6.0` |
| 目标契约 | Core API `2.0` / Plugin API `2.0` / Snapshot Schema `2.0` / HTTP API `v1` |
| 发布性质 | 受控破坏性 MINOR，所有当前调用方整体迁移 |
| 架构风格 | 模块化单体、DDD 边界、Clean Architecture、Ports & Adapters |
| 交付要求 | 基于基线仅形成一个 `main` release commit |

## 2. 目标

Research OS 1.6.0 将现有专业研究语义内核收敛为一个不可绕过、可持久化、可扩展、可审计的系统边界：

```text
单一研究执行权威
+ 类型化 Artifact/Capability
+ Plugin API 2.0
+ 持久化 Snapshot 2.0
+ 正式 HTTP API v1
+ 专业财务/指标/策略/方法合同
+ 历史提交级重放
+ 工业级质量门禁
```

本版本不是推倒重写。1.5.12 已有的 PIT、Evidence Lineage、Missingness、Comparison Basis、Semantic Preservation、Claim Strength、Valuation Reconciliation 和单向展示链全部保留并迁入新契约。

## 3. v1.5.12 基线复核

### 3.1 已完成且必须保留

- `semantic.preservation` 与跨 Result/View/Document 的语义指纹；
- Claim Strength、Recovery/Trough 与 Moat Realization 类型；
- 敏感性假设、模型边界、适用范围和 Caveat 不可分离；
- 监控阈值来源、类型、比较口径和适用范围；
- Typed Valuation Reconciliation：`INTERSECTION`、`CROSS_CHECK_BAND`、`MODEL_DISAGREEMENT`、`NOT_COMPARABLE`；
- 1.5.08–1.5.12 Field Replay；
- Manifest 驱动的 Verification Pack 和稳定 CI 入口。

### 3.2 仍需解决的结构性缺陷

1. `runtime/factory.py` 仍在 Engine 之后重算 Thesis/Expectation 并写入 Artifact；
2. `_version_bundle()` 仍含过期组件默认版本；
3. `IndustryKpiModule` 仍可能形成嵌套模块执行和私有 `_pack` 依赖；
4. `ModuleResult.artifacts` 与 `ResearchRunResult.artifacts` 仍是 `dict[str, Any]`；
5. `ResearchRuntime` 同时承担注册、编排、完成度、报告贡献、版本和快照；
6. Snapshot 仍以进程内存为主要实现；
7. API 仍是动态路由加内存 ReadStore 的原型；
8. Decision 仍以 `theses[0]` 代表整个 Thesis 集合；
9. 活跃 Reporting/Replay 仍存在补丁版本继承和源码指纹对当前源码漂移的耦合。

## 4. 非目标

本版本不做以下事情：

- 不拆分微服务；
- 不引入 Kafka、Celery、BPMN 或内部 Event Bus；
- 不建设数据采集连接器或商业数据源；
- 不实现自动交易、下单或组合执行；
- 不一次性覆盖所有行业和全部估值方法；
- 不把报告层变成第二研究引擎；
- 不修改或重写历史提交、历史快照和历史验收事实。

## 5. 目标逻辑架构

```text
┌─────────────────────────────────────────────────────────────────┐
│                         Interface Layer                         │
│ Python Core API 2.0              HTTP API v1                   │
└───────────────────────┬───────────────────────┬─────────────────┘
                        │                       │
                        ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Application Layer                        │
│ ResearchApplication                                             │
│  ├─ BootstrapPlanCompiler                                       │
│  ├─ PluginResolver                                              │
│  ├─ ResearchPlanCompiler                                        │
│  ├─ ResearchEngine (唯一 Module.run 调用者)                      │
│  ├─ CompletionEvaluator                                         │
│  ├─ ReadinessEvaluator                                          │
│  ├─ RunFinalizer                                                │
│  └─ SnapshotWriter                                              │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Domain Layer                           │
│ Evidence / Period / Metrics / Policies / Router / Capital       │
│ Thesis Portfolio / Expectations / Valuation / Decision          │
│ Forecast Evaluation / Peer Normalization / Postmortem           │
│ Semantic Preservation / Claim Strength / Reconciliation         │
└───────────────────────────────┬─────────────────────────────────┘
                                │ ports
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Adapter Layer                           │
│ SQLAlchemy Repositories / UnitOfWork / HTTP / Entry Points       │
│ Markdown / HTML / Playwright PDF / Git Historical Replay         │
└─────────────────────────────────────────────────────────────────┘
```

依赖只允许向内。Domain 不导入 FastAPI、SQLAlchemy、Playwright、Release 或 Reporting。

## 6. Core API 2.0

### 6.1 运行入口

```python
class ResearchApplication:
    def run(self, command: ResearchRunCommand) -> ResearchRunResult:
        ...
```

`ResearchRuntimeFactory` 不再是正式公共入口。迁移期可在 `research_os.compat.v1` 提供明确转换函数，但不得再创建另一套 Runtime。

### 6.2 ResearchRunCommand

```python
class ResearchRunCommand(BaseModel):
    model_config = ConfigDict(frozen=True)

    context: ResearchContext
    financial: FinancialResearchInput = FinancialResearchInput()
    thesis: ThesisResearchInput = ThesisResearchInput()
    expectations: ExpectationResearchInput = ExpectationResearchInput()
    valuation: ValuationResearchInput = ValuationResearchInput()
    monitoring: MonitoringResearchInput = MonitoringResearchInput()
    forecasting: ForecastResearchInput = ForecastResearchInput()
    peers: PeerResearchInput = PeerResearchInput()
    readiness: ResearchReadinessInput = ResearchReadinessInput()
    options: ResearchRunOptions = ResearchRunOptions()
```

每个子输入只被对应领域模块依赖。不得再让所有模块共同依赖一个无限膨胀的 DTO。

### 6.3 ResearchRunResult

```python
class ResearchRunResult(BaseModel):
    model_config = ConfigDict(frozen=True)

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
    snapshot: ResearchSnapshotDescriptor
```

不再公开可任意写入的 `dict[str, Any]`。

## 7. 类型化 Artifact 与 Capability

### 7.1 基础类型

```python
T = TypeVar("T")

@dataclass(frozen=True, slots=True)
class ArtifactKey(Generic[T]):
    artifact_id: str
    schema_version: str
    value_type: type[T]

class ArtifactMode(StrEnum):
    EXCLUSIVE = "exclusive"
    COLLECTION = "collection"

@dataclass(frozen=True, slots=True)
class ArtifactDefinition(Generic[T]):
    key: ArtifactKey[T]
    mode: ArtifactMode
    reducer_id: str | None = None
```

### 7.2 写入与快照

```python
class ArtifactWrite(BaseModel, Generic[T]):
    key: ArtifactKey[T]
    value: T
    producer_id: str
    evidence_ids: tuple[str, ...] = ()

class ArtifactSnapshot:
    def require(self, key: ArtifactKey[T]) -> T: ...
    def get(self, key: ArtifactKey[T]) -> T | None: ...
    def envelope(self, key: ArtifactKey[T]) -> ArtifactEnvelope[T] | None: ...
```

`ArtifactSnapshot` 是不可变结果；只有 Engine 内部的 `ArtifactStore` 可写。

### 7.3 Provider 与 Reducer 规则

- Exclusive Artifact 只有一个 Provider；
- Collection Artifact 可以有多个 Contributor；
- Collection Artifact 必须在 `ArtifactRegistry` 登记唯一 Reducer；
- Reducer 必须确定性排序、去重并保留 Producer/Evidence lineage；
- 未声明 Artifact、错误类型、重复 Exclusive Provider、缺失 Reducer 均在 Plan 编译期失败。

### 7.4 标准 Artifact Key

至少建立以下注册项：

```text
evidence.pit
validation.lineage
financial.fact_snapshot
business_model.profile
strategy.resolution
kpi.metrics
capital.efficiency
capital.funding_loop
drivers.graph
thesis.portfolio
thesis.semantic_signal_assessment
semantic.claims
expectation.snapshot
expectation.quality
expectation.gap
forecast.evaluation
peers.normalized
valuation.routing
valuation.execution
valuation.result
valuation.reconciliation
decision.record
decision.state_provenance
monitoring.plan
research.readiness
```

## 8. 唯一执行路径与两阶段计划编译

插件选择依赖业务模型结果，因此运行分成两段，但都由同一个 `ResearchEngine` 执行模块：

```text
Phase A：Bootstrap
Repository Preflight -> PIT/Lineage -> Financial Snapshot -> Business Model

Phase B：Professional Plan
ResolvedStrategyModule -> KPI -> Capital -> Drivers -> Thesis ->
Expectation -> Forecast -> Valuation -> Decision -> Monitoring -> Readiness
```

流程：

1. `BootstrapPlanCompiler` 构造基础计划；
2. Engine 产生不可变 Bootstrap ArtifactSnapshot；
3. `PluginResolver` 根据业务模型选择 Plugin API 2.0 服务；
4. `ResearchPlanCompiler` 注入解析后的服务，生成 Phase B Plan；
5. Engine 以 Bootstrap Snapshot 为只读初始状态执行 Phase B；
6. `RunFinalizer` 只组合模块结果、版本和指纹，不产生研究语义；
7. `SnapshotWriter` 持久化最终结果。

`ResolvedStrategyModule` 将预计算的 StrategyResolution 作为 Engine 产物写入，因此最终语义 Artifact 仍全部由 Engine 产生。

## 9. Plugin API 2.0

### 9.1 Manifest

```python
class PluginManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    plugin_id: str
    plugin_type: Literal["industry", "methodology"]
    plugin_version: str
    plugin_api_version: Literal["2.0"]
    core_api_specifier: str
    research_os_specifier: str
    supported_business_models: frozenset[str] = frozenset()
    service_capabilities: frozenset[str]
    priority: int = 100
    maturity: Literal["experimental", "candidate", "stable", "deprecated"]
```

### 9.2 Plugin Services

```python
class PluginServices(BaseModel):
    kpi_provider: KpiProvider | None = None
    valuation_methods: tuple[ValuationMethod, ...] = ()
    policy_contributions: tuple[PolicyDefinition, ...] = ()
    report_contributions: tuple[ReportContribution, ...] = ()
```

插件不得返回要自行执行的嵌套 `ResearchModule`；确需模块扩展时，由受控 `ModuleContribution` 交给 `ResearchPlanCompiler` 编译，仍由 Engine 唯一执行。

### 9.3 标准能力复用

- SemVer：`packaging.version.Version`；
- 版本范围：`packaging.specifiers.SpecifierSet`；
- 外部发现：`importlib.metadata.entry_points(group="research_os.plugins")`；
- 内置插件：显式 `BuiltinPluginProvider`；
- 不引入自研插件扫描器或 DI 容器。

## 10. 版本单一权威

`research_os.version` 仍是无依赖叶子，仅包含常量：

```python
RESEARCH_OS_VERSION = "1.6.0"
CORE_API_VERSION = "2.0"
PLUGIN_API_VERSION = "2.0"
SNAPSHOT_SCHEMA_VERSION = "2.0"
HTTP_API_VERSION = "v1"
```

`ReleaseManifest` 消费这些常量并增加对应字段。规则：

- Research OS 自有组件版本只来自 Manifest 或实际选中组件；
- 调用方不能用 `versions` 字典覆盖内置组件；
- 外部 dataset/parser/model 版本通过 `ExternalVersionInputs` 提供；
- Snapshot、Audit Appendix 和 API 元数据由同一 `RunVersionSet` 生成；
- 任何不一致都使发布门禁失败。

## 11. Completion 与 Research Readiness

### 11.1 Execution Completion

只判断运行所需模块是否满足完成规则：

```python
class ExecutionCompletionResult(BaseModel):
    final_status: Literal["COMPLETE", "INCOMPLETE"]
    blocking_capabilities: tuple[str, ...]
    module_statuses: Mapping[str, ModuleStatus]
```

### 11.2 Research Readiness

评估专业输出是否达到发布准备度：

```python
class ResearchReadinessAssessment(BaseModel):
    final_status: Literal["READY", "NOT_READY"]
    dimensions: tuple[ReadinessDimension, ...]
    blocking_dimensions: tuple[str, ...]
```

标准维度继续覆盖时间序列、经营证据、现金流、一致预期、同行、敏感性、监控事件、上期验证和方法披露。Readiness 不改变 Decision State。

## 12. Snapshot Schema 2.0

### 12.1 模型

```python
class ResearchSnapshotV2(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_id: str
    schema_version: Literal["2.0"]
    codec_version: str
    hash_algorithm: Literal["sha256"]
    run_id: str
    company_id: str
    decision_ts: datetime
    created_at: datetime
    baseline: BaselineFingerprint
    versions: RunVersionSet
    component_fingerprints: tuple[ComponentFingerprint, ...]
    artifact_fingerprints: tuple[ArtifactFingerprint, ...]
    payload: ResearchSnapshotPayloadV2
    payload_hash: str
```

### 12.2 编码与哈希

- 使用 RFC 8785/JCS 兼容的规范 JSON 实现；
- `payload_hash = sha256(canonical_bytes)`；
- 禁止 `json.dumps(..., default=str)`；
- Datetime 固定为 UTC RFC 3339；
- NaN/Infinity 被拒绝；
- 编码器、Schema 和 Hash Algorithm 独立版本化。

### 12.3 Repository 与事务

```python
class SnapshotRepository(Protocol):
    def append(self, snapshot: ResearchSnapshotV2) -> None: ...
    def get(self, snapshot_id: str) -> ResearchSnapshotV2: ...
    def list_for_company(self, query: SnapshotQuery) -> SnapshotPage: ...

class UnitOfWork(Protocol):
    evidence: EvidenceRepository
    runs: ResearchRunRepository
    snapshots: SnapshotRepository
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
```

提供 `InMemorySnapshotRepository` 用于单元测试，`SqlSnapshotRepository` 用于正式运行。

### 12.4 1.x 兼容

`research_os.compat.v1.snapshot_reader` 只读取旧 Snapshot 并投影为 `LegacySnapshotView`。不得把旧快照原地升级或重新计算历史结论。

## 13. Persistence 与 Evidence

适配器目录：

```text
src/research_os/adapters/persistence/
    db.py
    schema.py
    evidence_mapper.py
    evidence_repository.py
    run_repository.py
    snapshot_repository.py
    unit_of_work.py
```

数据库查询负责在 PIT 条件下选择最新 revision；不再把全部 revision 读入 Python 后归并。最低组合索引：

```text
(company_id, publish_ts)
(evidence_id, revision_no)
(company_id, evidence_id, publish_ts, revision_no)
(company_id, decision_ts)
```

Snapshot 和 Run 元数据在同一 UnitOfWork 中原子提交。

## 14. HTTP API v1

### 14.1 边界

HTTP API v1 首期为只读查询面，不通过 HTTP 发起自动交易或修改研究结论。

### 14.2 Endpoint

```text
GET /api/v1/research-runs/{run_id}
GET /api/v1/research-runs/{run_id}/artifacts/{artifact_id}
GET /api/v1/companies/{company_id}/snapshots
GET /api/v1/snapshots/{snapshot_id}
GET /api/v1/snapshots/{snapshot_id}/research-view
GET /api/v1/health
```

Snapshot 列表支持 `decision_ts_lte`、`limit` 和 opaque cursor。

### 14.3 错误合同

采用 `application/problem+json`：

```json
{
  "type": "urn:research-os:error:snapshot-not-found",
  "title": "Snapshot not found",
  "status": 404,
  "detail": "No snapshot exists for the supplied identifier.",
  "instance": "/api/v1/snapshots/...",
  "request_id": "..."
}
```

API 层依赖 Query Service，不直接依赖 SQLAlchemy Session。OpenAPI Schema 进入契约测试。

## 15. 专业财务与指标基础模型

### 15.1 值对象

```text
Money(amount, currency, scale)
Ratio(value, representation)
Quantity(value, unit)
AccountingScope(standard, consolidation, segment, geography)
ReportingPeriod(period_type, start, end, days, cumulative, fiscal_year)
MetricKind(balance, flow, ratio, delta, growth, statistical)
ComparisonBasis(YOY_PERIOD, QOQ_PERIOD, END_VS_BEGIN, POINT_IN_TIME, ...)
SourceLocator(document_id, page, table, url)
```

必须区分：

```text
RawEvidence
NormalizedFact
CalculatedMetric
StatisticalEvidence
AnalystAssumption
Inference
ResearchConclusion
```

### 15.2 MetricDefinitionRegistry

```python
class MetricDefinition(BaseModel):
    metric_id: str
    definition_version: str
    economic_meaning: str
    formula_id: str
    output_kind: MetricKind
    output_unit: Unit
    required_inputs: tuple[MetricInputDefinition, ...]
    valid_comparison_bases: frozenset[ComparisonBasis]
    annualization_policy: str | None
    accounting_scope_policy: str
```

KPI Pack 只选择业务适用指标，公式和基础语义由 Metric Registry 统一拥有。相同财务公式不得在多个行业包复制。

## 16. Policy Registry

所有影响结论的阈值必须类型化：

```python
class PolicyDefinition(BaseModel):
    policy_id: str
    policy_version: str
    policy_type: str
    applicability: PolicyApplicability
    parameters: Mapping[str, PolicyParameter]
    rationale: str
    source: PolicySource
```

首批 Policy：

```text
BusinessModelRoutingPolicy
ExpectationQualityPolicy
FundingLoopPolicy
ThesisFormationPolicy
ValuationFitnessPolicy
DecisionAggregationPolicy
ForecastPromotionPolicy
```

研究快照记录实际使用的 Policy ID、版本和参数指纹。不得把所有阈值简单搬到无类型 YAML。

## 17. Business Model Routing 2.0

输出区分：

```text
rule_match_score
usable_evidence_coverage
classification_status
confidence_band
ambiguity
positive_evidence
counter_evidence
segment_profiles
```

没有统计校准时不得输出概率。第一和第二候选差距低于策略阈值时输出 `UNRESOLVED`。集团型企业可以形成 Segment Profile，但主研究链仍由明确聚合策略决定，不能让多个行业插件直接覆盖同一 Exclusive Artifact。

## 18. Thesis Portfolio 与 Decision 2.0

```python
class ThesisPortfolio(BaseModel):
    primary: Thesis | None
    supporting: tuple[Thesis, ...]
    conflicting: tuple[Thesis, ...]
    unresolved: tuple[Thesis, ...]
    falsified: tuple[Thesis, ...]
```

Decision 不再读取 `theses[0]`。`DecisionAggregationPolicy` 明确：

- 哪些 Falsified/Material Risk 可否决正向状态；
- 冲突 Thesis 如何降级；
- 哪些 Thesis 仅影响 Monitoring；
- 每个 Decision Reason 必须追溯到 Thesis -> Driver -> Metric -> Evidence。

所有时间默认来自 `decision_ts` 或注入的 `Clock`，领域逻辑禁止 `date.today()`。

## 19. Valuation 2.0

保留 v1.5.12 Typed Reconciliation，新增方法级类型：

```text
DCFMethod
PEMethod
PBMethod
EVEBITDAMethod
SOTPMethod
```

首期可以只内置已经有充分输入合同的方法。适用性状态为：

```text
SUPPORTED
CONDITIONALLY_SUPPORTED
SANITY_CHECK_ONLY
CONTRAINDICATED
INSUFFICIENT_EVIDENCE
```

每个状态由规则级经济原因支持，不再把多个主观 0～1 输入乘积作为投资者正文中的伪精确结论。结果继续保留 Bear/Base/Bull、区间、假设、敏感性、Evidence、Assumption 和 Limitation。

## 20. Forecast、Peers 与 Postmortem

### 20.1 Forecast Evaluation

复用 `statsmodels` 和 `scikit-learn`，提供：

- 预注册 Hypothesis；
- PIT cutoff；
- 时间序列交叉验证；
- Benchmark Registry；
- MAE/RMSE/方向准确率；
- 预测区间与覆盖率；
- 稳定性窗口；
- Feature lineage；
- Model Card；
- Promotion/Rollback Policy。

模型只有在样本外优于已登记简单 Benchmark 且通过稳定性门禁时晋级。

### 20.2 Peer Normalization

归一化维度包括业务模型、会计准则、币种/尺度、财年、报告期、合并范围、租赁、一次性项目、少数股东、股本口径、估值日期和分部结构。不可比较时返回类型化差异，不伪造排名。

### 20.3 Postmortem Attribution

错误分类：

```text
DATA
BASIS
FORMULA
MODEL
ASSUMPTION
DRIVER_JUDGMENT
TIMING
EXOGENOUS_EVENT
PRESENTATION
```

对比 Prior Research State 与 Realized Outcome，输出归因、校准和流程改进建议；不把外生冲击伪装成模型失败。

## 21. Reporting 与 Presentation

保持唯一单向链：

```text
ResearchRunResult
  -> HumanReadableResearchView
  -> ResearchReportDocument
  -> MarkdownPresentationArtifact
  -> HtmlPresentationArtifact
  -> PdfPresentationArtifact
```

1.6.0 当前实现使用稳定文件名：

```text
reporting/research_view.py
reporting/composer.py
reporting/markdown_renderer.py
presentation/html_renderer.py
presentation/pdf_adapter.py
```

当前代码不继承 `*_v1_5_x.py`。Semantic Preservation 指纹扩展到类型化 Artifact Snapshot；Presentation 只能翻译、筛选、排序、组合和格式化，不能重新计算研究意义。

## 22. 历史重放

### 22.1 Profile

```python
class ReplayProfile(BaseModel):
    profile_id: str
    source_commit_sha: str
    runner_script: str
    fixture_dir: str
    expected_product_version: str
    frozen: bool
```

### 22.2 执行

- CI checkout 使用 `fetch-depth: 0`；
- HistoricalReplayExecutor 创建临时 detached worktree；
- 在历史提交目录执行该版本 runner；
- 输出复制到当前 build 目录；
- 清理 worktree；
- 当前源码不导入历史模块。

历史 Profile 固定到 1.5.08–1.5.12 各自 release commit。1.6.0 当前 Profile 在当前 checkout 执行。

## 23. 错误处理

统一错误层次：

```text
ContractError
  ├─ ArtifactContractError
  ├─ PluginCompatibilityError
  ├─ PlanCompilationError
  └─ SnapshotSchemaError

ResearchExecutionError
  ├─ ModuleExecutionError
  ├─ CompletionEvaluationError
  └─ PersistenceError
```

错误跨边界时保留 `run_id`、`module_id`、`plugin_id`、`artifact_id`、`request_id` 等责任定位信息，但投资者正文不暴露堆栈和内部路径。

## 24. 工程质量

复用成熟工具：

- Ruff：格式化与 Lint；
- mypy：核心合同严格类型检查；
- import-linter：依赖方向；
- pytest：单元、契约、集成、回归；
- Hypothesis：期间、比例、序列化与 Reducer 属性测试；
- pip-audit：依赖漏洞；
- `python -m build`：wheel/sdist；
- Playwright：真实 Chromium PDF。

CI 分为 quality、unit、integration、acceptance、security/package、release-gate。Release Gate 聚合结果，不重新实现检查。

## 25. 数据库迁移

1.6.0 新增 Alembic migration，至少创建：

```text
research_run
research_snapshot
artifact_index
```

并补足 Evidence PIT/revision 索引。Migration 必须从现有 1.5.12 数据库升级，且 downgrade 行为明确：允许删除 1.6.0 新表，但不修改旧 Evidence 数据。

## 26. 单提交交付

最终交付建立在基线 SHA 之上，仅有一个新 release commit：

```text
72ab06c619678b35c31cf7edef7547849e803d16
    -> release: architecture convergence and professional research foundation v1.6.0
```

开发期间可以在隔离 worktree 中形成内部检查点，但交付前必须：

1. 重新读取远端 `main`，确认仍指向冻结基线；
2. 将所有变更 squash/reset 为单个 commit；
3. 运行完整验证；
4. 生成源码包、binary patch、git bundle/format-patch、SHA256SUMS 和推送说明；
5. 用户将该唯一 commit fast-forward 到 `main`；
6. 禁止 force-push 和历史重写。

## 27. 验收标准

### 27.1 架构

- 只有 Engine 调用 `ResearchModule.run()`；
- 每个 Exclusive Artifact 只有一个 Provider；
- 每个 Collection Artifact 有唯一 Reducer；
- Engine 返回后无 canonical semantic write；
- 当前 Reporting 不导入历史版本实现；
- Domain 不导入 API、Persistence、Presentation 或 Release。

### 27.2 契约

- Core API/Plugin API 1.0 对 1.6.0 明确不兼容；
- 所有新 Artifact 有类型、Schema 版本和 Provider；
- Product/Core/Plugin/Snapshot/HTTP 版本独立且一致；
- Snapshot 可在进程重启后读取和验证；
- v1 Snapshot 可只读，不被重算。

### 27.3 业务

- 财务值具有币种、单位、期间和 Accounting Scope；
- 跨指标比较先校验 Basis 和 Metric Kind；
- Router 输出证据覆盖、歧义和置信等级，不输出伪概率；
- Decision 使用 ThesisPortfolio；
- 估值状态有经济原因，Reconciliation 不被展示层重算；
- Forecast 必须通过 PIT、Benchmark 和样本外门禁；
- Peer 不可比时失败关闭；
- Postmortem 区分模型错误与外生事件。

### 27.4 发布

- 完整 pytest、Ruff、mypy、import-linter、pip-audit 通过；
- wheel/sdist 构建、安装和 smoke test 通过；
- Alembic 从 1.5.12 升级通过；
- 1.5.08–1.5.12 历史 replay 通过；
- 1.6.0 当前 field acceptance 通过；
- Markdown、HTML、真实 PDF 通过；
- 生产源码不含验收公司身份分支；
- 最终交付相对基线仅有一个 commit。
