# Research OS v1.5.11 Semantic Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate generic semantic contradictions, unsafe comparison-basis conclusions, missingness conflation and investor-facing presentation integrity defects without introducing company-specific production logic.

**Architecture:** Add explicit comparison metadata and typed directional signals at the canonical thesis-analysis boundary, then make the active professional runtime consume the hardened semantics. Extend current decision/expectation states additively for missingness, project those semantics through versioned reporting classes, and enforce correctness with generic synthetic regressions plus field validation. Historical replay remains pinned where behavior must stay stable.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, existing Research OS module/runtime contracts, Markdown/HTML/Playwright PDF presentation pipeline.

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-5-11-semantic-correctness-design.md`

## Global Constraints

- Target Research OS version: `1.5.11`; Core API remains `1.0` unless a verified unavoidable public-contract break is found.
- No production code may branch on a company/security identifier or hard-code acceptance-company facts.
- Reporting/presentation never recomputes research semantics.
- Cross-metric growth comparisons fail closed unless comparison basis and economic type are compatible.
- No hidden universal thresholds are introduced solely from field examples.
- Historical v1.5.05–v1.5.10 replay remains green.
- Development stays on `v1.5.11-semantic-correctness`; final `main` receives exactly one squash release commit.

---

### Task 1: Typed Directional Signals and Comparison-Basis Safety

**Files:**
- Modify: `src/research_os/domain/evidence.py`
- Create: `src/research_os/thesis/semantic_signals.py`
- Create: `src/research_os/thesis/semantic_service_v1_5_11.py`
- Test: `tests/unit/thesis/test_semantic_signals_v1_5_11.py`

**Interfaces:**
- Consumes: PIT `Evidence` rows.
- Produces: `ComparisonBasis`, `MetricKind`, `DirectionalSignal`, `ComparisonAssessment`, `SemanticThesisService.assess_signals()`.

- [ ] **Step 1: Write failing tests** proving negative margin change renders downward semantics, positive margin change renders improvement semantics, stock-change vs flow-YoY is `NOT_COMPARABLE`, and explicitly compatible YoY comparisons may create a working-capital signal.
- [ ] **Step 2: Run** `pytest -q tests/unit/thesis/test_semantic_signals_v1_5_11.py` and verify RED due to missing new contracts.
- [ ] **Step 3: Add optional evidence metadata** `comparison_basis` and `metric_kind` to `Evidence`; defaults are `None` so historical evidence stays valid.
- [ ] **Step 4: Implement semantic signal contracts** with fail-closed comparability. Unknown metadata never permits a cross-metric directional conclusion.
- [ ] **Step 5: Implement `SemanticThesisService.assess_signals()`** using direction-derived labels; retain no company identities or field-fixture rules.
- [ ] **Step 6: Run Task 1 tests and legacy thesis tests**; expected GREEN.
- [ ] **Step 7: Commit feature-branch Task 1.**

### Task 2: Thesis Lifecycle and Directionally Correct Verification Conditions

**Files:**
- Modify: `src/research_os/thesis/models.py`
- Modify: `src/research_os/thesis/semantic_service_v1_5_11.py`
- Modify: `src/research_os/runtime/inputs.py`
- Modify: `src/research_os/runtime/professional_modules.py`
- Test: `tests/unit/thesis/test_lifecycle_semantics_v1_5_11.py`
- Test: `tests/integration/runtime/test_semantic_thesis_runtime_v1_5_11.py`

**Interfaces:**
- Consumes: typed signal assessment plus optional explicit `prior_theses` input.
- Produces: unresolved/waiting-confirmation thesis semantics with `resolution_conditions`, `conviction_up_conditions`, `deterioration_conditions`; weakening only from explicit prior directional thesis.

- [ ] **Step 1: Write failing lifecycle tests** for mixed-without-prior => unresolved, explicit prior directional thesis => weakening when contradicted, and unresolved thesis => no falsifier-backed thesis-broken condition.
- [ ] **Step 2: Run targeted tests and verify RED.**
- [ ] **Step 3: Extend `Thesis` additively** with `unresolved` status and structured verification-condition lists; unresolved does not require falsifiers.
- [ ] **Step 4: Add `prior_theses` to `ResearchInputs`** as an explicit analyst/runtime input; absence means no prior directional thesis exists.
- [ ] **Step 5: Implement current professional lifecycle** in `SemanticThesisService.evaluate()` and inject it through `ProfessionalDriverThesisModule`; bump current module version without altering legacy `ThesisService` behavior.
- [ ] **Step 6: Update active DecisionModule mapping only as necessary** so unresolved is not coerced to ACTIVE.
- [ ] **Step 7: Run thesis/runtime/history-focused tests and make GREEN.**
- [ ] **Step 8: Commit feature-branch Task 2.**

### Task 3: Expectation Missingness and Decision Fail-Safe Semantics

**Files:**
- Modify: `src/research_os/decision/models.py`
- Modify: `src/research_os/decision/engine.py`
- Modify: `src/research_os/runtime/inputs.py`
- Modify: `src/research_os/runtime/professional_modules.py`
- Modify: `src/research_os/reporting/semantics.py`
- Test: `tests/unit/decision/test_missing_expectation_v1_5_11.py`
- Test: `tests/integration/runtime/test_expectation_missingness_v1_5_11.py`

**Interfaces:**
- Consumes: explicit expectation state input and expectation runtime evidence status.
- Produces: active `ExpectationState` with `UNKNOWN`; Decision Engine treats it as missing information, not a negative signal.

- [ ] **Step 1: Write failing tests**: no PIT expectation evidence => UNKNOWN; explicit provenance-aware MIXED remains MIXED; UNKNOWN cannot by itself trigger directional risk logic.
- [ ] **Step 2: Run tests and verify RED.**
- [ ] **Step 3: Extend active expectation literal and semantic labels** with `UNKNOWN` / `市场预期证据不足`.
- [ ] **Step 4: Change active default expectation state to UNKNOWN** while preserving explicit legacy/analyst MIXED input.
- [ ] **Step 5: Make ProfessionalDecisionModule resolve missing expectation evidence fail-safe** and update state provenance without fabricating a conclusion.
- [ ] **Step 6: Run decision/expectation/runtime tests plus historical replay gates; isolate historical imports/builders if required rather than weakening the active contract.**
- [ ] **Step 7: Commit feature-branch Task 3.**

### Task 4: Presentation Integrity and Confidence Labeling

**Files:**
- Create: `src/research_os/reporting/research_view_v1_5_11.py`
- Create: `src/research_os/reporting/markdown_renderer_v1_5_11.py`
- Modify: `src/research_os/reporting/__init__.py`
- Modify: `src/research_os/presentation/html_renderer.py` only if a new static section label/id is required
- Test: `tests/unit/reporting/test_semantic_integrity_v1_5_11.py`
- Test: `tests/regression/research_patterns/test_v1_5_11_semantic_output_patterns.py`

**Interfaces:**
- Consumes: current canonical `ResearchRunResult` / v1.5.10 human-readable view.
- Produces: Presenter `professional-research-view@1.6.0` and Markdown renderer version bump with display-only hardening.

- [ ] **Step 1: Write failing reporting tests** for no literal `None`, OCF alias deduplication, human date formatting, explicit comparison-basis labels, evidence-quality wording, and categorical valuation fitness in body.
- [ ] **Step 2: Run tests and verify RED.**
- [ ] **Step 3: Implement additive Presenter v1.5.11 projection**; do not recompute state or confidence.
- [ ] **Step 4: Implement additive Markdown renderer** that converts null display cells to `—`/empty safe text, deduplicates semantically equivalent canonical fact aliases, and shows categorical valuation suitability while preserving precise score in audit metadata.
- [ ] **Step 5: Keep audit exact timestamps and scores; format investor-facing decision date only in body.**
- [ ] **Step 6: Run reporting/presentation and historical renderer replay suites; isolate historical renderer imports where needed.**
- [ ] **Step 7: Commit feature-branch Task 4.**

### Task 5: Generic Semantic Correctness Gate and Active Field Validation

**Files:**
- Create: `tests/regression/architecture/test_semantic_correctness_contract_v1_5_11.py`
- Create: `tests/regression/research_patterns/test_v1_5_11_semantic_correctness.py`
- Create: `tests/fixtures/field_acceptance/v1_5_11/manufacturing_semantic_correctness.json`
- Create: `scripts/render_field_acceptance_v1_5_11.py`
- Create/Modify: integration field-acceptance tests for v1.5.11
- Modify: `scripts/release_gate_v1_1.py`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: active v1.5.11 runtime and reporting pipeline.
- Produces: fail-closed generic semantic correctness gate plus one manufacturing field-validation artifact.

- [ ] **Step 1: Write release-pattern RED tests** enforcing all 13 correctness cases in the spec and scanning production source for acceptance-company identity branches.
- [ ] **Step 2: Add a generic synthetic manufacturing fixture** with explicit comparison metadata and no real-company identity.
- [ ] **Step 3: Add v1.5.11 field runner** that validates machine semantics plus rendered Markdown/HTML/PDF, not keyword presence alone.
- [ ] **Step 4: Register correctness tests and field render in CI/Release Gate.**
- [ ] **Step 5: Run targeted correctness/field suites to GREEN.**
- [ ] **Step 6: Re-run a real manufacturing field fixture as validation evidence; company-specific facts stay test data only.**
- [ ] **Step 7: Commit feature-branch Task 5.**

### Task 6: Release v1.5.11 and One-Commit Main Integration

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `pyproject.toml`
- Modify: `research_os_version.json`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/prompts/stock_research.md`
- Create: `docs/migrations/v1.5.11.md`
- Create: `tests/regression/architecture/test_release_contract_v1_5_11.py`

