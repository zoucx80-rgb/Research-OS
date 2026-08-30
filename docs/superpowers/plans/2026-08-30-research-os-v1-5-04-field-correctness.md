# Research OS v1.5.04 Field-Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Research OS v1.5.04 as a conservative PATCH that fixes the correctness defects reproduced by the three-company field test.

**Architecture:** Add one shared delta-comparison helper, tighten existing Capital/Funding/Thesis/Valuation semantics, and extend the existing one-way professional presenter. Preserve the canonical runtime, completion, decision, router and snapshot boundaries.

**Tech Stack:** Python 3.12, Pydantic, pytest, existing Research OS runtime/plugin/release infrastructure.

**Spec:** `docs/superpowers/specs/2026-08-30-research-os-v1-5-04-field-correctness-design.md`

## Global Constraints

- Display version is `v1.5.04`; SemVer is `1.5.4`; `CORE_API_VERSION` remains `1.0`.
- Work directly on the existing `main`; create no additional branch.
- Use TDD: each production behavior begins with a regression test observed failing against v1.5.03.
- Do not add company-specific production logic or a second Router, Completion Gate, Decision Engine, risk engine, or presentation state.
- Missing/ambiguous facts remain missing; do not coerce them to zero.
- Preserve historical snapshots, release tags and all earlier Release Gate checks.

---

### Task 1: Freeze field-test regressions and release contract

**Files:**
- Create: `tests/regression/research_patterns/test_v1_5_04_field_correctness.py`
- Create: `tests/regression/architecture/test_release_contract_v1_5_04.py`
- Modify: `src/research_os/release/runtime.py`

**Interfaces:**
- Consumes: v1.5.03 public validators, engines, runtime and presenter.
- Produces: named Release Gate checks for every v1.5.04 acceptance behavior.

- [ ] **Step 1: Write failing behavior tests**

Add literal, hand-checked tests named for the break they catch:

```python
def test_reported_yoy_rounding_does_not_fail_financial_sanity(): ...
def test_negative_ocf_triggers_cash_thesis_falsifier_and_limits_lineage(): ...
def test_book_equity_change_is_not_external_financing_or_dilution(): ...
def test_incomparable_delta_bases_do_not_produce_incremental_ratios(): ...
def test_debt_funded_negative_ocf_distributor_cannot_route_pe_as_primary(): ...
def test_professional_view_projects_material_canonical_artifacts(): ...
```

The financial test uses the three literal field-test revenue pairs and reported growth values. The thesis test includes unrelated evidence and asserts it is absent from support. The comparison test uses explicit unequal basis strings. The valuation test uses uniformly high PE fitness plus a canonical severe Funding Loop. The presentation test builds a real runtime result and asserts projected values equal the canonical artifacts.

- [ ] **Step 2: Run the new behavior tests and verify RED**

Run:

```bash
pytest -q tests/regression/research_patterns/test_v1_5_04_field_correctness.py
```

Expected: all six behaviors fail for their named v1.5.03 defect, not from fixture/import errors.

- [ ] **Step 3: Write failing release-contract tests**

Define the exact v1.5.04 check-name to node-id mapping:

```python
V1_5_04_CHECKS = {
    "reported_yoy_rounding": "...::test_reported_yoy_rounding_does_not_fail_financial_sanity",
    "canonical_ocf_falsifier": "...::test_negative_ocf_triggers_cash_thesis_falsifier_and_limits_lineage",
    "explicit_equity_financing": "...::test_book_equity_change_is_not_external_financing_or_dilution",
    "delta_comparison_basis": "...::test_incomparable_delta_bases_do_not_produce_incremental_ratios",
    "funding_aware_pe_fitness": "...::test_debt_funded_negative_ocf_distributor_cannot_route_pe_as_primary",
    "material_artifact_projection": "...::test_professional_view_projects_material_canonical_artifacts",
}
```

Assert the runtime gate contains all names and the public version is `1.5.4` with Core API `1.0`.

- [ ] **Step 4: Run release-contract tests and verify RED**

Run:

```bash
pytest -q tests/regression/architecture/test_release_contract_v1_5_04.py
```

Expected: FAIL because v1.5.04 metadata and gate checks do not yet exist.

### Task 2: Correct rounded YoY and canonical thesis falsification

**Files:**
- Modify: `src/research_os/validation/financial.py`
- Modify: `src/research_os/thesis/service.py`
- Test: `tests/regression/research_patterns/test_v1_5_04_field_correctness.py`
- Test: `tests/unit/validation/test_financial_sanity.py`
- Test: `tests/unit/thesis/test_service.py`

**Interfaces:**
- Consumes: `FinancialSanityValidator.check_yoy`, `ThesisService.evaluate`, `evaluate_existing`.
- Produces: two-decimal-percentage-point tolerance and canonical OCF alias resolution.

- [ ] **Step 1: Add boundary unit tests and verify RED**

