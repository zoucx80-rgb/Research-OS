# Research OS v1.3 Architecture Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Research OS from a monolithic research workflow with ad-hoc pack selection into a stable, dependency-aware runtime with versioned core contracts, automatic dual-plugin resolution, compatibility adapters, and reproducible component fingerprints.

**Architecture:** Preserve every v1.2.1 research invariant and validated Manufacturing/Distributor formula while introducing a new `runtime` layer and `plugins` layer. `ResearchOS.complete_run()` remains the compatibility facade; internally it constructs a `ResearchContext`, resolves industry/methodology plugins, executes a capability-driven module pipeline, evaluates completion once, freezes all component fingerprints, and adapts the canonical result back to the legacy response where necessary.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, existing Research OS domain/services, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-29-research-os-v1-3-architecture-foundation-design.md`

## Global Constraints

- Target release is `1.3.0`.
- Keep `main` as the only development branch unless the user explicitly changes the repository workflow.
- Do not force-push or rewrite historical tags/snapshots.
- Preserve PIT, evidence lineage, missing-value semantics, period truthfulness, completion single-source semantics, and legal decision-state validation.
- Do not add production Hotel/Bank/Resource/Consumer/Software industry content in v1.3.
- Do not add company-specific logic, thresholds, names, tickers, or real-company golden fixtures.
- Preserve v1.2.1 ManufacturingPack and DistributorPack formula semantics while moving them behind the new plugin architecture.
- `ResearchOS.complete_run(ResearchRunRequest)` remains available as a compatibility facade.
- Unsupported industry coverage must remain visible and must not receive specialized KPI PASS.
- A research run may emit an extension request but may not edit the repository or promote a generated plugin.
- Historical v1.2.1 snapshots remain readable and are never rewritten.
- All behavior changes use TDD: RED first, then minimal GREEN, then regression.
- Run the full existing suite and Release Gate after architecture integration before claiming completion.

---

## File Structure

Create these focused architecture files:

```text
src/research_os/
├── runtime/
│   ├── __init__.py
│   ├── context.py          # CompanyRef, BaselineFingerprint, Fact/Evidence views, ResearchContext
│   ├── modules.py          # ModuleSpec, ModuleStatus, ModuleResult, ResearchModule protocol
│   ├── state.py            # ResearchState + read-only ResearchStateView
│   ├── engine.py           # dependency resolution + deterministic execution
│   ├── result.py           # ResearchRunResult + ComponentFingerprint
│   ├── builtin_modules.py  # adapters around existing core analytical services
│   └── factory.py          # default runtime composition
├── plugins/
│   ├── __init__.py
│   ├── models.py           # PluginManifest, coverage/extension/result models
│   ├── protocols.py        # IndustryStrategyPack, MethodologyPack, ResearchPlugin
│   ├── registry.py         # registration and compatibility validation
│   ├── resolver.py         # BusinessModelProfile -> StrategyResolution
│   └── builtins.py         # built-in adapters for existing packs + methodology proof plugin
├── knowledge/
│   ├── __init__.py
│   ├── models.py           # KnowledgeQuery / KnowledgeItem
│   └── provider.py         # KnowledgeProvider + Null/InMemory implementations
└── reporting/
    └── contributions.py    # ReportContribution contract
```

Modify these existing files:

```text
src/research_os/version.py
src/research_os/domain/versions.py
src/research_os/kpi/base.py
src/research_os/orchestration.py
src/research_os/snapshots/service.py
src/research_os/reporting/summary.py
research_os_version.json
pyproject.toml
.github/workflows/ci.yml
scripts/release_gate_v1_1.py
README.md
CHANGELOG.md
docs/prompts/stock_research.md
```

Add architecture tests under:

```text
tests/unit/runtime/
tests/unit/plugins/
tests/unit/knowledge/
tests/integration/runtime/
tests/regression/architecture/
```

---

### Task 1: Establish Core API Version and ResearchContext

**Files:**
- Create: `src/research_os/runtime/__init__.py`
- Create: `src/research_os/runtime/context.py`
- Modify: `src/research_os/version.py`
- Modify: `src/research_os/domain/versions.py`
- Test: `tests/unit/runtime/test_context.py`
- Test: `tests/unit/test_version_consistency_v1_3.py`

**Interfaces:**
- Produces: `CORE_API_VERSION`, `CompanyRef`, `BaselineFingerprint`, `EvidenceView`, `FactView`, `LegacyEvidenceView`, `LegacyFactView`, `ResearchOptions`, `ResearchContext`.
- Consumes: existing `Evidence`, `VersionBundle`.

- [ ] **Step 1: Write the RED tests for immutable context and legacy fact/evidence adapters**

```python
from datetime import datetime, timezone

from research_os.domain.evidence import Evidence, ConfidenceGrade
from research_os.runtime.context import (
    BaselineFingerprint,
    CompanyRef,
    LegacyEvidenceView,
    LegacyFactView,
    ResearchContext,
    ResearchOptions,
)
from research_os.version import CORE_API_VERSION


