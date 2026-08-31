# Research OS 1.6.0 M2：Snapshot、Persistence 与 HTTP API 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将研究运行和 Snapshot 从进程内原型升级为可持久化、事务一致、规范序列化、可验证的审计基础设施，并建立只读 HTTP API v1。

**Architecture:** Application 依赖 Repository/UnitOfWork Port；SQLAlchemy 实现在 `adapters/persistence`。Snapshot Schema 2.0 使用规范 JSON 和 SHA-256。HTTP Adapter 依赖 Query Service，不直接持有数据库 Session。

**Tech Stack:** SQLAlchemy 2、Alembic、Pydantic 2、FastAPI、RFC 8785/JCS 实现、SHA-256、pytest、Hypothesis。

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-6-0-architecture-convergence-design.md`

## Global Constraints

- M1 的 `ArtifactSnapshot`、`ResearchRunResult` 和 `RunVersionSet` 已冻结。
- 正式存储不得使用全局内存字典；内存 Repository 仅为测试适配器。
- 旧 Snapshot 只读，不改 hash、不补字段、不重新研究。
- API 首期只读，不增加交易、研究结论修改或任意 SQL 查询能力。

---

### Task 1：Snapshot Schema 2.0 模型

**Files:**
- Create: `src/research_os/snapshots/models.py`
- Modify: `src/research_os/snapshots/__init__.py`
- Create: `tests/unit/snapshots/test_models.py`

- [ ] 写 RED 测试：Schema/Codec/Hash 版本必填，UTC 时间、run/company/baseline/version/fingerprint 必填。
- [ ] 写 RED 测试：NaN、Infinity、无 Schema Artifact 和可变 payload 被拒绝。
- [ ] 实现冻结的 `ResearchSnapshotV2`、`ResearchSnapshotPayloadV2`、`ArtifactFingerprint`、`ResearchSnapshotDescriptor`。

### Task 2：规范序列化与哈希

**Files:**
- Create: `src/research_os/snapshots/codec.py`
- Create: `tests/unit/snapshots/test_codec.py`
- Create: `tests/property/snapshots/test_canonicalization_properties.py`

**Interfaces:**

```python
class SnapshotCodecV2:
    codec_version = "jcs-1"
    def encode(self, payload: ResearchSnapshotPayloadV2) -> bytes: ...
    def digest(self, payload: ResearchSnapshotPayloadV2) -> str: ...
