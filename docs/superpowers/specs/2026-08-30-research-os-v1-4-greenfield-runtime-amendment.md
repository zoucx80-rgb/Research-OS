# Research OS v1.4 Greenfield Runtime Amendment

**Status:** Approved by explicit project-owner direction on 2026-08-30

**Target release:** `1.4.0`

**Baseline:** `zoucx80-rgb/Research-OS@d42bb243cc22b61a0ea01acd04d39459b018de55`

**Amends:** `docs/superpowers/specs/2026-08-29-research-os-v1-3-architecture-foundation-design.md`

## 1. Decision

Research OS is still a new project. The v1.4 architecture must optimize for long-term correctness, extensibility, professional research quality, and clear module ownership. Backward compatibility with the pre-runtime monolithic API is not a product requirement. Code that exists only to preserve an obsolete interface may be deleted or rewritten once its research semantics are protected by canonical tests.

The project owner explicitly chooses `1.4.0` for this architecture release. For this pre-production project, the 1.x line is being used as an architecture-building series even where internal interfaces are replaced. No historical release tags or frozen research snapshots may be rewritten.

## 2. Architecture objective

The success criterion is not merely that current manufacturing and distributor cases run. The architecture must become easier to extend as it grows.

A future industry or methodology plugin must be addable without modifying `ResearchEngine`, completion policy, PIT/lineage logic, or unrelated plugins.

The stable dependency direction is:

```text
User/API
  -> ResearchContext + ResearchInputs
  -> ResearchRuntime
       -> Core modules
       -> BusinessModelRouter
       -> PluginRegistry
       -> StrategyResolver
       -> resolved Industry / Methodology modules
       -> ResearchEngine
       -> ResearchCompletionGate
       -> SnapshotService
  -> ResearchRunResult
  -> Report/API/Monitoring consumers
```

## 3. Extensibility invariants

### 3.1 Stable Core API

`CORE_API_VERSION = "1.0"` remains independent from the Research OS package version. Plugins depend on the Core API contract, not internal implementation files.

### 3.2 Declarative capability graph

Every runtime module declares stable `requires` and `provides` capabilities through `ModuleSpec`. `ResearchEngine` knows only the generic module contract and dependency graph. It must never contain industry IDs, company IDs, or plugin-specific branches.

### 3.3 Explicit composition, no import-time mutation

`ResearchRuntimeFactory.default()` explicitly registers trusted built-ins. Importing a module must not mutate a global registry. A future entry-point/catalog provider can be added behind a provider interface without changing the engine.

### 3.4 Industry and methodology remain orthogonal

Industry plugins answer **what must be examined**. Methodology plugins answer **how a reusable analytical question is evaluated**. Neither family may impersonate the other to gain priority or bypass capability checks.

### 3.5 Coverage gaps are first-class

Unsupported business models or capabilities emit `CoverageGap`. Core infrastructure must never turn missing specialized coverage into PASS. Future assisted extension consumes `ExtensionRequest`; it may not mutate the production registry during the discovering run.

### 3.6 Runtime result is the only public research truth

`ResearchRunResult` is the single result contract for reports, snapshots, API surfaces, and future monitoring. No second legacy run object may own or recompute policy.

## 4. Compatibility requirements removed

The following v1.3 requirements are cancelled:

- preserving `ResearchOS.complete_run(ResearchRunRequest)` as the primary public execution path;
- maintaining a legacy `ResearchRun` output facade;
- permanent `LegacyRunAdapter` architecture;
- keeping `KpiPackRegistry` solely as an external compatibility facade;
- release gates whose purpose is old-request API compatibility.

Validated domain algorithms may remain. Compatibility-only glue should be deleted when canonical v1.4 tests cover the semantics.

## 5. Canonical runtime inputs

`ResearchContext` contains immutable run identity, company identity, decision timestamp, baseline, PIT evidence/fact views, knowledge view, and options.

A focused `ResearchInputs` model carries run-specific non-fact inputs required by analytical modules:

```python
class ResearchInputs(BaseModel):
    preflight: RepositoryPreflightEvidence | None = None
    financial_unit: str = "元"
    financial_observations: list[FinancialMetricObservation] = []
    expectation_vintage: ConsensusVintage | None = None
    expectation_evidence: ExpectationEvidence | None = None
    expectation_conclusion: str | None = None
    valuation_models: dict[str, ModelFitnessInputs] = {}
    valuation_execution: ValuationExecution | None = None
    fundamental_state: str = "UNCERTAIN"
    valuation_state: str = "UNRELIABLE"
    expectation_state: str = "MIXED"
    next_verification_event: NextVerificationEvent | None = None
    claimed_conclusions: list[str] = []
    versions: dict[str, str] = {}
```

`ResearchInputs` is immutable per run and injected into runtime modules. Modules must not reach back into an old monolithic request object.

## 6. Canonical runtime

Public execution:

```python
runtime = ResearchRuntimeFactory.default()
result = runtime.run_context(context, inputs)
```

Execution is:

```text
validate context/input contracts
 -> construct run-scoped module graph
 -> ResearchEngine.run(context)
 -> map module results to canonical completion statuses
 -> ResearchCompletionGate.evaluate(...)
 -> freeze component fingerprints and strategy resolution
 -> SnapshotService.freeze(...)
 -> ResearchRunResult
```

The factory may build fresh run-scoped module instances so stateful services such as expectation/ledger stores cannot leak across unrelated runs.

## 7. Completion mapping

The completion gate remains the sole completion authority. Runtime module IDs map centrally to the existing completion capability names; reporting must consume `ResearchRunResult.completion` directly.

Unsupported primary industry behavior is mandatory:

```text
strategy_resolution.coverage_gaps != []
Industry KPI module = INSUFFICIENT_EVIDENCE
KPI Pack = INSUFFICIENT_EVIDENCE
completion.final_status = INCOMPLETE
```

## 8. Deletion/rewrite policy

Old code may be removed or rewritten when:

1. canonical runtime owns the behavior;
2. domain correctness is protected by tests;
3. no PIT, lineage, missingness, completion, decision or valuation safety rule is weakened;
4. historical release tags and snapshots remain untouched.

Prefer one clear implementation over parallel legacy and canonical orchestration.

## 9. Regression policy

Dropping API compatibility does not drop research correctness. Keep or rewrite regression tests that protect:

- period-aware KPI calculations;
- missing-value semantics and known-zero distinction;
- Funding Loop truthfulness;
- Manufacturing and Distributor KPI formula outputs;
- PIT and evidence lineage;
- expectation and valuation safety gates;
- legal decision states;
- completion single-source behavior;
- snapshot reproducibility and component fingerprints.

All new architecture fixtures remain anonymous/synthetic. No company-specific production logic or golden company numbers may be added.

## 10. v1.4 release gates

The release gate must include at least:

```text
research_context_contract
research_inputs_contract
module_contract
pipeline_dependency_resolution
plugin_manifest_contract
plugin_compatibility_resolution
industry_auto_resolution
methodology_auto_resolution
unsupported_coverage_gap
plugin_failure_isolation
canonical_runtime_entrypoint
canonical_result_contract
knowledge_interface_pit
snapshot_component_fingerprints
completion_single_source_v1_4
core_api_version_consistency
extensibility_no_engine_change
no_legacy_runtime_policy_duplication
```

Final legal line:

```text
READY: v1.4.0 stable
```

## 11. Acceptance criteria

v1.4.0 is complete only when:

1. `ResearchRuntime.run_context()` is the canonical execution entry point and returns `ResearchRunResult`.
2. Runtime modules consume `ResearchInputs`, not a legacy request object.
3. `ResearchEngine` contains no industry/plugin/company-specific logic.
4. Manufacturing and Distributor are auto-resolved through stable industry plugins and preserve validated KPI semantics.
5. An unsupported synthetic consumer/hotel profile produces a visible coverage gap and blocks false COMPLETE.
6. A synthetic third-party plugin can be registered/resolved/executed without modifying `ResearchEngine`.
7. Methodology plugins can be added independently of industry plugins through capability declarations.
8. Completion and reporting consume one authoritative completion result.
9. Snapshots freeze core/module/plugin fingerprints and preserve payload reproducibility.
10. Full correctness, architecture, migration/storage and Release Gate suites pass.
11. Public version surfaces are `1.4.0`; `CORE_API_VERSION` remains `1.0`.
12. Documentation explains plugin authoring, extension boundaries, and the rule that research runs never self-modify production code.