def test_legacy_fact_view_preserves_missing_and_lineage():
    view = LegacyFactView(
        values={"revenue": 100.0, "ocf": None},
        evidence_by_fact={"revenue": ["ev:revenue"]},
    )
    assert view.get("revenue") == 100.0
    assert view.get("ocf") is None
    assert view.get("missing") is None
    assert view.evidence_ids("revenue") == ["ev:revenue"]
    assert view.as_mapping()["ocf"] is None


def test_context_carries_frozen_baseline_and_core_api_version():
    baseline = BaselineFingerprint(
        repository_full_name="zoucx80-rgb/Research-OS",
        repository_id=1350382205,
        branch="main",
        commit_sha="a" * 40,
        research_os_version="1.3.0",
        core_api_version=CORE_API_VERSION,
    )
    context = ResearchContext(
        run_id="run:1",
        company=CompanyRef(company_id="synthetic:1"),
        decision_ts=datetime(2026, 8, 29, tzinfo=timezone.utc),
        baseline=baseline,
        evidence=LegacyEvidenceView([]),
        facts=LegacyFactView(values={}, evidence_by_fact={}),
        options=ResearchOptions(),
    )
    assert context.baseline.core_api_version == "1.0"
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
pytest -q tests/unit/runtime/test_context.py tests/unit/test_version_consistency_v1_3.py
```

Expected: import errors because `research_os.runtime.context` and `CORE_API_VERSION` do not exist.

- [ ] **Step 3: Implement the minimal stable context contract**

`src/research_os/version.py` must expose:

```python
RESEARCH_OS_VERSION = "1.3.0"
CORE_API_VERSION = "1.0"
```

`src/research_os/runtime/context.py` must define Pydantic-frozen identity/context models and adapter classes. `LegacyEvidenceView.as_of()` must filter `publish_ts <= decision_ts`; `LegacyFactView` must preserve `None` exactly and return copied lineage lists.

Use a `KnowledgeView` protocol in this file only as a forward-compatible type boundary; default `knowledge` may be `None` until Task 7 installs a provider.

- [ ] **Step 4: Make `VersionBundle` backward-readable**

Add a defaulted field rather than a required migration:

```python
from research_os.version import CORE_API_VERSION

class VersionBundle(BaseModel):
    ...
    core_api_version: str = CORE_API_VERSION
```

Existing serialized bundles without the field must still validate.

- [ ] **Step 5: Run RED tests plus current version tests**

Run:

```bash
pytest -q tests/unit/runtime/test_context.py tests/unit/test_version_consistency_v1_2_1.py tests/unit/test_version_consistency_v1_3.py
```

Expected: PASS after v1.3 version metadata tests are updated to read the central constant rather than hard-code v1.2.1.

- [ ] **Step 6: Commit Task 1**

```bash
git add src/research_os/runtime src/research_os/version.py src/research_os/domain/versions.py tests/unit/runtime tests/unit/test_version_consistency_v1_3.py tests/unit/test_version_consistency_v1_2_1.py
git commit -m "feat: add v1.3 research context contract"
```

---

### Task 2: Add Module Contract, Artifact State, and Dependency Engine

**Files:**
- Create: `src/research_os/runtime/modules.py`
- Create: `src/research_os/runtime/state.py`
- Create: `src/research_os/runtime/engine.py`
- Test: `tests/unit/runtime/test_engine.py`

**Interfaces:**
- Consumes: `ResearchContext` from Task 1.
- Produces: `ModuleStatus`, `ModuleSpec`, `ModuleResult`, `ResearchModule`, `ResearchState`, `ResearchStateView`, `ResearchEngine`, `PipelineDefinitionError`, `ModuleExecutionError`.

- [ ] **Step 1: Write RED tests for deterministic dependency ordering**

```python
from research_os.runtime.modules import ModuleResult, ModuleSpec
from research_os.runtime.engine import ResearchEngine


class FakeModule:
    def __init__(self, module_id, requires, provides, calls):
        self.spec = ModuleSpec(
            module_id=module_id,
            module_version="1.0.0",
            requires=set(requires),
            provides=set(provides),
        )
        self.calls = calls

    def run(self, context, state):
        self.calls.append(self.spec.module_id)
        return ModuleResult(
            module_id=self.spec.module_id,
            status="PASS",
            artifacts={cap: self.spec.module_id for cap in self.spec.provides},
            evidence_ids=[],
            diagnostics=[],
        )


def test_engine_orders_modules_by_capability_dependencies(context):
    calls = []
    modules = [
        FakeModule("b", {"a.ready"}, {"b.ready"}, calls),
        FakeModule("a", set(), {"a.ready"}, calls),
    ]
    result = ResearchEngine(modules).run(context)
    assert calls == ["a", "b"]
    assert result.module_results["b"].status == "PASS"
