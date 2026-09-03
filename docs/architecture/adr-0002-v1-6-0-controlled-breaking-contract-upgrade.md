# ADR-0002：Research OS 1.6.0 受控破坏性契约升级

- **状态：** Accepted
- **日期：** 2026-08-31
- **接受日期：** 2026-09-03
- **行为基线：** `zoucx80-rgb/Research-OS@72ab06c619678b35c31cf7edef7547849e803d16`
- **M4 稳定基线 / M5 delivery parent：** `zoucx80-rgb/Research-OS@abd19bbc7e22d7958df853333e0ba8cedff39f6f`
- **目标产品版本：** `1.6.0`
- **目标 Core API：** `2.0`
- **目标 Plugin API：** `2.0`
- **目标 Snapshot Schema：** `2.0`
- **目标 HTTP API：** `v1`

## 背景

Research OS 1.5.12 已建立 PIT、证据血缘、缺失值保护、比较口径安全、语义保持、Claim Strength、Cycle/Moat 状态、估值对账、单向报告链和历史重放机制。v1.6.0 解决了三类结构性风险：

1. `ResearchEngine` 之外仍能直接执行插件模块或在执行结束后写入语义 Artifact；
2. 运行边界大量使用字符串 Artifact ID 与 `dict[str, Any]`；
3. Snapshot、Storage、HTTP API 和插件发现仍处于原型或半类型化状态。

这些问题无法通过普通 PATCH 的局部兼容修补彻底解决，因此产品版本采用 `1.6.0`，独立接口契约升级为 `2.0`。

## 决策

### 1. 产品版本与接口版本独立演进

```text
Research OS Product  1.6.0
Core API             2.0
Plugin API           2.0
Snapshot Schema      2.0
HTTP API             v1
```

`1.6.0` 是明确记录的 **breaking migration release**。不得声称它与 1.5.x Runtime、Plugin 或 Snapshot 写入接口向后兼容。

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

Snapshot 使用规范化 JSON、显式 Schema/Codec/Hash 版本和 SHA-256。Snapshot Repository 为 append-only。当前包只读写 Schema 2.0，不提供旧 Snapshot Reader、转换器或原地重写；历史 Snapshot 只在对应历史提交的 isolated replay 中使用。

### 7. 历史重放绑定历史提交

历史 1.5.08–1.5.12 重放不从当前源码继承或复制逻辑。Release Replay Profile 绑定历史 commit SHA，发布验证器在 detached worktree 和独立解释器/环境中执行历史提交自己的 runner。当前 CI 获取完整 Git history，但历史实现不进入 1.6.0 当前运行依赖。

### 8. Completion 与 Readiness 分开

- `ExecutionCompletionResult`：机器研究执行是否完成；
- `ResearchReadinessAssessment`：专业研究内容是否达到发布准备度。

Readiness 不能成为第二 Decision Engine 或第二 Completion Gate。唯一顺序为 `Engine modules -> CompletionEvaluator -> ReadinessEvaluator -> Finalizer`。Completion 排除 Readiness；缺证据、无覆盖、`NOT_APPLICABLE` 是可审计的类型化状态，未登记 Provider 或依赖循环才在编译期失败。Finalizer 不能补写语义。

### 9. Revision-bound PIT 与 Snapshot 投影

Phase A 创建绑定 `company_id + decision_ts` 的不可变 `FactView`。所有事实引用包含 evidence ID、具体 revision 和 content fingerprint；ID-only/无 cutoff 读取不属于 v2 边界。Snapshot 分离研究语义指纹与完整性指纹；`SnapshotDescriptor` 不进入自身哈希输入，未知 Schema/动态 import 失败关闭。

### 10. M5 发布历史规则

M1–M4 已分别以 squash commit 进入 `main`，其中 M4 基线固定为 `abd19bbc7e22d7958df853333e0ba8cedff39f6f`。M5 不得重写、重放或重新合入这些过程历史。M5 feature branch 可保留 RED/GREEN/refactor 过程提交，但最终 `main` 必须满足：

```text
M4 main HEAD (abd19bbc...)
    ↓
exactly one M5 squash commit
    ↓
new main HEAD
```

发布前重新获取 `origin/main`；若它不再等于 M4 delivery parent，必须先审查并整合外部提交，禁止 force-push。最终交付包只能在新的 `main` 上、且 `abd19bbc..HEAD` 的 commit count 精确为 `1` 时生成。

## 影响

### 正面影响

- 消除双执行器和双语义权威；
- 编译期/测试期发现 Artifact 类型和版本错误；
- 插件可扩展但不污染核心编排；
- Snapshot 可跨进程持久化、验证和审计；
- 当前代码与历史重放物理隔离；
- 专业研究能力由版本化 Metric/Policy/Method Registry 支撑；
- 发布质量由 Manifest-selected verification packs、分层 CI、真实 PDF、历史 replay、依赖审计和安装包 smoke test 共同约束。

### 成本

- 所有现有 Core API 1.0 调用方和插件必须迁移；
- 调用入口、测试和 fixtures 需迁移；
- 数据库需要 1.6.0 migration；
- 发布需要完整历史 replay、安装包、API 和真实 PDF 验证。

## 被否决的方案

### 在 1.6.0 中继续维持 Core API 1.0

否决。接口已经发生结构性破坏，保留相同 API 版本会让旧插件被错误识别为兼容。

### 为 1.x 和 2.x 长期维护两套正式 Runtime

否决。不提供包内输入转换工具、旧 Snapshot Reader 或第二套研究执行路径；集成方重建 v2 输入和插件，历史复现只在历史提交中执行。

### 将系统拆成微服务

否决。当前规模和耦合形态适合模块化单体；分布式事务、远程调用和运维成本不能带来等量收益。

### 继续新增 `*_v1_6_0.py` 活跃实现

否决。当前实现使用稳定、无版本后缀模块；历史实现由 commit-addressed replay 保留。

## 强制验证

1. 除 `ResearchEngine` 外，生产源码不得调用 `.run(context, state)`；
2. Engine 返回后不得写入 canonical semantic Artifact；
3. Manifest、实际组件指纹、Run Result、Snapshot 和 AuditAppendix 版本完全一致；
4. 1.5.08–1.5.12 历史 replay 在对应历史提交中通过；
5. 1.6.0 当前 acceptance 同时验证机器语义与 Markdown/HTML/真实 PDF；
6. 生产源码不得包含验收公司身份特例；
7. 当前包只暴露 Core API 2.0、Plugin API 2.0、Snapshot 2.0 和新的 application command/result，不含 v1 compatibility surface；
8. M3 专业研究能力必须由 Manifest-selected verification pack 覆盖，不能只依赖 full pytest 的偶然包含；
9. wheel/sdist、依赖审计、twine check 和 clean-venv wheel smoke test 必须通过；
10. 最终 `main` 相对 `abd19bbc7e22d7958df853333e0ba8cedff39f6f` 只能 ahead 1，并在该最终 commit 上重新跑完整 CI。
