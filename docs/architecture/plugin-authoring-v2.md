# Research OS Plugin Authoring Contract 2.0

## 1. 设计边界

Plugin API 2.0 扩展行业研究策略和跨行业方法，不拥有 PIT、Evidence Lineage、Artifact Store、Module Execution、Completion、Snapshot 或 Release Governance。

插件必须是 run-scoped 或无状态。禁止 import-time 注册到全局可变 Registry。

## 2. Manifest

```python
class PluginManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    plugin_id: str
    plugin_type: Literal["industry", "methodology"]
    plugin_version: str
    plugin_api_version: Literal["2.0"]
    core_api_specifier: str
    research_os_specifier: str
    supported_business_models: frozenset[str]
    service_capabilities: frozenset[str]
    priority: int = 100
    maturity: Literal[
        "experimental", "candidate", "stable", "deprecated"
    ]
```

版本和范围分别使用 `packaging.version.Version` 与 `SpecifierSet`。重复 ID、无效版本、范围不兼容、声明与对象形状不一致均失败关闭。

## 3. Industry Plugin

```python
@runtime_checkable
class IndustryPlugin(Protocol):
    manifest: PluginManifest

    def applicability(
        self,
        context: ResearchContext,
        business_model: BusinessModelProfile,
    ) -> ApplicabilityResult: ...

    def services(self) -> PluginServices: ...
```

`ApplicabilityResult` 必须包含适用状态、规则级理由、所用证据和限制。没有校准模型时，score 只称为 rule score，不称为概率。

## 4. Methodology Plugin

```python
@runtime_checkable
class MethodologyPlugin(Protocol):
    manifest: PluginManifest

    def supports(
        self,
        context: ResearchContext,
        available_capabilities: frozenset[str],
    ) -> SupportAssessment: ...

    def services(self) -> PluginServices: ...

class SupportAssessment(BaseModel):
    supported: bool
    rationale: tuple[str, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    limitations: tuple[str, ...] = ()
```

方法插件可以贡献估值方法、预测评估器或 Policy，但不能改变 Completion 和 Decision 的唯一权威。`SupportAssessment.evidence_refs` 必须包含支持该方法选择的具体 revision；选中的 `ResolvedPlugin` 和 `StrategyResolution` 保留同一 lineage。纯能力匹配未读取证据时该字段可以为空。

## 5. PluginServices

```python
@dataclass(frozen=True)
class PluginServices:
    kpi_provider: KpiProvider | None = None
    valuation_methods: tuple[ValuationMethod, ...] = ()
    forecast_methods: tuple[ForecastMethod, ...] = ()
    policy_contributions: tuple[PolicyDefinition, ...] = ()
    report_contributions: tuple[ReportContribution, ...] = ()
```

服务对象必须有稳定 `provider_id` 和组件版本。插件不得要求 Core 读取 `_pack` 等私有属性。

Plugin API 2.0 首期不支持通用 `ModuleContribution`。若未来需要模块扩展，必须先通过新的公共合同/ADR 定义可声明依赖和 Artifact 的受控形状；插件始终不能自行执行 Module。

## 6. KPI Provider

```python
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

KPI Provider 选择业务适用指标和输入映射；通用 MetricDefinition/Formula 由 Core Registry 拥有。Provider 不得重新定义不兼容的通用指标。

`FactView`、`ReportingPeriod`、`AccountingScope`、`MetricResult`、`PolicySnapshot` 和只读 `MetricDefinitionRegistry` 的最小公共形状在 M1 冻结。`ReportingPeriod`/`AccountingScope` 由 revision-bound FactSnapshot/FactView 携带，Provider 不接受另一套临时 `calculate(facts, period) -> MetricSet` 签名。内置和外部插件运行同一个 contract test；发现的插件必须声明并实现 API 2.0。

## 7. Valuation/Forecast Method

方法必须：

- 公开类型化输入；
- 声明 Evidence、Assumption 和 Comparison Basis；
- 返回适用性状态和经济理由；
- 缺输入时返回 `INSUFFICIENT_EVIDENCE`；
- 不从产品/renderer 版本推导经济结论。

Forecast 方法还必须提供 `train_cutoff`、每个 fold 的 feature availability、label maturity、`evaluation_ts`、Benchmark、样本外验证和 Model Card。Realized outcome 只可用于其成熟后的历史评估，不能进入当时训练输入。

## 8. Report Contribution

报告贡献只能描述：

- 需要展示的 canonical Artifact；
- 专业问题；
- Required Capability/Evidence；
- 顺序和标题。

不得包含重新计算函数、Decision 规则或未经 Artifact 支持的答案模板。

## 9. Discovery

外部插件使用 Python entry point：

```toml
[project.entry-points."research_os.plugins"]
my_plugin = "my_package.plugin:provider"
```

Core 使用 `importlib.metadata.entry_points()` 读取，并按 Plugin ID 确定性排序。加载失败必须包含 distribution、entry point 和 plugin ID 上下文。

## 10. 隔离与安全

插件不得：

- 修改仓库、Git、Shell 或全局环境；
- 读取或保存凭证；
- 绕过 PIT/Lineage；
- 写未声明 Artifact；
- 直接执行 Runtime Module；
- 定义公司/股票代码特例替代通用业务模型；
- 宣告自动交易状态；
- 修改历史 Snapshot 或 Replay Fixture。

## 11. 测试合同

每个插件至少覆盖：

1. Manifest/API/版本兼容；
2. 适用性与反向证据；
3. 声明能力和实际服务一致；
4. 缺失 Evidence 的失败关闭；
5. 确定性输出和指纹；
6. 异常隔离；
7. 无需修改 `ResearchEngine`；
8. 无私有字段跨边界依赖；
9. 无公司身份生产分支。

测试使用匿名 synthetic fixtures。真实公司 fixture 仅可作为冻结 acceptance evidence。

## 12. Clean-break upgrade

`modules()` 不再是正式 Plugin API。集成方必须重写插件：

- KPI Module 迁移为 `KpiProvider`；
- Report contributions 原类型可映射到 2.0 类型；
- Manifest 将 `api_version` 改为 `plugin_api_version`，并明确 Core/Product specifier；
- 重新构建、安装并发现新的 API 2.0 分发包；当前包不解析、适配或执行 API 1.0 插件。