```

- [ ] **Step 2: Add RED tests for cycle, missing capability, duplicate exclusive provider, and artifact overwrite**

Tests must assert `PipelineDefinitionError` for:

```text
a -> b -> a cycle
requires={"missing"} without provider
module A and B both provide "business_model.primary" without precedence
module result returning an undeclared artifact capability
```

- [ ] **Step 3: Run engine tests and verify RED**

Run:

```bash
pytest -q tests/unit/runtime/test_engine.py
```

Expected: imports fail.

- [ ] **Step 4: Implement canonical module/status/result contracts**

Use:

```python
ModuleStatus = Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"]
```

`ModuleResult.artifacts.keys()` must be a subset of the module's declared `provides` capabilities.

- [ ] **Step 5: Implement deterministic topological execution**

Requirements:

- sort ready modules by `module_id` to remove registration-order nondeterminism;
- validate the full graph before executing any module;
- expose only `ResearchStateView` to module code;
- engine is the only writer to `ResearchState`;
- store each `ModuleResult` by unique module ID;
- module exceptions become `ModuleExecutionError` with module ID and original exception chained.

- [ ] **Step 6: Run Task 2 tests**

Run:

```bash
pytest -q tests/unit/runtime/test_engine.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 2**

```bash
git add src/research_os/runtime/modules.py src/research_os/runtime/state.py src/research_os/runtime/engine.py tests/unit/runtime/test_engine.py
git commit -m "feat: add dependency-aware research engine"
```

---

### Task 3: Formalize Dual Plugin Contracts and Compatibility Registry

**Files:**
- Create: `src/research_os/plugins/__init__.py`
- Create: `src/research_os/plugins/models.py`
- Create: `src/research_os/plugins/protocols.py`
- Create: `src/research_os/plugins/registry.py`
- Test: `tests/unit/plugins/test_registry.py`
- Test: `tests/unit/plugins/test_manifest_contract.py`

**Interfaces:**
- Consumes: `CORE_API_VERSION`, `ResearchContext`, `ResearchModule`.
- Produces: `PluginManifest`, `ResolvedPlugin`, `CoverageGap`, `ExtensionRequest`, `ApplicabilityResult`, `IndustryStrategyPack`, `MethodologyPack`, `PluginRegistry`, `PluginCompatibilityError`, `DuplicatePluginError`.

- [ ] **Step 1: Write RED manifest/registry tests**

```python
from research_os.plugins.models import PluginManifest
from research_os.plugins.registry import PluginRegistry, PluginCompatibilityError


def manifest(plugin_id="industry:synthetic", api_version="1.0"):
    return PluginManifest(
        plugin_id=plugin_id,
        plugin_type="industry",
        plugin_version="1.0.0",
        api_version=api_version,
        min_research_os_version="1.3.0",
        provides={"kpi.synthetic"},
        requires={"business_model.profile"},
        supported_business_models={"synthetic"},
        maturity="stable",
    )


def test_registry_rejects_incompatible_core_api(fake_plugin):
    fake_plugin.manifest = manifest(api_version="9.0")
    registry = PluginRegistry(core_api_version="1.0", research_os_version="1.3.0")
    with pytest.raises(PluginCompatibilityError):
        registry.register(fake_plugin)
```

Also test duplicate `plugin_id`, invalid empty capability IDs, plugin type mismatch, and min/max Research OS version compatibility.

- [ ] **Step 2: Run tests and verify RED**

```bash
pytest -q tests/unit/plugins/test_registry.py tests/unit/plugins/test_manifest_contract.py
```

Expected: import errors.

- [ ] **Step 3: Implement plugin models and protocols**

Use the exact manifest fields from the spec. Avoid mutable default sets by using `Field(default_factory=set)`.

`IndustryStrategyPack` exposes `applicability`, `modules`, and `report_contributions`.

`MethodologyPack` exposes `supports` and `modules`.

- [ ] **Step 4: Implement registry compatibility checks**

Version checks must use parsed semantic versions rather than lexical string comparison. Add the existing `packaging` dependency only if not already transitively available as a direct project dependency; otherwise implement a tiny internal SemVer parser limited to `MAJOR.MINOR.PATCH` to avoid an unnecessary dependency.

The registry must be deterministic and must never import arbitrary remote code.

- [ ] **Step 5: Run plugin registry tests**

```bash
pytest -q tests/unit/plugins/test_registry.py tests/unit/plugins/test_manifest_contract.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 3**

```bash
git add src/research_os/plugins tests/unit/plugins
git commit -m "feat: add versioned dual plugin contracts"
```

---

### Task 4: Add StrategyResolver and Automatic Industry/Methodology Selection

**Files:**
- Create: `src/research_os/plugins/resolver.py`
- Test: `tests/unit/plugins/test_resolver.py`

**Interfaces:**
- Consumes: existing `BusinessModelProfile`, `PluginRegistry`, plugin protocols.
- Produces: `StrategyResolution`, `StrategyResolver`.

- [ ] **Step 1: Write RED automatic-resolution tests**

Use synthetic plugins and profiles only.

```python
def test_resolver_automatically_selects_matching_industry_plugin(context, registry):
    profile = BusinessModelProfile(
        company_id="synthetic:manufacturer",
        primary_model="manufacturing",
        secondary_models=[],
        confidence=0.9,
        evidence_ids=["ev:model"],
        router_version="router@test",
    )
    resolution = StrategyResolver().resolve(profile, context, registry)
    assert [p.plugin_id for p in resolution.industry_plugins] == ["industry:manufacturing"]
    assert resolution.coverage_gaps == []
