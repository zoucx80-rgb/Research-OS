# Research OS v1.3 Architecture Foundation — Design Specification

**Status:** Approved architecture direction / implementation design

**Target release:** `1.3.0`

**Baseline:** `zoucx80-rgb/Research-OS@21221329832507ad195ca7f93113bbc4dbbe46ad` (`v1.2.1 stable`)

**Date:** 2026-08-29

## 1. Purpose

Research OS v1.3 is an architecture release. Its primary objective is not to add more industry coverage or more investment-research features. Its objective is to make the system structurally stable enough that future methodology changes, industry strategy packs, knowledge sources, and research modules can be added with bounded changes and without repeatedly rewriting the core orchestration path.

The desired long-term property is:

> A company name or security identifier enters one stable research entry point. The system builds a point-in-time research context, identifies the business model, automatically resolves applicable industry and methodology plugins, executes a versioned research pipeline, records coverage gaps instead of fabricating support, freezes all selected component fingerprints, and produces one authoritative research result.

The architectural target is a durable research platform rather than a collection of company-specific prompts or hard-coded workflows.

## 2. Why v1.3 Is Needed

The v1.2.1 acceptance runs across three materially different business models exposed the correct next priority:

- distributor research can use a specialized Distributor KPI Pack;
- manufacturing research can use a specialized Manufacturing KPI Pack;
- a hotel / consumer-service company can be researched analytically, but the machine correctly reports `KPI Pack = INSUFFICIENT_EVIDENCE` because no specialized pack exists;
- current orchestration is still a large concrete workflow that knows too much about individual subsystems;
- plugin-like concepts exist, but registration, dependency resolution, lifecycle, compatibility, and provenance are not yet first-class architecture;
- industry-specific logic and general research methodology are not yet separated into independent extension dimensions;
- future automatic extension must not be implemented as silent self-modification of the production repository.

v1.2.1 deliberately made unsupported coverage visible. v1.3 must now turn that visibility into a stable extension architecture.

## 3. Release Philosophy

v1.3 follows five rules.

### 3.1 Architecture before coverage

Do not add HotelPack, BankPack, ResourcePack, ConsumerPack, SoftwarePack, or similar broad industry content merely to increase coverage in this release.

Existing manufacturing and distributor behavior must be preserved through the new architecture and act as compatibility proofs.

### 3.2 Stable contracts before richer models

Public and cross-module interfaces must be explicit, versioned, small, and testable before new methodology is layered on top.

### 3.3 Core owns invariants; plugins own domain variation

PIT, lineage, missing-value semantics, completion truth, execution contracts, version compatibility, and snapshot reproducibility belong to the core.

Industry-specific KPIs, business drivers, sector-specific evidence requirements, and preferred valuation families belong to industry strategy plugins.

Reusable analytical techniques that cut across industries belong to methodology plugins.

### 3.4 Unsupported means unsupported

A missing plugin must create a visible coverage gap. Generic infrastructure must never be interpreted as specialized analytical coverage.

### 3.5 Evolution without historical mutation

A later Research OS release may improve the core or plugins, but a frozen historical snapshot must retain the exact core, module, and plugin fingerprints that produced it.

## 4. Target Architecture

The v1.3 target is five primary layers plus two cross-cutting control planes.

```text
User / API
    |
    v
+-------------------------------+
|  Report / Presentation Layer  |
+-------------------------------+
              ^
              |
+-------------------------------+
|      Research Engine          |
|  Pipeline / Module Runtime    |
+-------------------------------+
       ^                 ^
       |                 |
+-------------+   +------------------+
| Industry    |   | Methodology      |
| Strategy    |   | Plugins          |
| Plugins     |   |                  |
+-------------+   +------------------+
       ^                 ^
       +--------+--------+
                |
+-------------------------------+
|         Core Kernel           |
| PIT / Lineage / Missing /     |
| Contracts / Completion /      |
| Versions / Snapshot Rules     |
+-------------------------------+
                ^
                |
+-------------------------------+
|        Knowledge Layer        |
| versioned, PIT-aware queries  |
+-------------------------------+

Cross-cutting control planes:
- Plugin Registry + Compatibility Resolver
- Release / Regression / Migration Governance
```

