# ADR-0002：Research OS 1.6.0 受控破坏性契约升级

- **状态：** Proposed，随 Research OS 1.6.0 实施并在发布前转为 Accepted
- **日期：** 2026-08-31
- **行为基线：** `zoucx80-rgb/Research-OS@72ab06c619678b35c31cf7edef7547849e803d16`
- **评审时 main：** `zoucx80-rgb/Research-OS@812b6212410723bc80ed6222b5c78bbc74917390`
- **交付父提交：** M1 启动时冻结的、包含本次设计修订的最新 `main` HEAD（发布证据记录精确 SHA）
- **目标产品版本：** `1.6.0`
- **目标 Core API：** `2.0`
- **目标 Plugin API：** `2.0`
- **目标 Snapshot Schema：** `2.0`
- **目标 HTTP API：** `v1`

## 背景

Research OS 1.5.12 已建立 PIT、证据血缘、缺失值保护、比较口径安全、语义保持、Claim Strength、Cycle/Moat 状态、估值对账、单向报告链和历史重放机制。与此同时，当前运行时仍有三类结构性风险：

1. `ResearchEngine` 之外仍能直接执行插件模块或在执行结束后写入语义 Artifact；
2. 运行边界仍大量使用字符串 Artifact ID 与 `dict[str, Any]`；
3. Snapshot、Storage、HTTP API 和插件发现仍处于原型或半类型化状态。

这些问题无法通过普通 PATCH 的局部兼容修补彻底解决。用户已决定让现有调用方统一迁移，同时将产品版本保持在 `1.x` 演进，因此本次产品版本采用 `1.6.0`，但独立接口契约升级为 `2.0`。

## 决策

本 ADR 仍为 `Proposed`，直到实现、验证和发布门禁完成后才转为 `Accepted`。该状态不是发布批准，也不改变 v1.6.0 当前未实施事实。

### 1. 产品版本与接口版本独立演进

Research OS 产品版本使用 `1.6.0`。以下接口单独表达兼容性：

```text
Research OS Product  1.6.0
Core API             2.0
Plugin API           2.0
Snapshot Schema      2.0
HTTP API             v1
```

`1.6.0` 是一次明确记录的 **breaking migration release**。不得继续声称它与 1.5.x Runtime、Plugin 或 Snapshot 写入接口向后兼容。

### 2. 模块化单体保持不变

不拆微服务，不引入内部消息总线、通用工作流平台或重量级依赖注入框架。应用层负责编排，领域层负责研究语义，适配器层负责数据库、HTTP、浏览器和外部插件发现。

### 3. 唯一模块执行权威

生产代码中只有 `ResearchEngine` 可以调用 `ResearchModule.run()`。插件不得在模块内部再次执行模块，Runtime/Finalizer 不得在 Engine 返回后重算或覆盖语义 Artifact。

### 4. 类型化 Artifact 与 Capability

Core API 2.0 使用 `ArtifactKey[T]`、`ArtifactDefinition[T]`、`ArtifactWrite[T]`、`ArtifactStore` 和不可变 `ArtifactSnapshot`。Artifact 分为：

- `exclusive`：唯一 Provider；
- `collection`：允许多个 Contributor，但必须登记唯一、确定性的 Reducer。

### 5. Plugin API 2.0 提供领域服务而不是嵌套运行时

插件公开适用性、KPI Provider、估值方法、策略贡献和报告贡献。插件不能要求核心调用私有 `_pack`，也不能拥有第二套模块执行策略。外部发现复用 `importlib.metadata.entry_points()`；版本约束复用 `packaging.version` 与 `packaging.specifiers`。

### 6. Snapshot Schema 2.0 是持久化审计合同

Snapshot 使用规范化 JSON、显式 Schema/Codec/Hash 版本和 SHA-256。Snapshot Repository 为 append-only；旧 1.x Snapshot 只读，不原地重写。

### 7. 历史重放绑定历史提交

历史 1.5.08–1.5.12 重放不再从当前源码继承或复制逻辑。Release Replay Profile 绑定历史 commit SHA，发布验证器在临时 Git worktree 中执行该提交的 runner。当前 CI 必须获取所需历史提交，但历史实现不进入 1.6.0 当前运行依赖。

### 8. Completion 与 Readiness 分开

- `ExecutionCompletionResult`：机器研究执行是否完成；
- `ResearchReadinessAssessment`：专业研究内容是否达到发布准备度。

Readiness 不能成为第二 Decision Engine 或第二 Completion Gate。

唯一顺序为 `Engine modules -> CompletionEvaluator -> ReadinessEvaluator -> Finalizer`。Completion 排除 Readiness；缺证据/无覆盖/`NOT_APPLICABLE` 是可审计的类型化状态，未登记 Provider 或依赖循环才在编译期失败。异常终止不生成有效结论，Finalizer 不能补写语义。

### 9. Revision-bound PIT 与 Snapshot 投影

Phase A 创建绑定 `company_id + decision_ts` 的不可变 `FactView`。所有事实引用必须包含 evidence ID、具体 revision 和 content fingerprint；旧的 ID-only/无 cutoff 读取不属于 v2 边界。Snapshot 同时定义不含 run/snapshot 时间身份的研究语义指纹投影，以及包含完整 envelope 的完整性指纹投影；受控 codec 负责类型解码，未知 Schema/动态 import 一律失败。

### 10. 历史 replay 隔离

HistoricalReplayExecutor 显式绑定目标 worktree 的解释器、依赖和 `sys.path`，清理或绑定 `GITHUB_SHA`，并断言导入文件、产品/API 版本和 Git HEAD 匹配；无依赖锁时只声明记录环境复放。

## 影响

### 正面影响

- 消除双执行器和双语义权威；
- 编译期/测试期发现 Artifact 类型和版本错误；
- 插件可扩展但不污染核心编排；
- Snapshot 可跨进程持久化、验证和审计；
- 当前代码与历史重放物理隔离；
- 研究专业能力可通过 Metric/Policy/Method Registry 稳定扩展。

### 成本

- 所有现有 Core API 1.0 调用方和插件必须迁移；
- 现有测试、脚本和 fixtures 的调用入口需要更新；
- 需要新增数据库迁移；
- 需要一次完整的历史重放、安装包、API 和真实 PDF 验证。

## 被否决的方案

### 在 1.6.0 中继续维持 Core API 1.0

否决。接口已经发生结构性破坏，保留相同 API 版本会让旧插件被错误识别为兼容。

### 为 1.x 和 2.x 长期维护两套正式 Runtime

否决。只保留一次性输入迁移工具和旧 Snapshot 只读 Reader，不保留第二套长期研究执行路径。

### 将系统拆成微服务

否决。当前规模和耦合形态适合模块化单体；分布式事务、远程调用和运维成本不能带来等量收益。

### 继续新增 `*_v1_6_0.py` 活跃实现

否决。当前实现使用稳定、无版本后缀模块；历史实现由 commit-addressed replay 保留。

## 强制验证

1. 除 `ResearchEngine` 外，生产源码不得调用 `.run(context, state)`；
2. Engine 返回后不得写入 canonical semantic Artifact；
3. Manifest、实际组件指纹、Run Result、Snapshot 和 AuditAppendix 版本完全一致；
4. 1.5.08–1.5.12 历史 replay 在对应历史提交中通过；
5. 1.6.0 当前 acceptance 同时验证机器语义与 Markdown/HTML/PDF；
6. 生产源码不得包含验收公司身份特例；
7. Core API 1.0 和 Plugin API 1.0 对 1.6.0 明确失败并给出可操作迁移错误。