Add a literal value exactly inside `0.00005` tolerance and another outside it. Add an existing `cfo` falsifier evaluated against `ocf` evidence for backward compatibility. Run the targeted node IDs and confirm expected failures.

- [ ] **Step 2: Implement minimal rounded-YoY tolerance**

Change only the YoY comparison call to:

```python
return _result(expected, float(declared_growth), "YoY growth", rel_tol=1e-6, abs_tol=5e-5)
```

- [ ] **Step 3: Implement canonical OCF alias resolution**

Add a private lookup that treats `cfo`, `ocf`, and `operating_cash_flow` as aliases. Emit `ocf` in new falsifiers/verification metrics. Build financing-thesis support from evidence IDs on selected working-capital/financing driver nodes.

- [ ] **Step 4: Run targeted tests and verify GREEN**

Run:

```bash
pytest -q tests/unit/validation tests/unit/thesis tests/regression/research_patterns/test_v1_5_04_field_correctness.py -k "rounding or ocf or thesis"
```

Expected: selected tests PASS.

### Task 3: Enforce comparison basis and explicit equity financing

**Files:**
- Create: `src/research_os/period/comparison.py`
- Modify: `src/research_os/capital/engine.py`
- Modify: `src/research_os/kpi/distributor.py`
- Modify: `src/research_os/plugins/builtins.py`
- Modify: existing Capital/Distributor/runtime test fixtures that intentionally supply comparable delta facts
- Test: `tests/regression/research_patterns/test_v1_5_04_field_correctness.py`
- Test: `tests/unit/capital/test_engine.py`
- Test: `tests/unit/kpi/test_distributor_pack.py`

**Interfaces:**
- Produces: `comparable_ratio(facts, numerator, denominator) -> (value, reason_code)` and `common_comparison_basis(facts, names) -> reason_code | None`.
- Produces fact keys: `<fact>_comparison_basis`, `external_equity_financing`, `equity_dilution`.
- Produces additive result fields listed in the spec.

- [ ] **Step 1: Add matching/missing/mismatch helper tests and verify RED**

Use hand-derived literals: matching bases return `0.6`; missing bases return `COMPARISON_BASIS_REQUIRED`; unequal bases return `COMPARISON_BASIS_MISMATCH`.

- [ ] **Step 2: Implement the shared comparison helper**

Keep the helper industry-neutral. It must not inspect company or business-model identity.

- [ ] **Step 3: Apply the helper to Capital and Distributor ratios**

Suppress only affected ratios. Preserve `MetricResult(status="missing")` and expose the appropriate reason code. Advance `DistributorPack.pack_version` to `distributor@1.3.0`.

- [ ] **Step 4: Separate book equity, external financing and dilution**

Use `delta_equity` only for `reported_equity_change`; use `external_equity_financing` for funding state/ratio math; use `equity_dilution is True` for `EQUITY_DILUTION`. Advance the Distributor plugin manifest to `1.2.0`.

- [ ] **Step 5: Update legitimate legacy fixtures explicitly**

Where a test intends comparable delta math, add one identical literal comparison basis to each delta fact. Where a test intends known zero external equity financing, add `external_equity_financing=0.0`. Do not weaken any expected economic state.

- [ ] **Step 6: Run Capital, KPI, integration and v1.2.1/v1.5.03 regressions**

Run:

```bash
pytest -q tests/unit/capital tests/unit/kpi tests/integration/test_canonical_research_runtime.py tests/integration/test_runtime_safety_inputs.py tests/regression/research_patterns/test_v1_2_1_correctness_patterns.py tests/regression/research_patterns/test_v1_5_03_professional_integrity.py
```

Expected: PASS.

### Task 4: Add the funding-aware PE guard

**Files:**
- Modify: `src/research_os/valuation/router.py`
- Modify: `src/research_os/runtime/builtin_modules.py`
- Modify: `src/research_os/reporting/research_view.py`
- Test: `tests/unit/valuation/test_router.py`
- Test: `tests/regression/research_patterns/test_v1_5_04_field_correctness.py`

**Interfaces:**
- Consumes: canonical `capital.funding_loop` artifact.
- Produces: additive `ValuationContext.funding_state`, `funding_reason_codes`, and `RoutedModel.reason_codes`.

- [ ] **Step 1: Add direct router and runtime regression tests; verify RED**

The direct router test supplies `business_model="distributor"`, `funding_state="debt_funded"`, `NEGATIVE_OCF`, and high PE inputs. The runtime test confirms the module passes the existing artifact, not a caller-created parallel flag.

- [ ] **Step 2: Implement the minimal router overlay**

Apply `0.25` only to PE under the exact reusable condition and append `CASH_FUNDING_RISK_PE_PENALTY`.

- [ ] **Step 3: Wire the existing Funding Loop artifact into ValuationModule**

Add `capital.funding_loop` to its dependency set and pass state/reasons into `ValuationContext`. Do not add another risk classifier.