```

- [ ] **Step 2: Add RED unsupported-industry test**

```python
def test_resolver_emits_coverage_gap_without_silent_core_fallback(context, empty_registry):
    profile = BusinessModelProfile(
        company_id="synthetic:hotel",
        primary_model="consumer",
        secondary_models=[],
        confidence=0.8,
        evidence_ids=["ev:model"],
        router_version="router@test",
    )
    result = StrategyResolver().resolve(profile, context, empty_registry)
    assert result.industry_plugins == []
    assert result.coverage_gaps[0].gap_type == "industry_strategy"
    assert result.coverage_gaps[0].business_model == "consumer"
```

- [ ] **Step 3: Add RED deterministic mixed-model and methodology tests**

Requirements:

- higher applicability score wins when two industry plugins support the same primary model;
- equal applicability uses manifest `priority`, then `plugin_id` lexical order;
- methodology plugins are selected only when `supports()` is true and their required capabilities can be satisfied;
- explicit override uses `ResearchOptions` and records rationale rather than silently changing selection.

- [ ] **Step 4: Run tests and verify RED**

```bash
pytest -q tests/unit/plugins/test_resolver.py
```

Expected: resolver import failure.

- [ ] **Step 5: Implement deterministic resolver**

The resolver must not instantiate plugins, modify the registry, or execute modules. It only returns selection metadata.

- [ ] **Step 6: Run resolver tests**

```bash
pytest -q tests/unit/plugins/test_resolver.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 4**

```bash
git add src/research_os/plugins/resolver.py tests/unit/plugins/test_resolver.py
git commit -m "feat: add automatic strategy resolution"
```

---

### Task 5: Adapt Existing Manufacturing and Distributor Packs as Built-in Industry Plugins

**Files:**
- Create: `src/research_os/plugins/builtins.py`
- Modify: `src/research_os/kpi/base.py`
- Test: `tests/unit/plugins/test_builtin_industry_plugins.py`
- Test: `tests/regression/architecture/test_v1_2_1_pack_compatibility.py`

**Interfaces:**
- Consumes: existing `ManufacturingPack`, `DistributorPack`, `MetricResult`, new plugin contracts.
- Produces: `ManufacturingIndustryPlugin`, `DistributorIndustryPlugin`, `BuiltinPluginProvider`, compatibility `KpiModule` wrappers.

- [ ] **Step 1: Freeze existing pack semantics in RED compatibility tests**

Re-use anonymous synthetic v1.2.1 regression inputs, not real company data.

The test must run each pack both directly and through its new plugin module and assert equality for:

```text
metric_id
value
status
reason_code
formula_version
evidence_ids
```

Example:

```python
def test_distributor_plugin_preserves_v1_2_1_metrics(distributor_facts, context):
    legacy = {m.metric_id: m for m in DistributorPack().calculate(distributor_facts)}
    plugin_result = run_builtin_industry_plugin("industry:distributor", context)
    migrated = {m.metric_id: m for m in plugin_result.artifacts["kpi.metrics"]}
    assert migrated == legacy
```

- [ ] **Step 2: Run compatibility tests and verify RED**

```bash
pytest -q tests/unit/plugins/test_builtin_industry_plugins.py tests/regression/architecture/test_v1_2_1_pack_compatibility.py
```

Expected: built-in plugin imports fail.

- [ ] **Step 3: Implement thin adapters without rewriting formula code**

The built-in plugin must delegate KPI calculation to the existing pack instance. Do not copy formulas into plugin code.

Each built-in manifest declares:

```text
industry:manufacturing -> supported_business_models={manufacturing, manufacturer}
industry:distributor -> supported_business_models={distributor}
```

Both are `stable` and use `api_version="1.0"`.

- [ ] **Step 4: Preserve `KpiPackRegistry` as a deprecated compatibility facade**

Existing callers of `KpiPackRegistry.default()` and `.resolve()` must continue to work in v1.3. Internally the default runtime no longer relies on it as the primary plugin registry.

Add a docstring deprecation notice only; do not remove the class in v1.3.

- [ ] **Step 5: Run existing KPI and architecture compatibility suites**

```bash
pytest -q tests/unit/kpi tests/unit/plugins/test_builtin_industry_plugins.py tests/regression/architecture/test_v1_2_1_pack_compatibility.py
```

Expected: PASS.

