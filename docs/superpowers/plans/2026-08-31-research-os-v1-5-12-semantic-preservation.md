# Research OS v1.5.12 Semantic Preservation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve material research qualifiers through the reporting pipeline and add canonical, basis-aware valuation reconciliation.

**Architecture:** Add stable semantic and valuation domain services, then expose their typed artifacts through the active runtime. Versioned presentation classes consume those artifacts without recomputation; historical replay adapters stay pinned.

**Tech Stack:** Python 3.12, Pydantic 2, pytest 9, existing Research OS runtime/presentation/release registries.

**Spec:** `docs/superpowers/specs/2026-08-31-research-os-v1-5-12-semantic-preservation-design.md`

## Global Constraints

- Baseline is `main@5067e4decb673a39cb96085e34a3a555fe24d58e`.
- Research OS becomes `1.5.12`; Core API stays `1.0` only at release closeout.
- Do not modify or delete frozen v1.5.08–v1.5.11 fixtures to make tests pass.
- Do not add company-specific logic to `src/research_os`.
- Do not calculate research meaning in the presentation layer.
- Every production behavior follows RED -> GREEN -> refactor.

---

### Task 1: Typed claim strength and moat/cycle semantics

**Files:**
- Create: `src/research_os/semantics/__init__.py`
- Create: `src/research_os/semantics/claims.py`
- Test: `tests/unit/semantics/test_claims.py`

**Interfaces:**
- Produces: `ClaimStrengthPolicy.assess(ClaimSupport)`, `CycleAssessment`, `MoatAssessment`.

- [ ] Write tests proving missing/non-comparable evidence caps language strength, recovery does not confirm a trough, and technical barriers do not imply realized economic moat.
- [ ] Run `python -m pytest -q tests/unit/semantics/test_claims.py` and observe import/behavior failures.
- [ ] Implement the minimal frozen Pydantic models and deterministic policy.
- [ ] Re-run the test file and keep it green.

### Task 2: Sensitivity and monitoring context contracts

**Files:**
- Modify: `src/research_os/completeness/models.py`
- Create: `src/research_os/semantics/preservation.py`
- Create: `src/research_os/runtime/semantic_preservation.py`
- Modify: `src/research_os/runtime/professional_modules.py`
- Test: `tests/unit/completeness/test_semantic_context_v1_5_12.py`
- Test: `tests/integration/runtime/test_semantic_preservation_v1_5_12.py`

**Interfaces:**
- Produces: `SemanticPreservationModule` artifacts `semantic.preservation` and `validation.semantic_preservation`.

- [ ] Write RED tests for result-bearing scenarios without material assumptions and thresholds without source/basis/applicability.
- [ ] Add additive scenario and threshold fields; preserve legacy parsing.
- [ ] Validate active artifacts fail-closed and emit stable semantic fingerprints.
- [ ] Prove exact qualifier values survive Runtime Result -> View -> Document.

### Task 3: Canonical valuation reconciliation

**Files:**
- Create: `src/research_os/valuation/reconciliation.py`
- Modify: `src/research_os/valuation/__init__.py`
- Modify: `src/research_os/runtime/inputs.py`
- Modify: `src/research_os/runtime/professional_modules.py`
- Test: `tests/unit/valuation/test_reconciliation_v1_5_12.py`
- Test: `tests/integration/runtime/test_valuation_reconciliation_v1_5_12.py`

**Interfaces:**
- Produces: `ValuationReconciler.reconcile(tuple[ValuationRange, ...]) -> ValuationReconciliation` and artifact `valuation.reconciliation`.

- [ ] Write RED tests for compatible intersection, non-overlap disagreement, incompatible bases, and cross-check-only ranges.
- [ ] Implement range validation and deterministic reconciliation without presentation dependencies.
- [ ] Reject software/release version tokens in model-fitness analytical rationales.
- [ ] Integrate the typed result into the active valuation module.

### Task 4: v1.5.12 view, document and Markdown consumption

**Files:**
- Create: `src/research_os/reporting/research_view_v1_5_12.py`
- Create: `src/research_os/reporting/composer_v1_5_12.py`
- Create: `src/research_os/reporting/markdown_renderer_v1_5_12.py`
- Modify: `src/research_os/reporting/__init__.py`
- Test: `tests/unit/reporting/test_semantic_preservation_v1_5_12.py`
- Test: `tests/regression/architecture/test_semantic_preservation_contract_v1_5_12.py`

**Interfaces:**
- Consumes: `semantic.preservation`, `valuation.reconciliation`, complete sensitivity and monitoring payloads.
- Produces: display-only v1.5.12 report artifacts.

- [ ] Write RED tests that material assumptions, model boundaries and threshold context appear with results.
- [ ] Render canonical reconciliation statuses without calculating ranges in the renderer.
- [ ] Add an architecture regression that forbids version strings in analytical rationale.
- [ ] Verify all v1.5.11 presentation tests remain green.

### Task 5: Freeze v1.5.11 and add v1.5.12 field acceptance

**Files:**
- Modify: `src/research_os/release/replays.py`
- Modify: `src/research_os/release/verification.py`
- Create: `scripts/render_field_acceptance_v1_5_12.py`
- Create: `tests/fixtures/field_acceptance/v1_5_12/manufacturing_semantic_preservation.json`
- Create: `tests/fixtures/field_acceptance/v1_5_12/300034.SZ.json`
- Test: `tests/integration/presentation/test_field_acceptance_v1_5_12.py`

**Interfaces:**
- Produces: frozen v1.5.11 replay plus current v1.5.12 synthetic and real-company acceptance.

- [ ] Pin v1.5.11 runtime/presenter/composer/renderer behavior before switching active exports.
- [ ] Add synthetic minimal reproductions for every semantic defect.
- [ ] Add the PIT real-company fixture with `decision_ts=2026-08-30` and no post-cutoff evidence.
- [ ] Keep first-pass output and record PASS/WARN/FAIL plus layer attribution.

### Task 6: Release integration and final gates

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `src/research_os/release/manifest.py`
- Modify: `research_os_version.json`
- Modify: `CHANGELOG.md`
- Create: `docs/migrations/v1.5.12.md`
- Test: `tests/regression/architecture/test_release_contract_v1_5_12.py`

**Interfaces:**
- Produces: Research OS `1.5.12`, Core API `1.0`, reusable verification pack and active field replay.

- [ ] Update release identity and component fingerprints only after feature tests are green.
- [ ] Run targeted v1.5.12 checks, all historical field replays, full pytest and `python scripts/release_gate_v1_1.py`.
- [ ] Run Chromium HTML/PDF integration and inspect generated artifacts.
- [ ] Verify the feature HEAD and compare it with the frozen main baseline; do not merge or push without available permission.