## 5. Core Kernel

The Core Kernel is the most stable layer. It must not contain sector-specific research logic.

### 5.1 Responsibilities

The kernel owns:

- point-in-time validation;
- evidence lineage requirements;
- missing-value semantics;
- reporting-period semantics;
- immutable run identity and baseline fingerprints;
- module execution contract validation;
- plugin manifest compatibility validation;
- authoritative completion evaluation;
- version surfaces and compatibility rules;
- snapshot freezing and reproducibility rules;
- legal research decision-state validation;
- distinction among fact, calculation, statistical evidence, assumption, and conclusion.

### 5.2 Non-responsibilities

The kernel must not know:

- how hotel RevPAR is calculated;
- how semiconductor distributors should model inventory risk;
- how banks should be valued;
- which commodity KPI matters for a mining company;
- what a particular industry thesis should say;
- a company name, ticker, or company-specific threshold.

## 6. Research Context Contract

v1.3 introduces a stable `ResearchContext` as the common input seen by the Research Engine and plugins.

The architectural contract is:

```python
class ResearchContext(BaseModel):
    run_id: str
    company: CompanyRef
    decision_ts: datetime
    baseline: BaselineFingerprint
    evidence: EvidenceView
    facts: FactView
    knowledge: KnowledgeView
    options: ResearchOptions
```

### 6.1 CompanyRef

```python
class CompanyRef(BaseModel):
    company_id: str
    security_id: str | None = None
    exchange: str | None = None
    display_name: str | None = None
```

Identity metadata must not itself become financial evidence.

### 6.2 BaselineFingerprint

```python
class BaselineFingerprint(BaseModel):
    repository_full_name: str
    repository_id: int
    branch: str
    commit_sha: str
    research_os_version: str
    core_api_version: str
```

### 6.3 EvidenceView and FactView

v1.3 establishes interfaces without forcing an all-at-once storage migration.

```python
class EvidenceView(Protocol):
    def as_of(self, decision_ts: datetime) -> list[Evidence]: ...
    def get(self, evidence_id: str) -> Evidence | None: ...


class FactView(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...
    def evidence_ids(self, key: str) -> list[str]: ...
    def as_mapping(self) -> Mapping[str, Any]: ...
```

The existing `facts: dict` request remains supported through a `LegacyFactView` adapter in v1.3. This prevents the architecture release from becoming a simultaneous database/data-contract rewrite.

A richer typed `FinancialFact` / restatement graph can be introduced behind this interface in a later release without changing plugin call sites.

## 7. Research Engine

The current monolithic orchestration flow must become a small pipeline runtime that executes independently testable research modules.

### 7.1 Module contract

```python
class ResearchModule(Protocol):
    spec: ModuleSpec

    def run(
        self,
        context: ResearchContext,
        state: ResearchStateView,
    ) -> ModuleResult: ...
```

```python
class ModuleSpec(BaseModel):
    module_id: str
    module_version: str
    requires: set[str]
    provides: set[str]
    required_for_completion: bool = True
```

```python
class ModuleResult(BaseModel):
    module_id: str
    status: ModuleStatus
    artifacts: dict[str, Any]
    evidence_ids: list[str]
    diagnostics: list[str]
```

`ModuleStatus` uses one canonical vocabulary shared by runtime, completion, snapshot, and report surfaces:

```text
PASS
FAIL
INSUFFICIENT_EVIDENCE
NOT_APPLICABLE
```

### 7.2 Dependency execution

The engine must resolve a deterministic directed acyclic graph from `requires` and `provides` capabilities.

The engine must reject:

- duplicate exclusive capability providers without an explicit precedence rule;
- cycles;
- missing required capabilities;
- module IDs or versions inconsistent with the resolved manifest;
- a plugin attempting to overwrite an immutable artifact produced by a prior module unless the artifact contract explicitly allows replacement.