- [ ] **Step 6: Commit Task 5**

```bash
git add src/research_os/plugins/builtins.py src/research_os/kpi/base.py tests/unit/plugins/test_builtin_industry_plugins.py tests/regression/architecture/test_v1_2_1_pack_compatibility.py
git commit -m "refactor: adapt built-in KPI packs to industry plugins"
```

---

### Task 6: Convert Core Orchestration Services into Research Modules

**Files:**
- Create: `src/research_os/runtime/builtin_modules.py`
- Test: `tests/unit/runtime/test_builtin_modules.py`
- Test: `tests/integration/runtime/test_pipeline_statuses.py`

**Interfaces:**
- Consumes: existing validators/services/routers/engines and Task 2 module API.
- Produces built-in modules for the existing research stages.

- [ ] **Step 1: Write RED contract tests for each built-in module's declared capabilities**

At minimum cover these modules:

```text
RepositoryPreflightModule
PITLineageModule
FinancialSanityModule
BusinessModelModule
StrategyResolutionModule
IndustryKpiModule
CapitalEfficiencyModule
FundingLoopModule
DriverThesisModule
ExpectationModule
ForecastDisciplineModule
ValuationModule
DecisionModule
TemporalModule
```

Each test asserts:

- stable `module_id`;
- explicit `requires`/`provides`;
- result status is one canonical ModuleStatus;
- artifacts are declared;
- material outputs carry evidence IDs when evidence exists.

- [ ] **Step 2: Run built-in module tests and verify RED**

```bash
pytest -q tests/unit/runtime/test_builtin_modules.py
```

Expected: import failure.

- [ ] **Step 3: Implement modules as thin service adapters**

Important ownership rules:

- `RepositoryPreflightModule` delegates to existing `PreflightValidator`.
- `PITLineageModule` owns decision-time filtering and fact/evidence consistency checks.
- `BusinessModelModule` delegates to existing `BusinessModelRouter`.
- `StrategyResolutionModule` delegates only to `StrategyResolver` and emits `strategy.resolution`.
- `IndustryKpiModule` executes only resolved industry plugin modules and maps missing primary coverage to `INSUFFICIENT_EVIDENCE`.
- Capital/Funding modules delegate to existing `CapitalEfficiencyEngine`.
- Expectation/Valuation/Decision/Temporal modules delegate to existing v1.2.1 services and preserve their safety behavior.
- `ForecastDisciplineModule` remains `NOT_APPLICABLE` until a real forecast methodology exists.

- [ ] **Step 4: Do not place completion policy inside any ordinary module**

Completion remains a kernel finalization step after the engine has collected module statuses.

- [ ] **Step 5: Run module and current safety-gate tests**

```bash
pytest -q tests/unit/runtime/test_builtin_modules.py tests/unit/completion tests/unit/validation tests/unit/valuation tests/unit/decision
```

Expected: PASS.

- [ ] **Step 6: Commit Task 6**

```bash
git add src/research_os/runtime/builtin_modules.py tests/unit/runtime/test_builtin_modules.py tests/integration/runtime/test_pipeline_statuses.py
git commit -m "refactor: expose research stages as runtime modules"
```

---

### Task 7: Add Knowledge Interface, Report Contributions, and Safe Extension Request

**Files:**
- Create: `src/research_os/knowledge/__init__.py`
- Create: `src/research_os/knowledge/models.py`
- Create: `src/research_os/knowledge/provider.py`
- Create: `src/research_os/reporting/contributions.py`
- Test: `tests/unit/knowledge/test_provider.py`
- Test: `tests/unit/plugins/test_extension_request.py`
- Test: `tests/unit/reporting/test_contributions.py`

**Interfaces:**
- Produces: `KnowledgeQuery`, `KnowledgeItem`, `KnowledgeProvider`, `NullKnowledgeProvider`, `InMemoryKnowledgeProvider`, `ReportContribution`.
- Consumes: `CoverageGap`, `ExtensionRequest` from Task 3.

- [ ] **Step 1: Write RED PIT-aware knowledge tests**

```python
def test_in_memory_knowledge_provider_filters_future_items():
    provider = InMemoryKnowledgeProvider([
        KnowledgeItem(
            knowledge_id="old",
            content={"definition": "known"},
            source_id="source:old",
            publish_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            version="1",
            evidence_ids=["ev:old"],
        ),
        KnowledgeItem(
            knowledge_id="future",
            content={"definition": "future"},
            source_id="source:future",
            publish_ts=datetime(2027, 1, 1, tzinfo=timezone.utc),
            version="1",
            evidence_ids=["ev:future"],
        ),
    ])
    result = provider.query(KnowledgeQuery(topic="definition", as_of=DECISION_TS))
    assert [item.knowledge_id for item in result] == ["old"]
```

- [ ] **Step 2: Write RED extension-request test**

A coverage gap can be converted to a serializable `ExtensionRequest`, but no registry mutation method accepts an `ExtensionRequest` directly.

