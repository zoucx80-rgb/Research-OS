# Research OS v1.4 Canonical Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace compatibility-driven orchestration with one extensible canonical ResearchRuntime while preserving research correctness and safety invariants.

**Architecture:** `ResearchContext + ResearchInputs` feed a run-scoped module graph built by `ResearchRuntimeFactory`; `ResearchEngine` executes only declarative module contracts; `ResearchCompletionGate` finalizes status; `SnapshotService` freezes fingerprints; `ResearchRunResult` is the only public result. Industry and methodology plugins remain orthogonal and may be added without editing `ResearchEngine`.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-30-research-os-v1-4-greenfield-runtime-amendment.md`

## Global Constraints

- Target public release: `1.4.0`.
- `CORE_API_VERSION = "1.0"`.
- `ResearchEngine` must contain no company, industry, or plugin IDs.
- No import-time global plugin registry mutation.
- No company-specific production logic or real-company golden fixtures.
- Missing remains missing; PIT and lineage remain core-owned.
- `ResearchCompletionGate` is the only COMPLETE/INCOMPLETE authority.
- Historical tags and frozen snapshots are never rewritten.
- Compatibility-only facade code may be deleted or rewritten.

---

### Task 1: Introduce canonical ResearchInputs and remove legacy-request dependencies

**Files:**
- Create: `src/research_os/runtime/inputs.py`
- Modify: `src/research_os/runtime/builtin_modules.py`
- Modify: `src/research_os/runtime/__init__.py`
- Test: `tests/unit/runtime/test_inputs.py`
- Test: `tests/unit/runtime/test_builtin_modules_inputs.py`

**Interfaces:**
- Produces: `ResearchInputs` immutable Pydantic model.
- Changes module construction to accept `inputs: ResearchInputs` rather than `legacy_request`.

- [ ] Write RED tests asserting `ResearchInputs` is frozen, has safe defaults, and modules no longer expose a `legacy_request` constructor parameter.
- [ ] Verify RED with targeted pytest.
- [ ] Implement `ResearchInputs` using current domain types for preflight, financial observations, expectation evidence/vintage, valuation inputs/execution, analyst states, temporal event, claims and version metadata.
- [ ] Replace `_safety(legacy_request)` and `getattr` access in built-in modules with typed `self.inputs` fields.
- [ ] Keep run-scoped services isolated; no module may mutate shared factory/global state.
- [ ] Run runtime unit tests and current safety regressions.
- [ ] Commit: `refactor: replace legacy request with runtime inputs`.

---

### Task 2: Build canonical ResearchRuntime and extensible factory

**Files:**
- Create: `src/research_os/runtime/factory.py`
- Modify: `src/research_os/runtime/result.py`
- Modify: `src/research_os/runtime/__init__.py`
- Test: `tests/unit/runtime/test_factory.py`
- Test: `tests/integration/runtime/test_canonical_runtime.py`
- Test: `tests/regression/architecture/test_extensibility.py`

**Interfaces:**
- Produces: `ResearchRuntime`, `ResearchRuntimeFactory.default()`, `ResearchRuntime.run_context(context, inputs) -> ResearchRunResult`.

- [ ] Write RED factory/runtime tests.
- [ ] Add a synthetic third-party industry plugin test proving registry/resolver/runtime execution works without modifying `ResearchEngine`.
- [ ] Implement default factory with explicit trusted built-in registration and no import-time mutation.
- [ ] Build run-scoped module graph from registry/resolver dependencies.
- [ ] Execute `ResearchEngine`, centralize module-result -> completion-name mapping, call `ResearchCompletionGate`, build component fingerprints, freeze snapshot, return `ResearchRunResult`.
- [ ] Make repeated same-input runs deterministic except snapshot UUID; payload hash and component fingerprint set must match.
- [ ] Run targeted and full architecture tests.
- [ ] Commit: `feat: add canonical extensible research runtime`.

---

### Task 3: Remove duplicate legacy orchestration policy

**Files:**
- Delete or rewrite: `src/research_os/orchestration.py`
- Modify callers under `src/research_os/api/` if any.
- Remove compatibility-only `KpiPackRegistry` facade if no canonical code requires it.
- Rewrite tests that depend on old facade against `ResearchRuntime`.

**Interfaces:**
- Public research execution is canonical runtime only.

- [ ] Search repository for `ResearchOS`, `ResearchRunRequest`, `ResearchRun`, `KpiPackRegistry`, and `legacy_request` references.
- [ ] Write RED architecture test asserting no policy-owning legacy orchestration remains.
- [ ] Migrate required callers/tests to `ResearchContext + ResearchInputs`.
- [ ] Delete obsolete facade/adapter code when no longer referenced.
- [ ] Preserve semantic regressions for manufacturing/distributor KPI, PIT, financial sanity, expectation/valuation safety, decision and completion.
- [ ] Run full suite.
- [ ] Commit: `refactor: remove duplicate legacy orchestration`.

---

### Task 4: Make reporting consume canonical result only

**Files:**
- Modify: `src/research_os/reporting/summary.py`
- Test: `tests/unit/reporting/test_canonical_result.py`

**Interfaces:**
- Reporting consumes `ResearchRunResult` and `ResearchRunResult.completion`.

- [ ] Write RED test proving report builder cannot independently promote INCOMPLETE to COMPLETE.
- [ ] Add canonical `build_from_result()` path and remove duplicated completion policy inputs where obsolete.
- [ ] Run reporting/completion tests.
- [ ] Commit: `refactor: report from canonical runtime result`.

---

### Task 5: Version v1.4 and add extensibility release gates

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `pyproject.toml`
- Modify: `research_os_version.json`
- Modify: `src/research_os/__init__.py`
- Modify: `scripts/release_gate_v1_1.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/prompts/stock_research.md`
- Create: `docs/architecture/plugin-authoring-v1.md`
- Create: `docs/migrations/v1.4.0.md`
- Test: `tests/regression/architecture/test_release_contract_v1_4.py`

**Interfaces:**
- Produces stable v1.4 release contract.

- [ ] Write RED release-contract tests for all v1.4 architecture gates and CI order.
- [ ] Set all public package/runtime/report version surfaces to `1.4.0`; keep Core API `1.0`.
- [ ] Add gates: research_context_contract, research_inputs_contract, module_contract, pipeline_dependency_resolution, plugin_manifest_contract, plugin_compatibility_resolution, industry_auto_resolution, methodology_auto_resolution, unsupported_coverage_gap, plugin_failure_isolation, canonical_runtime_entrypoint, canonical_result_contract, knowledge_interface_pit, snapshot_component_fingerprints, completion_single_source_v1_4, core_api_version_consistency, extensibility_no_engine_change, no_legacy_runtime_policy_duplication.
- [ ] CI order: architecture targeted -> correctness targeted -> migration/storage smoke -> full pytest -> release gate.
- [ ] Document plugin authoring including stable/experimental maturity, capability declarations, registration, resolution, contract tests, forbidden repository mutation, and future catalog/provider extension point.
- [ ] Update stock prompt: normal users provide company/security; plugins resolve automatically; gaps never silently become COMPLETE.
- [ ] Commit: `release: prepare Research OS v1.4 architecture gate`.

---

### Task 6: Full verification and architecture acceptance

**Files:** Verification-only except proven fixes.

- [ ] Run architecture-targeted tests: runtime, plugins, knowledge, integration/runtime, regression/architecture.
- [ ] Run v1.2.1 correctness regression set protecting period/missing/funding/completion semantics.
- [ ] Run storage migration smoke.
- [ ] Run full `pytest -q` with zero failures.
- [ ] Run Release Gate; final line must be `READY: v1.4.0 stable`.
- [ ] Run anonymous acceptance patterns: manufacturing auto-resolves; distributor auto-resolves; unsupported consumer/hotel yields coverage gap and INCOMPLETE; synthetic third-party plugin resolves without editing engine.
- [ ] Verify repeated synthetic run component fingerprints and deterministic payload hash.
- [ ] Inspect diff and secret hygiene.
- [ ] Commit only proven verification fixes.
- [ ] Re-read remote `main` and confirm verified HEAD.

## Self-Review

- Spec coverage: canonical runtime, typed inputs, dual plugins, declarative graph, completion ownership, fingerprints, safe extension, deletion of legacy duplication, extensibility acceptance and documentation are all assigned to tasks.
- Placeholder scan: no TBD/TODO implementation steps.
- Type consistency: `ResearchContext`, `ResearchInputs`, `ResearchRuntime`, `ResearchRunResult`, `PluginRegistry`, `StrategyResolver`, `ResearchCompletionGate`, `CORE_API_VERSION` are used consistently.