### 7.3 State ownership

Modules return artifacts; they do not mutate arbitrary global dictionaries.

The engine owns a `ResearchState` artifact store and exposes only a read-only `ResearchStateView` to modules.

This makes lineage, dependency ownership, and module substitution auditable.

## 8. Dual Plugin Architecture

v1.3 formalizes two plugin families.

## 8.1 Industry Strategy Pack

Industry packs answer:

> For this type of business, what must be examined?

Typical responsibilities:

- specialized KPI definitions;
- required and optional evidence families;
- domain driver graph contributions;
- industry-specific risk/falsifier templates;
- preferred valuation model families;
- sector-specific reporting contributions;
- applicability scoring.

Contract:

```python
class IndustryStrategyPack(Protocol):
    manifest: PluginManifest

    def applicability(self, context: ResearchContext) -> ApplicabilityResult: ...
    def modules(self) -> list[ResearchModule]: ...
    def report_contributions(self) -> list[ReportContribution]: ...
```

Existing `ManufacturingPack` and `DistributorPack` must be migrated or wrapped as built-in industry plugins without changing their validated formula semantics during v1.3.

## 8.2 Methodology Pack

Methodology packs answer:

> How should a reusable analytical question be evaluated?

Examples for later releases include:

- capital-efficiency methodology;
- expectation-gap methodology;
- forecast benchmark discipline;
- scenario valuation methodology;
- quality-of-growth methodology;
- cyclicality diagnostics.

Contract:

```python
class MethodologyPack(Protocol):
    manifest: PluginManifest

    def supports(self, context: ResearchContext, state: ResearchStateView) -> bool: ...
    def modules(self) -> list[ResearchModule]: ...
```

Methodology packs must not claim an industry identity merely because they can operate on that industry's data.

## 9. Plugin Manifest

Every plugin has a machine-readable manifest.

```python
class PluginManifest(BaseModel):
    plugin_id: str
    plugin_type: Literal["industry", "methodology"]
    plugin_version: str
    api_version: str
    min_research_os_version: str
    max_research_os_version: str | None = None
    provides: set[str]
    requires: set[str]
    supported_business_models: set[str] = set()
    priority: int = 100
    maturity: Literal["experimental", "stable"] = "experimental"
```

Rules:

1. `plugin_id` is globally unique within a run.
2. Plugin SemVer is independent from Research OS SemVer.
3. `api_version` is the stable plugin-contract version, not the package version.
4. A plugin incompatible with the current core API is rejected before execution.
5. Stable completion claims may depend on stable plugins only unless the run explicitly opts into experimental research.
6. All selected manifests are frozen into the research snapshot.

## 10. Plugin Registry and Resolution

The Registry owns discovery and compatibility. The Router owns business-model inference. The Resolver joins the two.

These responsibilities must not be collapsed into one class.

### 10.1 PluginRegistry

```python
class PluginRegistry:
    def register(self, plugin: ResearchPlugin) -> None: ...
    def manifests(self, plugin_type: str | None = None) -> list[PluginManifest]: ...
    def get(self, plugin_id: str) -> ResearchPlugin | None: ...
```

Built-ins are registered explicitly in v1.3. The registry interface must allow a later provider based on package entry points or another trusted catalog without changing the Research Engine.

### 10.2 StrategyResolver

```python
class StrategyResolver:
    def resolve(
        self,
        profile: BusinessModelProfile,
        context: ResearchContext,
        registry: PluginRegistry,
    ) -> StrategyResolution: ...
```

```python
class StrategyResolution(BaseModel):
    industry_plugins: list[ResolvedPlugin]
    methodology_plugins: list[ResolvedPlugin]
    coverage_gaps: list[CoverageGap]
    rationale: list[str]
```

### 10.3 Default automatic behavior

Normal user input does not need to specify an industry plugin.

Default flow:

```text
Company
  -> PIT evidence
  -> Business Model Router
  -> Strategy Resolver
  -> automatically load compatible Industry Strategy Pack(s)
  -> resolve required Methodology Pack(s)
  -> execute pipeline
```