- [ ] **Step 3: Write RED report-contribution test**

`ReportContribution` contains only presentation metadata and artifact keys; it has no `final_status` or decision-state override field.

- [ ] **Step 4: Run tests and verify RED**

```bash
pytest -q tests/unit/knowledge tests/unit/plugins/test_extension_request.py tests/unit/reporting/test_contributions.py
```

Expected: import failures.

- [ ] **Step 5: Implement minimal interfaces**

`NullKnowledgeProvider.query()` returns `[]` deterministically.

`InMemoryKnowledgeProvider` filters `publish_ts > as_of` for time-stamped items and sorts by `(publish_ts or datetime.min, knowledge_id)`.

- [ ] **Step 6: Run Task 7 tests**

```bash
pytest -q tests/unit/knowledge tests/unit/plugins/test_extension_request.py tests/unit/reporting/test_contributions.py
```

Expected: PASS.

- [ ] **Step 7: Commit Task 7**

```bash
git add src/research_os/knowledge src/research_os/reporting/contributions.py tests/unit/knowledge tests/unit/plugins/test_extension_request.py tests/unit/reporting/test_contributions.py
git commit -m "feat: add knowledge and extension contracts"
```

---

### Task 8: Build Canonical ResearchRunResult, Component Fingerprints, and Snapshot Reproducibility

**Files:**
- Create: `src/research_os/runtime/result.py`
- Modify: `src/research_os/snapshots/service.py`
- Test: `tests/unit/runtime/test_result.py`
- Test: `tests/integration/runtime/test_snapshot_component_fingerprints.py`

**Interfaces:**
- Consumes: module results, strategy resolution, existing `ResearchCompletionResult`, `ResearchSnapshot`.
- Produces: `ComponentFingerprint`, `ResearchRunResult`.

- [ ] **Step 1: Write RED fingerprint tests**

```python
def test_v1_3_snapshot_freezes_selected_component_fingerprints(runtime_result):
    fingerprints = runtime_result.snapshot.payload["component_fingerprints"]
    ids = {item["component_id"] for item in fingerprints}
    assert "core:research-engine" in ids
    assert "industry:manufacturing" in ids
```

- [ ] **Step 2: Add RED reproducibility test**

Freeze a result, then register a newer plugin version in a separate registry. Verifying the old snapshot must retain the original plugin fingerprint and payload hash.

- [ ] **Step 3: Run tests and verify RED**

```bash
pytest -q tests/unit/runtime/test_result.py tests/integration/runtime/test_snapshot_component_fingerprints.py
```

Expected: imports/fingerprint assertions fail.

- [ ] **Step 4: Implement component fingerprints without rewriting the storage schema**

Keep `ResearchSnapshot` compatible. Add component fingerprints and strategy resolution to `payload`. Do not make historical payloads require these new keys.

- [ ] **Step 5: Run snapshot tests including existing reproducibility tests**

```bash
pytest -q tests/unit/runtime/test_result.py tests/integration/runtime/test_snapshot_component_fingerprints.py tests/unit/snapshots tests/integration/storage
```

Expected: PASS.

- [ ] **Step 6: Commit Task 8**

```bash
git add src/research_os/runtime/result.py src/research_os/snapshots/service.py tests/unit/runtime/test_result.py tests/integration/runtime/test_snapshot_component_fingerprints.py
git commit -m "feat: freeze runtime component fingerprints"
```

---

### Task 9: Compose Default Runtime and Migrate `ResearchOS.complete_run` Behind the Facade

**Files:**
- Create: `src/research_os/runtime/factory.py`
- Modify: `src/research_os/orchestration.py`
- Modify: `src/research_os/reporting/summary.py`
- Test: `tests/integration/runtime/test_legacy_facade.py`
- Test: `tests/regression/architecture/test_legacy_run_semantics.py`
- Test: `tests/regression/architecture/test_unsupported_industry_completion.py`

**Interfaces:**
- Produces: `ResearchRuntime`, `ResearchRuntimeFactory.default()`, canonical `run_context()` path.
- Preserves: `ResearchOS.complete_run(ResearchRunRequest)`.

- [ ] **Step 1: Write RED legacy-facade equivalence tests**

For existing anonymous manufacturing and distributor requests, compare the v1.2.1 expected semantic outputs against the v1.3 facade:

```text
profile.primary_model
pack_ids
material KPI values/statuses
funding_state
decision.state
validation_statuses
completion.final_status
```

Do not assert volatile UUID snapshot IDs.

- [ ] **Step 2: Write RED unsupported-industry completion test**

A synthetic consumer/hotel-style profile with no stable industry plugin must produce:

```text
strategy_resolution.coverage_gaps != []
KPI Pack = INSUFFICIENT_EVIDENCE
completion.final_status = INCOMPLETE
blocking_modules contains KPI Pack
```

- [ ] **Step 3: Run tests and verify RED against current orchestration**

