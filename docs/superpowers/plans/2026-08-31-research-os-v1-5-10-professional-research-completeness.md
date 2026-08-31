# Research OS v1.5.10 Professional Research Completeness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add typed, PIT-safe research-completeness and continuous-validation artifacts that make professional reports more decision-useful without turning Reporting into a second research engine.

**Architecture:** Extend `ResearchInputs` and professional runtime modules with additive canonical artifacts. Project those artifacts through an additive v1.5.10 Presenter/Composer/Renderer layer and harden field acceptance. External retrieval stays outside Core; missing data remains missing.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, existing Research OS runtime/reporting/presentation pipeline, GitHub Actions/Playwright PDF regression.

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-5-10-professional-research-completeness-design.md`

## Global Constraints

- Baseline parent for final release commit: `a3e82b3cc80b871b559ac9f5cd29e18e97b8e98d`.
- Development branch: `v1.5.10-professional-research-completeness`.
- Final `main` must receive exactly one squashed v1.5.10 commit.
- Core API remains `1.0`.
- No time travel, no fabricated data, preserve evidence/assumption lineage.
- No company-specific production rules or universal thresholds from review examples.
- Reporting/Presentation never retrieve data or calculate new investment states.
- No DB migration expected; no Hospitality Plugin; chart rendering deferred.

---

### Task 1: Typed Completeness Contracts

**Files:**
- Create: `src/research_os/completeness/models.py`
- Create: `src/research_os/completeness/services.py`
- Create: `src/research_os/completeness/__init__.py`
- Modify: `src/research_os/runtime/inputs.py`
- Test: `tests/unit/completeness/test_models_and_services.py`

**Interfaces:**
- Produces immutable types: `OperatingObservation`, `FinancialSeriesPoint`, `FinancialTimeSeries`, `CashFlowQualityInput`, `CashFlowQualityBridge`, `ConsensusObservation`, `ConsensusDistribution`, `PeerComparableObservation`, `SensitivityCase`, `MonitoringRule`, `VerificationCalendarEvent`, `PriorRunReviewInput`, `PriorRunReview`.
- Produces services: `build_cash_flow_quality_bridge`, `build_consensus_distribution`, `build_prior_run_review`.

- [ ] **Step 1: Write RED tests** covering frozen models, missing-value preservation, PIT rejection for consensus observations, single-source consensus not marked broad, cash bridge arithmetic only with complete inputs, prior-run unknown when prediction/actual is absent, and monitoring thresholds retained as input data.
- [ ] **Step 2: Run** `pytest -q tests/unit/completeness/test_models_and_services.py`; expected failure because `research_os.completeness` does not exist.
- [ ] **Step 3: Implement minimal contracts/services**. `build_cash_flow_quality_bridge` may compute `simplified_fcf = ocf - capex_cash` only when both exist and must label `simplified_fcf_not_fcff`; working-capital contribution remains `None` unless supplied. `build_consensus_distribution` filters/rejects `publish_ts > decision_ts`, computes low/median/high only from supplied numeric values and sets `breadth="single_source"` when source count <2. `build_prior_run_review` returns `UNKNOWN` without both prediction and actual.
- [ ] **Step 4: Re-run targeted tests**; expected PASS.

### Task 2: Professional Runtime Completeness Module

**Files:**
- Create: `src/research_os/runtime/research_completeness.py`
- Modify: `src/research_os/runtime/professional_modules.py`
- Modify: `src/research_os/runtime/inputs.py`
- Test: `tests/unit/runtime/test_research_completeness_v1_5_10.py`

**Interfaces:**
- Produces canonical artifacts: `research.operating_evidence`, `financial.time_series`, `cash_flow.quality_bridge`, `expectation.consensus_distribution`, `peers.comparables`, `scenario.sensitivities`, `monitoring.rules`, `monitoring.verification_calendar`, `monitoring.prior_run_review`, `methodology.disclosure`.

- [ ] **Step 1: Write RED test** constructing explicit inputs and asserting exact artifact identities plus lineage-safe/missing-safe behavior; also assert no artifact appears merely because a field is absent.
- [ ] **Step 2: Run** targeted test; expected missing module/artifacts.
- [ ] **Step 3: Add optional tuple fields to `ResearchInputs`** for the typed inputs, defaulting empty. Implement `ResearchCompletenessModule` using only these inputs plus `decision_ts`; insert it in `build_professional_builtin_modules` after the financial snapshot and before driver/thesis. Methodology disclosure is static repository-contract text only, with no invented weights/thresholds.
- [ ] **Step 4: Re-run runtime/completeness tests**; expected PASS.

### Task 3: Presenter / Document / Markdown Projection

**Files:**
- Create: `src/research_os/reporting/research_view_v1_5_10.py`
- Create: `src/research_os/reporting/composer_v1_5_10.py`
- Create: `src/research_os/reporting/markdown_renderer_v1_5_10.py`
- Modify: `src/research_os/reporting/document.py`
- Modify: `src/research_os/reporting/__init__.py`
- Test: `tests/unit/reporting/test_research_completeness_v1_5_10.py`

**Interfaces:**
- Current Presenter version becomes `professional-research-view@1.5.0`.
- Current Composer version becomes `research-report-composer@1.3.0`.
- Current Markdown Renderer version becomes `professional-markdown-renderer@1.2.0`.
- New document blocks: `ResearchCompletenessBlock` with a stable `kind` and display-only payload.

- [ ] **Step 1: RED tests** assert canonical artifacts become sections for trend, operating evidence, cash quality, peers, consensus dispersion, sensitivity, monitoring/calendar, prior-run review and methodology; absent artifacts omit sections; raw evidence/assumption ids remain out of body; simplified FCF visibly says it is not FCFF.
- [ ] **Step 2: Run targeted reporting test**; expected missing v1.5.10 projection.
- [ ] **Step 3: Implement additive wrappers** over v1.5.09 classes. Presenter copies only canonical artifact data into human-readable structures. Composer orders completeness sections after core financial/causal content and before gaps/appendix. Renderer formats deterministic Chinese headings/tables and does not calculate values.
- [ ] **Step 4: Run reporting tests including v1.5.09**; expected PASS with historical modules imported explicitly where version fingerprints are historical.

### Task 4: Completeness Gate & Manufacturing Acceptance

**Files:**
- Create: `tests/fixtures/field_acceptance/v1_5_10/manufacturing_completeness.json`
- Create: `tests/regression/research_patterns/test_v1_5_10_research_completeness.py`
- Modify: `scripts/render_field_acceptance_v1_5_09.py` only if common reusable evaluator can be safely extended; otherwise create `scripts/render_field_acceptance_v1_5_10.py`.
- Test: `tests/integration/presentation/test_field_acceptance_v1_5_10.py`

**Interfaces:**
- Manifest includes dimension coverage values `PASS|INCOMPLETE|NOT_APPLICABLE` for time series, operating evidence, cash flow, consensus, peers, sensitivity, monitoring/events, prior-run validation and methodology.

- [ ] **Step 1: RED tests** assert required missing dimensions fail closed and explicitly not-applicable dimensions do not fail. Fixture must use generic manufacturing-archetype data, not real company names.
- [ ] **Step 2: Run** targeted integration/regression tests; expected missing evaluator/fixture behavior.
- [ ] **Step 3: Implement evaluator** over already-rendered/canonical artifacts; never invent evidence. Add manufacturing fixture covering product-margin divergence, capacity/order gap or evidence, subsidiary divergence, multi-period series, cash bridge, peer rows, multi-source consensus, explicit sensitivity assumptions, configurable rules/events and prior-run review.
- [ ] **Step 4: Run v1.5.10 acceptance plus v1.5.09 field acceptance**; expected PASS.

### Task 5: Release Contract and Documentation

**Files:**
- Create: `tests/regression/architecture/test_release_contract_v1_5_10.py`
- Create: `docs/migrations/v1.5.10.md`
- Modify: `src/research_os/version.py`
- Modify: `pyproject.toml`
- Modify: `research_os_version.json`
- Modify: `src/research_os/release/runtime.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/prompts/stock_research.md`

**Interfaces:**
- Research OS `1.5.10`, Core API `1.0`.
- Module metadata registers `research_completeness=1.0.0`; presenter/composer/markdown versions match Task 3.

- [ ] **Step 1: Add release RED contract** requiring versions, module fingerprints, migration docs, CI v1.5.10 tests/acceptance, Release Gate registration, no new Alembic migration and no company-specific production constants.
- [ ] **Step 2: Run architecture contract**; expected failure on version/docs/gate/CI.
- [ ] **Step 3: Update release files/docs** and register v1.5.10 test nodes in Release Gate and CI. Historical contracts become forward-compatible where they incorrectly bind current top-level component versions, without weakening historical capability assertions.
- [ ] **Step 4: Run architecture tests and dedicated v1.5.10 suites**; expected PASS.

### Task 6: Full Verification and One-Commit Main Integration

**Files:** no semantic changes expected.

- [ ] **Step 1: Run branch CI** including full pytest, v1.5.09 replay, v1.5.10 field acceptance and Release Gate.
- [ ] **Step 2: Inspect failures and repair on the feature branch until exact branch HEAD is green.** Any repair that changes behavior requires RED/GREEN coverage.
- [ ] **Step 3: Compare baseline `a3e82b3...` to final branch tree** and verify no unrelated files/secrets/company-specific production facts were introduced.
- [ ] **Step 4: Create one squashed commit** whose parent is exactly the current `main` baseline and whose tree is the verified branch tree; message `release: professional research completeness v1.5.10`.
- [ ] **Step 5: Fast-forward `main` to that one commit.** Do not merge the intermediate branch commit history.
- [ ] **Step 6: Run fresh CI on the squashed main SHA.** Only this result can establish stable release evidence.
- [ ] **Step 7: Verify remote `main` still equals the tested SHA and compare `a3e82b3...main` to prove exactly one new commit represents v1.5.10.

## Self-Review

Spec coverage: all accepted audit areas map to Tasks 1–4; external experts/tenders/patents remain evidence-provider inputs rather than fabricated Core capability; chart rendering remains deferred while typed datasets are delivered. No placeholders. Type names are consistent across tasks. Historical one-way/PIT/lineage boundaries remain explicit.