Manual plugin override is permitted only as an explicit `ResearchOptions` override with rationale recorded in the snapshot.

## 11. Unsupported Industry and Future Automatic Extension

If no compatible industry plugin exists, the resolver returns a `CoverageGap`.

```python
class CoverageGap(BaseModel):
    gap_type: Literal["industry_strategy", "methodology", "capability"]
    business_model: str | None
    missing_capability: str | None
    reason: str
```

The system may still run core validation and generic modules, but specialized KPI coverage remains `INSUFFICIENT_EVIDENCE` and Completion Gate behavior remains authoritative.

### 11.1 Candidate extension hook

v1.3 reserves an output contract for future automatic strategy generation:

```python
class ExtensionRequest(BaseModel):
    company_id: str
    business_model: str
    coverage_gaps: list[CoverageGap]
    evidence_requirements: list[str]
    requested_capabilities: list[str]
```

A research run may emit this request. It must not automatically edit the repository, promote a generated plugin to `stable`, or make the current run retroactively COMPLETE.

A later release may implement:

```text
CoverageGap
 -> Candidate Pack Generator
 -> anonymous/synthetic regression extraction
 -> contract tests
 -> representative-company acceptance runs
 -> human/release approval
 -> registry promotion
 -> later research runs may use it automatically
```

This preserves the desired self-expanding direction without allowing one unvalidated company analysis to mutate production research semantics.

## 12. Knowledge Layer Interface

Knowledge must be pluggable but cannot bypass evidence discipline.

```python
class KnowledgeQuery(BaseModel):
    topic: str
    business_model: str | None = None
    as_of: datetime
    tags: set[str] = set()


class KnowledgeItem(BaseModel):
    knowledge_id: str
    content: Any
    source_id: str
    publish_ts: datetime | None
    version: str
    evidence_ids: list[str]


class KnowledgeProvider(Protocol):
    def query(self, query: KnowledgeQuery) -> list[KnowledgeItem]: ...
```

Rules:

- knowledge is advisory context until tied to evidence or an explicit analyst assumption;
- knowledge providers must honor `as_of` when time-sensitive content is returned;
- a plugin cannot silently convert an unversioned knowledge snippet into a fact;
- the provider ID/version used by a material conclusion is snapshot-visible.

v1.3 only needs a stable interface and a no-op/in-memory implementation. External retrieval systems are future work.

## 13. Report Layer

Reporting must remain a consumer of canonical runtime results.

The report layer receives one `ResearchRunResult` and plugin contributions.

```python
class ReportContribution(BaseModel):
    contribution_id: str
    section: str
    order: int
    artifact_keys: list[str]
    required: bool = False
```

The report layer may format or organize artifacts. It may not:

- independently change `FINAL_STATUS`;
- invent missing metrics;
- promote experimental plugin output to stable status;
- infer a valuation or expectation conclusion that the runtime did not validate.

## 14. Research Run Result

The engine returns one canonical result.

```python
class ResearchRunResult(BaseModel):
    run_id: str
    company: CompanyRef
    decision_ts: datetime
    baseline: BaselineFingerprint
    business_model: BusinessModelProfile
    strategy_resolution: StrategyResolution
    module_results: dict[str, ModuleResult]
    artifacts: dict[str, Any]
    completion: ResearchCompletionResult
    component_fingerprints: list[ComponentFingerprint]
    snapshot: ResearchSnapshot
```

This object is the single source consumed by snapshot, report, API, and future monitoring layers.

## 15. Component Fingerprints and Version Governance

Research OS versioning is separated into three levels.

### 15.1 Research OS release version

`RESEARCH_OS_VERSION = "1.3.0"`

This identifies the packaged product release.

### 15.2 Core API version

`CORE_API_VERSION = "1.0"`

This identifies the stable plugin and module contract family.

The goal is for Research OS 1.3, 1.4, and later compatible releases to evolve internals without forcing all plugins to change if `CORE_API_VERSION` remains compatible.

### 15.3 Component/plugin versions