**Interfaces:**
- Produces: stable `Research OS 1.5.11` release contract and one-commit main history.

- [ ] **Step 1: Write release-contract RED** for version consistency, active fingerprints, semantic correctness gates, CI field artifact, historical replay, no DB migration, and no company-specific production logic.
- [ ] **Step 2: Run contract and verify RED only on unreleased surfaces.**
- [ ] **Step 3: Update versions, metadata, migration notes, README, CHANGELOG and canonical stock-research protocol.**
- [ ] **Step 4: Run full feature-branch CI** including `pytest -q`, PDF integration, historical field replay, v1.5.11 field validation and Release Gate; require exact GREEN.
- [ ] **Step 5: Verify final branch diff against v1.5.10** is scoped to semantic correctness and release surfaces.
- [ ] **Step 6: Create a squash commit from the verified final tree with parent `05a3ba99edc02ac93ee9fdf1130485da7e6fa8ab` and message `release: semantic correctness and comparison-basis safety v1.5.11`.**
- [ ] **Step 7: Fast-forward `main` once to the squash commit.**
- [ ] **Step 8: Run fresh exact-HEAD main CI and require all checks GREEN.**
- [ ] **Step 9: Verify compare `v1.5.10 main -> v1.5.11 main` reports `ahead_by=1`, `behind_by=0`, `total_commits=1`.**