```

- [ ] 写 RED 测试：对象 key 顺序不影响 bytes/hash。
- [ ] 写 RED 测试：Datetime、Decimal、Enum、Pydantic Model 有唯一规范形式。
- [ ] 写 RED 测试：未知对象类型、非字符串 key、NaN/Infinity 失败关闭。
- [ ] 复用 RFC 8785/JCS 库，不用 `default=str` 或自行发明浮点规则。
- [ ] 用 Hypothesis 验证确定性与 round-trip normalization。

### Task 3：Repository Port 与内存实现

**Files:**
- Create: `src/research_os/snapshots/repository.py`
- Create: `src/research_os/application/repositories.py`
- Create: `tests/unit/snapshots/test_repository_contract.py`

- [ ] 定义 Snapshot/Run/Evidence Repository Protocol 和分页 Query 类型。
- [ ] 写共享 Repository Contract Tests。
- [ ] 实现 InMemory Adapter，只用于测试，复制输入并返回不可变值。
- [ ] Append-only：重复 Snapshot ID、重复 Run ID、替换版本均失败。

### Task 4：SQL Schema、Mapper 与 Alembic

**Files:**
- Create: `src/research_os/adapters/__init__.py`
- Create: `src/research_os/adapters/persistence/__init__.py`
- Create: `src/research_os/adapters/persistence/db.py`
- Create: `src/research_os/adapters/persistence/schema.py`
- Create: `src/research_os/adapters/persistence/mappers.py`
- Create: `alembic/versions/0004_v1_6_run_snapshot.py`
- Create: `tests/integration/storage/test_v1_6_migration.py`

- [ ] 写 RED migration test：从 1.5.12 head 升级后存在 `research_run`、`research_snapshot`、`artifact_index`。
- [ ] 写 RED test：升级不改写旧 `evidence` 行。
- [ ] 实现主键、唯一约束、外键和 PIT/decision_ts 索引。
- [ ] Downgrade 仅删除新增表/索引，不删除旧数据。
- [ ] SQLite 作为契约后端；对生产数据库差异保持 SQLAlchemy 可移植性。

### Task 5：Sql Repository 与 UnitOfWork

**Files:**
- Create: `src/research_os/adapters/persistence/evidence_repository.py`
- Create: `src/research_os/adapters/persistence/run_repository.py`
- Create: `src/research_os/adapters/persistence/snapshot_repository.py`
- Create: `src/research_os/adapters/persistence/unit_of_work.py`
- Create: `tests/integration/storage/test_sql_repositories.py`
- Create: `tests/integration/storage/test_unit_of_work.py`

- [ ] 写 RED：进程重启后 Snapshot 可读取并验证。
- [ ] 写 RED：Run/Snapshot 同事务提交，任一失败时整体 rollback。
- [ ] 写 RED：latest-as-of 在数据库侧选择 publish_ts/revision 最新记录。
- [ ] 使用窗口函数或相关子查询，不在 Python 中读取全部 revision 后归并。
- [ ] Mapper 保留 comparison_basis、metric_kind 和 v1.5.12 新语义字段。

### Task 6：SnapshotService 与 Run 持久化

**Files:**
- Modify: `src/research_os/snapshots/service.py`
- Modify: `src/research_os/application/service.py`
- Create: `tests/integration/runtime/test_run_snapshot_transaction.py`

- [ ] 写 RED：Application 完成后写入 Run + Snapshot + Artifact Index。
- [ ] 写 RED：hash 覆盖 payload、versions、component/artifact fingerprints。
- [ ] 写 RED：篡改数据库 payload 或版本后 `verify()` 返回明确失败原因。
- [ ] SnapshotWriter 不改变 Artifact 值，只序列化最终 Snapshot。

### Task 7：v1 Snapshot 只读 Reader

**Files:**
- Create: `src/research_os/compat/__init__.py`
- Create: `src/research_os/compat/v1/__init__.py`
- Create: `src/research_os/compat/v1/snapshots.py`
- Create: `tests/unit/compat/test_v1_snapshot_reader.py`

- [ ] 写 RED：读取 1.x payload 保留原版本/hash/字段。
- [ ] 写 RED：Reader 不允许 save、upgrade-in-place 或产生 1.6 Decision。
- [ ] 提供 `LegacySnapshotView` 和明确 `READ_ONLY_LEGACY_SNAPSHOT` 状态。

### Task 8：Query Service

**Files:**
- Create: `src/research_os/api/query.py`
- Create: `tests/unit/api/test_query_service.py`

**Interfaces:**

```python
class ResearchQueryService:
    def get_run(self, run_id: str) -> ResearchRunView: ...
    def get_artifact(self, run_id: str, artifact_id: str) -> ArtifactView: ...
    def list_snapshots(self, query: SnapshotQuery) -> SnapshotPage: ...
    def get_snapshot(self, snapshot_id: str) -> SnapshotView: ...
    def get_research_view(self, snapshot_id: str) -> HumanReadableResearchView: ...
```

- [ ] 写 RED：not found、无效 cursor、超限 limit、PIT 上界。
- [ ] Query Service 只依赖 Repository/Projector Port。
- [ ] Artifact Query 必须返回 Schema、Provider 和 Evidence metadata。

### Task 9：HTTP API v1 合同

**Files:**
- Create: `src/research_os/api/contracts.py`
- Modify: `src/research_os/api/app.py`
- Create: `src/research_os/api/errors.py`
- Replace/Expand: `tests/integration/api/test_research_routes.py`
- Create: `tests/contract/api/test_openapi_v1.py`

- [ ] 写 RED：所有 `/api/v1` endpoints、分页、PIT 参数和 response_model。
- [ ] 写 RED：错误为 `application/problem+json`，包含稳定 type/status/request_id。
- [ ] 写 RED：每个响应含 `X-Request-ID`，允许上游合法 ID，拒绝控制字符。
- [ ] 写 RED：HTTP API 版本不等于 Core API 版本。
- [ ] 实现 middleware、exception handlers 和 typed DTO。
- [ ] 删除正式 `ResearchReadStore` 默认路径；内存 Query Adapter 放到 tests helper。

### Task 10：M2 出口门禁

- [ ] `alembic upgrade head -> downgrade -1 -> upgrade head` 通过。
- [ ] Snapshot restart/tamper/append-only tests 通过。
- [ ] Evidence latest-as-of SQL query tests 通过。
- [ ] API integration 与 OpenAPI golden contract 通过。
- [ ] 确认 API/Persistence 未被 Domain 导入。
- [ ] 不创建 release commit。