Every module and plugin records its own version.

```python
class ComponentFingerprint(BaseModel):
    component_id: str
    component_type: str
    component_version: str
    api_version: str | None = None
```

Snapshots must freeze the complete selected fingerprint set rather than only a single `kpi_pack_version` string.

Existing `VersionBundle` remains readable through a compatibility adapter. Historical snapshots are never rewritten.

## 16. Backward Compatibility

v1.3 is a MINOR release and must preserve valid v1.2.1 callers where practical.

### 16.1 Public facade

`ResearchOS.complete_run(ResearchRunRequest)` remains available in v1.3.

Internally:

```text
ResearchRunRequest (legacy-compatible)
  -> LegacyRunAdapter
  -> ResearchContext
  -> ResearchEngine.run(...)
  -> ResearchRunResult
  -> legacy-compatible ResearchRun facade if required
```

### 16.2 Existing KPI packs

The validated calculations in ManufacturingPack and DistributorPack must not be semantically rewritten as part of the architecture migration.

They are moved behind or adapted to the new plugin interfaces.

### 16.3 Existing completion behavior

`ResearchCompletionGate` remains the only completion authority.

The architecture must not broaden COMPLETE semantics.

### 16.4 Existing snapshots

Existing snapshots remain parseable and verifiable.

v1.3 snapshots add component/plugin fingerprint information inside backward-compatible payload/version structures unless a migration is proven necessary by implementation tests.

No migration is added solely for architectural aesthetics.

## 17. Dependency Injection and Construction

The current `ResearchOS.__init__` directly constructs concrete engines. v1.3 replaces this internally with explicit composition.

Target construction:

```python
runtime = ResearchRuntime(
    kernel=CoreKernel(...),
    registry=PluginRegistry(...),
    resolver=StrategyResolver(...),
    engine=ResearchEngine(...),
    knowledge=KnowledgeProvider(...),
    reporter=ReportAssembler(...),
)
```

A default factory builds the production runtime:

```python
runtime = ResearchRuntimeFactory.default()
```

Tests may inject deterministic fakes without monkey-patching production global state.

## 18. Failure and Isolation Rules

Plugin failures must be contained and explicit.

A plugin cannot:

- modify another plugin's registry entry during a run;
- mutate the frozen `ResearchContext`;
- alter PIT-filtered evidence;
- override CompletionResult after evaluation;
- write to the methodology repository during stock research;
- silently fall back from an incompatible API version;
- claim a capability it did not declare in its manifest.

Plugin execution errors produce a module failure diagnostic and follow the Completion Gate's normal blocking policy.

## 19. Testing Architecture

v1.3 establishes architecture-level tests in addition to existing semantic tests.

### 19.1 Contract tests

Every plugin must pass a shared contract suite:

- valid manifest;
- compatible API version;
- declared capabilities equal actual module capabilities;
- deterministic resolution for the same context;
- missing input stays missing;
- all material artifacts retain evidence lineage.

### 19.2 Pipeline tests

Test:

- dependency ordering;
- missing capability failure;
- cycle rejection;
- duplicate provider conflict;
- deterministic run order;
- plugin failure isolation;
- authoritative CompletionResult propagation.

### 19.3 Compatibility tests

Existing v1.2.1 representative inputs for Manufacturing and Distributor must produce semantically equivalent KPI and decision behavior through the compatibility facade.

### 19.4 Unsupported coverage test

A synthetic hotel/consumer-service company with no matching plugin must resolve to a coverage gap and `KPI Pack = INSUFFICIENT_EVIDENCE`; generic Core infrastructure must not turn that into PASS.

### 19.5 Snapshot reproducibility

A snapshot records:

- frozen Research OS baseline;
- core API version;
- selected plugin IDs/versions;
- selected module IDs/versions;
- resolver result;
- completion result.

Reproduction must use the frozen selection, not re-run latest plugin discovery.

## 20. Release Gates for v1.3

The stable gate must retain every v1.2.1 correctness check and add at least:

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

`READY: v1.3.0 stable` is legal only after the full suite and all release checks pass.