```bash
pytest -q tests/integration/runtime/test_legacy_facade.py tests/regression/architecture/test_legacy_run_semantics.py tests/regression/architecture/test_unsupported_industry_completion.py
```

Expected: new runtime/facade expectations fail.

- [ ] **Step 4: Implement `ResearchRuntimeFactory.default()`**

Default construction must register only trusted built-ins and must explicitly inject:

```text
BusinessModelRouter
PluginRegistry
StrategyResolver
NullKnowledgeProvider
built-in runtime modules
ResearchCompletionGate
SnapshotService
```

No import-time global registry mutation.

- [ ] **Step 5: Refactor `ResearchOS.complete_run()` into an adapter**

Implementation sequence:

```text
ResearchRunRequest
 -> build LegacyEvidenceView / LegacyFactView
 -> construct ResearchContext
 -> runtime.run_context(context, legacy_request=req)
 -> canonical ResearchRunResult
 -> legacy ResearchRun adapter
```

Remove duplicated policy decisions from `orchestration.py`; keep Pydantic request/response models there for compatibility if moving them would create unnecessary churn.

- [ ] **Step 6: Make reporting consume canonical completion**

`DecisionSummary`/reporting must not recompute completion. It receives the same `ResearchCompletionResult` generated by the runtime.

- [ ] **Step 7: Run facade, completion, KPI, and snapshot regressions**

```bash
pytest -q tests/integration/runtime tests/regression/architecture tests/unit/completion tests/unit/kpi tests/unit/reporting
```

Expected: PASS.

- [ ] **Step 8: Commit Task 9**

```bash
git add src/research_os/runtime/factory.py src/research_os/orchestration.py src/research_os/reporting/summary.py tests/integration/runtime tests/regression/architecture
git commit -m "refactor: run legacy facade on modular runtime"
```

---

### Task 10: Version v1.3, Add Architecture Release Gates, and Document Plugin Authoring

**Files:**
- Modify: `pyproject.toml`
- Modify: `research_os_version.json`
- Modify: `scripts/release_gate_v1_1.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/prompts/stock_research.md`
- Create: `docs/architecture/plugin-authoring-v1.md`
- Create: `docs/migrations/v1.3.0.md`
- Test: `tests/regression/architecture/test_release_contract_v1_3.py`

**Interfaces:**
- Consumes all prior tasks.
- Produces the v1.3 stable release contract and author documentation.

- [ ] **Step 1: Write RED release-contract tests**

Assert Release Gate source registers these checks:

```text
research_context_contract
module_contract
pipeline_dependency_resolution
plugin_manifest_contract
plugin_compatibility_resolution
industry_auto_resolution
methodology_auto_resolution
unsupported_coverage_gap
plugin_failure_isolation
legacy_request_compatibility
legacy_pack_semantic_compatibility
knowledge_interface_pit
snapshot_component_fingerprints
completion_single_source_v1_3
core_api_version_consistency
```

Also assert CI executes architecture-targeted tests before migration smoke, full pytest, and Release Gate.

- [ ] **Step 2: Run release-contract tests and verify RED**

```bash
pytest -q tests/regression/architecture/test_release_contract_v1_3.py
```

Expected: missing v1.3 gate registrations.

- [ ] **Step 3: Update all public version surfaces to `1.3.0`**

Required surfaces:

```text
research_os.version.RESEARCH_OS_VERSION
pyproject.toml
research_os_version.json
package __version__
runtime default
reporting output
Release Gate banner
```

`CORE_API_VERSION` remains `1.0`.

- [ ] **Step 4: Extend Release Gate without deleting v1.2.1 correctness checks**

Keep every existing gate and append the architecture checks. The final output must be:

```text
READY: v1.3.0 stable
```

only when all gates pass.

- [ ] **Step 5: Update CI execution order**

Required order:

```text
1. architecture targeted tests
2. existing v1.2.1 correctness targeted tests
3. migration/storage smoke
4. full pytest
5. Release Gate
```

- [ ] **Step 6: Write `plugin-authoring-v1.md`**

The document must contain complete examples of:

- an IndustryStrategyPack manifest;
- a MethodologyPack manifest;
- a module with `requires`/`provides`;
- registry registration;
- automatic resolver selection;
- contract-test invocation;
- stable vs experimental maturity;
- forbidden behaviors: company special cases, repository mutation during research, bypassing PIT/lineage/completion.

- [ ] **Step 7: Write `docs/migrations/v1.3.0.md`**

Document:

- legacy facade remains supported;
- `KpiPackRegistry` compatibility status;
- new runtime/plugin paths;
- no required database migration for component fingerprints;
- snapshot backward compatibility;
- plugin authors target `CORE_API_VERSION=1.0`.

- [ ] **Step 8: Update canonical stock prompt**

State that normal users provide the company/security only; industry plugins are resolved automatically. Unsupported coverage emits a gap and does not silently become COMPLETE.

- [ ] **Step 9: Run release-contract test**