- [ ] **Step 4: Add a Chinese readable reason in the existing presenter**

Expose routed-model reason codes as localized semantic values; do not change routing in presentation.

- [ ] **Step 5: Run valuation/runtime/reporting tests and verify GREEN**

Run:

```bash
pytest -q tests/unit/valuation tests/unit/runtime tests/unit/reporting tests/regression/research_patterns/test_v1_5_04_field_correctness.py -k "valuation or pe or funding"
```

Expected: PASS.

### Task 5: Project material canonical artifacts

**Files:**
- Modify: `src/research_os/runtime/builtin_modules.py`
- Modify: `src/research_os/reporting/research_view.py`
- Modify: `src/research_os/runtime/factory.py`
- Test: `tests/unit/reporting/test_research_view.py`
- Test: `tests/regression/research_patterns/test_v1_5_04_field_correctness.py`

**Interfaces:**
- Consumes: `validation.financial`, `capital.efficiency`, `forecast.discipline`, `temporal.event`.
- Produces: additive human-readable financial-sanity, capital-efficiency, forecast-discipline and next-event fields.

- [ ] **Step 1: Add a real-result projection test and verify RED**

Build a canonical runtime result. Assert each new field copies the canonical status/value/event, and assert the financial status explanation says it is a process consistency check rather than an economic-health label.

- [ ] **Step 2: Make TemporalModule publish its canonical input**

Add `temporal.event` to `provides` and both result branches. Keep `NextVerificationEventValidator` authoritative.

- [ ] **Step 3: Add frozen human-readable projection models and mappings**

Add only presentation fields from the spec. Localize basis limitation and forecast reason. Use existing module-status semantics and do not calculate a new completion/economic state.

- [ ] **Step 4: Advance the presentation fingerprint**

Set `ResearchViewPresenter.version`, `HumanReadableResearchView.presentation_version`, runtime default `report_version`, and stock-research protocol fingerprint to `professional-research-view@1.2.0`.

- [ ] **Step 5: Run reporting, runtime and snapshot tests**

Run:

```bash
pytest -q tests/unit/reporting tests/unit/runtime tests/integration/runtime tests/integration/test_canonical_research_runtime.py tests/unit/snapshots
```

Expected: PASS.

### Task 6: Version, documentation and Release Gate

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `pyproject.toml`
- Modify: `research_os_version.json`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/prompts/stock_research.md`
- Create: `docs/migrations/v1.5.04.md`
- Modify: `src/research_os/release/runtime.py`
- Test: `tests/regression/architecture/test_release_contract_v1_5_04.py`

**Interfaces:**
- Produces: consistent v1.5.04 / 1.5.4 metadata and six named release checks.

- [ ] **Step 1: Register exact v1.5.04 pytest nodes**

Add the six check names from Task 1 to the existing release runtime without deleting or renaming historical checks.

- [ ] **Step 2: Update all public version surfaces**

Set SemVer to `1.5.4`, display text to `v1.5.04`, leave Core API `1.0`, and update component/report fingerprints required by changed behavior.

- [ ] **Step 3: Update human documentation**

Document corrected semantics, required comparison-basis/equity facts, no-database-migration status, compatibility, deferrals and the three-company evidence basis. Update the stock-research protocol so future runs require comparable delta bases and canonical OCF falsifiers.

- [ ] **Step 4: Run architecture/release-contract tests**

Run:

```bash
pytest -q tests/regression/architecture tests/unit/release
```

Expected: PASS.

### Task 7: Full verification and publish on main

**Files:**
- Verify all modified files; create no additional branch.

**Interfaces:**
- Consumes: complete v1.5.04 tree.
- Produces: one verified `main` release commit and exact-HEAD evidence.

- [ ] **Step 1: Run required targeted regression groups**

Run Architecture, Correctness, v1.5.01, v1.5.02, v1.5.03 and v1.5.04 groups explicitly. Expected: all PASS.

- [ ] **Step 2: Run migration smoke and full pytest**

Run the repository CI-equivalent commands with the virtual environment on `PATH`. Expected: zero failures.

- [ ] **Step 3: Run Release Gate**

Run:

```bash
python scripts/release_gate_v1_1.py
```

Expected final line: `READY: v1.5.4 stable`.

- [ ] **Step 4: Review diff, secrets and branch state**

Confirm only intended files changed, `main` is the only branch, no secret-like material exists, Core API remains `1.0`, and historical tags/snapshots are untouched.

- [ ] **Step 5: Commit and push directly to main**

Create a normal non-force commit and push `main`. If remote `main` moved, stop publication, fetch and reconcile instead of overwriting.

- [ ] **Step 6: Verify exact remote main HEAD and rerun the full gate**

Fetch remote `main`, verify local/remote SHA equality, ensure the worktree is at that exact SHA, rerun full pytest and Release Gate, and record the fresh output. Only then declare `Research OS v1.5.04 stable`.