## 21. v1.3 Scope

### In scope

- stable ResearchContext and facade adapter;
- modular ResearchEngine and ResearchModule contract;
- canonical ModuleResult/status contract;
- dual plugin interfaces;
- PluginManifest;
- PluginRegistry;
- StrategyResolver;
- automatic loading of existing compatible built-in industry plugins;
- methodology plugin infrastructure with at least one compatibility/built-in proof;
- coverage-gap and ExtensionRequest contracts;
- knowledge provider interface and no-op/in-memory provider;
- report contribution contract;
- core API versioning;
- component fingerprints in v1.3 snapshots;
- compatibility adapters for v1.2.1 public interfaces;
- architecture contract tests and release gates;
- migration and architecture documentation.

### Explicitly out of scope

- production HotelPack;
- production BankPack;
- production ResourcePack;
- production ConsumerPack;
- production SoftwarePack;
- automated candidate-pack code generation;
- automatic commits or automatic promotion of generated plugins;
- external plugin marketplace;
- remote code execution;
- complete typed FinancialFact/restatement database redesign;
- new forecast algorithms;
- new valuation models merely for feature growth;
- company-specific rules or fixtures;
- weakening any v1.2.1 safety gate.

## 22. Follow-on Architecture Roadmap

The architecture may continue across multiple releases rather than forcing everything into v1.3.

### v1.3 — Runtime and Plugin Foundation

Deliver the stable core/module/plugin contracts and compatibility migration described in this specification.

### v1.4 — Data and Knowledge Contract Hardening

Candidate scope:

- typed FinancialFact and observation contracts behind FactView;
- first-class restatement/supersession lineage;
- accounting-basis metadata;
- richer PIT knowledge providers;
- data-quality/materiality weighting.

### v1.5 — Plugin Lifecycle and Validation Infrastructure

Candidate scope:

- candidate plugin workspace;
- plugin scaffold generator;
- plugin conformance harness;
- anonymous real-research regression extraction;
- promotion workflow from experimental to stable;
- compatibility matrix across core API versions.

### v1.6 — Safe Assisted Extension

Candidate scope:

- consume ExtensionRequest;
- generate candidate industry/methodology plugin drafts;
- automatically run contract/synthetic regression suites;
- require release approval before stable registration;
- never retroactively alter the run that discovered the gap.

The exact release split after v1.3 may change as implementation evidence accumulates. The architectural direction does not.

## 23. Acceptance Criteria

v1.3 is complete only when all of the following are true.

1. A caller can submit the same kind of stock-research request used in v1.2.1 without manually specifying an industry plugin.
2. The Router and StrategyResolver automatically select the existing manufacturing or distributor industry plugin when applicable.
3. An unsupported industry produces an explicit coverage gap and cannot receive specialized KPI PASS.
4. Industry and methodology plugins use separate interfaces and registries/manifests.
5. Core modules execute through a dependency-aware ResearchEngine rather than a single orchestration function owning all concrete sequencing logic.
6. PIT, missing semantics, lineage, completion, and snapshot rules remain core-owned.
7. Report/API surfaces consume the same canonical ResearchRunResult and CompletionResult.
8. v1.3 snapshots freeze every selected plugin/module fingerprint.
9. Existing Manufacturing and Distributor semantic regression tests remain green.
10. Historical v1.2.1 snapshots remain valid; no historical artifact is rewritten.
11. No company-specific branching exists in the architecture.
12. Full pytest and all v1.2.1 + v1.3 release gates pass.
13. Repository `main` contains the architecture/migration documentation needed for future plugin authors.

## 24. Design Principle to Preserve

The most important long-term constraint is:

> Research OS should become easier to extend as it becomes larger.

Adding the tenth industry plugin must be closer to adding the third plugin than to rewriting the research engine. Improving a methodology should replace or version a methodology plugin rather than requiring every industry pack to fork the change. Improving the core should preserve compatible plugin contracts whenever possible.

That property, rather than feature count, is the success criterion for the v1.3 architecture release.