```bash
pytest -q tests/regression/architecture/test_release_contract_v1_3.py
```

Expected: PASS.

- [ ] **Step 10: Commit Task 10**

```bash
git add pyproject.toml research_os_version.json scripts/release_gate_v1_1.py .github/workflows/ci.yml README.md CHANGELOG.md docs/prompts/stock_research.md docs/architecture docs/migrations tests/regression/architecture/test_release_contract_v1_3.py
git commit -m "release: prepare Research OS v1.3 architecture gate"
```

---

### Task 11: Full Verification and Architecture Acceptance

**Files:**
- Modify only files required by failures proven during this task.
- Verification only otherwise.

**Interfaces:**
- Consumes the complete v1.3 implementation.
- Produces verification evidence for stable release readiness.

- [ ] **Step 1: Run architecture-targeted tests**

```bash
pytest -q \
  tests/unit/runtime \
  tests/unit/plugins \
  tests/unit/knowledge \
  tests/integration/runtime \
  tests/regression/architecture
```

Expected: PASS.

- [ ] **Step 2: Run existing v1.2.1 correctness regression set**

```bash
pytest -q \
  tests/regression/research_patterns/test_v1_2_1_correctness_patterns.py \
  tests/unit/kpi/test_period_sensitive_packs.py \
  tests/unit/capital/test_engine.py \
  tests/unit/kpi/test_applicability.py \
  tests/unit/completion/test_consistency.py
```

Expected: PASS.

- [ ] **Step 3: Run lineage/storage migration smoke**

```bash
pytest -q tests/integration/storage/test_v1_2_lineage_migration.py
```

Expected: PASS.

- [ ] **Step 4: Run the full suite**

```bash
pytest -q
```

Expected: zero failures.

- [ ] **Step 5: Run the full Release Gate**

```bash
python scripts/release_gate_v1_1.py
```

Expected final line:

```text
READY: v1.3.0 stable
```

- [ ] **Step 6: Run three anonymous architecture acceptance patterns**

Verify:

```text
Pattern A: manufacturing -> automatically resolves industry:manufacturing -> specialized KPI PASS
Pattern B: distributor -> automatically resolves industry:distributor -> specialized KPI PASS
Pattern C: consumer/hotel without plugin -> coverage gap -> KPI Pack INSUFFICIENT_EVIDENCE -> no false COMPLETE
```

No real company names or figures are persisted in these fixtures.

- [ ] **Step 7: Verify snapshot fingerprint stability**

Run the same synthetic request twice with the same baseline and registry; component fingerprint sets and deterministic artifacts must match. Snapshot UUID may differ; payload hashes must match where existing SnapshotService semantics permit.

- [ ] **Step 8: Inspect git diff and secret hygiene**

Run:

```bash
git status --short
git diff --check
git grep -n -E '(ghp_|github_pat_|BEGIN .*PRIVATE KEY|password\s*=|api[_-]?key\s*=)' -- . ':!docs/superpowers'
```

Expected: no accidental secrets and no unrelated files.

- [ ] **Step 9: Commit any verification-only corrections, if proven necessary**

Use a specific message matching the actual correction. Do not create a generic cleanup commit when no change is required.

- [ ] **Step 10: Push verified `main` and re-read remote HEAD**

Verify the remote `main` SHA equals the locally verified commit and do not force-push.

---

## Self-Review Against the Spec

### Spec coverage

- Stable ResearchContext: Task 1.
- Dependency-aware ResearchEngine/module contract: Task 2 + Task 6.
- Dual industry/methodology plugin architecture: Tasks 3–5.
- Automatic plugin resolution: Task 4 + Task 9.
- Unsupported coverage gap: Tasks 4 + 9.
- Safe future extension hook: Tasks 3 + 7.
- Knowledge interface: Task 7.
- Report contribution boundary: Task 7 + 9.
- Component fingerprints/snapshot reproducibility: Task 8.
- Legacy facade and pack compatibility: Tasks 5 + 9.
- Core API/version governance: Tasks 1 + 10.
- Release/contract tests: Tasks 10 + 11.
- No new industry content: enforced globally and in acceptance patterns.

### Placeholder scan

The plan contains no `TBD`, `TODO`, unspecified “write tests”, or undefined implementation hand-waving steps. Each task names exact files, interfaces, commands, and expected test states.

### Type consistency

The plan consistently uses:

```text
ResearchContext
ModuleSpec
ModuleResult
ResearchStateView
PluginManifest
PluginRegistry
StrategyResolver
StrategyResolution
CoverageGap
ExtensionRequest
ComponentFingerprint
ResearchRunResult
CORE_API_VERSION
```

These names match the approved v1.3 design specification.

## Execution Handoff

The plan is intentionally structured so each task is independently reviewable and can be executed directly on `main` under the repository's single-branch policy. When implementation begins, use `superpowers:executing-plans` or `superpowers:subagent-driven-development`, apply TDD to each task, and do not advance past a failed verification gate without root-cause analysis.
