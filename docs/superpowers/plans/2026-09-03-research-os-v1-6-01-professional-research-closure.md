# Research OS 1.6.01 Professional Research Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Core API 2.0 professional research pipeline so typed research inputs become canonical artifacts, decisions/readiness consume those artifacts, and three real-company regression cases produce professional investor-readable reports without presentation-layer semantic recomputation.

**Architecture:** Keep `ResearchApplication -> ResearchEngine -> ArtifactSnapshot` as the only semantic authority. Add focused Phase-B professional modules that project/compute existing typed domains into the already-registered v2 artifacts, then make Decision/Readiness consume those artifacts. After machine semantics are closed, add artifact-specific human projection/value formatting and section-id-based presentation, then replace the v1.6 acceptance side-channel oracle with final-result/real-company gates.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, mypy, Ruff, import-linter, FastAPI package surface, Playwright/Chromium PDF pipeline, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-03-research-os-v1-6-01-professional-research-closure-design.md`

## Global Constraints

- Frozen implementation baseline: `1cb163b38ac971dfc045e6adfe31e67efdd87af7`.
- Target product version: Research OS `1.6.01`.
- Keep Core API `2.0`, Plugin API `2.0`, Snapshot Schema `2.0`, HTTP API `v1`.
- Never restore v1 Runtime/Reporting/Thesis/Presentation compatibility shims.
- Research semantics are produced only by Engine-executed modules and stored in canonical artifacts.
- Reporting/Presentation may select, label, format, order, paginate and export; they may not recompute research semantics.
- Preserve PIT `publish_ts <= decision_ts`, revision-bound lineage and cross-company guards.
- Missing data remains typed missingness/`INSUFFICIENT_EVIDENCE`; never substitute zero or fabricate industry KPIs.
- Fixed regression decision time: `2026-08-30T00:00:00Z`.
- Milestones merge independently to `main`: M1, then M2, then M3.

---

## File Structure

### M1 runtime

- Create `src/research_os/application/professional_modules.py` — Phase-B modules for financial, capital, semantic, expectation, forecast, peers, valuation, sensitivity, monitoring and methodology projection/computation.
- Modify `src/research_os/application/plan.py` — compile the canonical Phase-B dependency order and make Decision consume professional states.
- Modify `src/research_os/application/service.py` only if module construction needs registry/plugin services not currently passed to the compiler.
- Reuse `src/research_os/runtime/core_artifacts.py` — no schema-version change; add keys only if a spec-required durable value is genuinely absent.
- Reuse domain packages under `capital/`, `expectations/`, `forecasting/`, `peers/`, `valuation/`, `thesis/`, `semantics/`, `monitoring/`; do not duplicate their calculations in application code.
- Add tests under `tests/unit/application/`, `tests/integration/application/`, `tests/regression/professional/`.

### M2 reporting/presentation

- Create `src/research_os/reporting/projectors.py` — artifact-specific presentation projectors/registry.
- Create/expand `src/research_os/reporting/formatting.py` — `HumanValueFormatter`.
- Modify `src/research_os/reporting/research_view.py` — use projectors rather than generic BaseModel JSON for investor-facing payloads.
- Modify `src/research_os/reporting/models.py` — add stable presentation block/section metadata only when required without changing canonical Artifact values.
- Modify `src/research_os/reporting/composer.py` — decision-first section structure; evidence/preflight audit-only.
- Modify `src/research_os/reporting/markdown_renderer.py` — render curated blocks, no recursive raw artifact dump for known artifacts.
- Modify `src/research_os/presentation/html_renderer.py` — route layout by stable `section_id`.
- Add tests under `tests/unit/reporting/`, `tests/integration/presentation/`, `tests/regression/presentation/`.

### M3 acceptance/release

- Modify `scripts/render_field_acceptance_v1_6_0.py` or introduce `scripts/render_field_acceptance_v1_6_01.py` and retire the 1.6.0 script from current release gates.
- Add fixed PIT fixtures under `tests/fixtures/field_acceptance/v1_6_01/` for `300034.SZ`, `001287.SZ`, `301073.SZ` or structurally equivalent anonymized fixtures that preserve the audited semantics.
- Modify `tests/integration/presentation/test_field_acceptance_v1_6_0.py` into the v1.6.01 acceptance tests.
- Modify release manifest/version files and `scripts/verify_release_pipeline.py` pack selection.
- Modify `.github/workflows/ci.yml` only where current acceptance/release gate invocation needs the v1.6.01 suite.

---

## M1 — Professional Runtime Completion

### Task 1: Add RED semantic-sensitivity and acceptance-oracle characterization

**Files:**
- Create: `tests/regression/professional/test_v1_6_01_professional_wiring.py`
- Modify/Test: `tests/integration/presentation/test_field_acceptance_v1_6_0.py`
- Read: `scripts/render_field_acceptance_v1_6_0.py`

**Interfaces:**
- Consumes: `ResearchApplication.run(ResearchRunCommand) -> ResearchRunResult`.
- Produces: regression helpers that compare `ArtifactSnapshot` keys/fingerprints for facts-only vs rich commands.

- [ ] **Step 1: Write a failing rich-vs-facts test**

```python
def test_substantive_professional_inputs_change_canonical_artifacts() -> None:
    facts_only, rich = run_pair("manufacturing")
    assert facts_only.artifacts.value_fingerprint() != rich.artifacts.value_fingerprint()
    assert rich.artifacts.get(VALUATION_RECONCILIATION) is not None
    assert rich.artifacts.get(SCENARIO_SENSITIVITIES) is not None
    assert rich.artifacts.get(MONITORING_PLAN) is not None
```

Use the repository's actual `ArtifactSnapshot` fingerprint/envelope API; do not invent a second hashing helper if a canonical one already exists.

- [ ] **Step 2: Write a failing side-channel oracle test**

```python
def test_research_depth_cannot_pass_without_result_valuation_artifacts() -> None:
    case = load_manufacturing_case_with_valuation_ranges()
    result = run_case_result(case)
    assert result.artifacts.get(VALUATION_RECONCILIATION) is None
    assert research_depth_from_result(result) != "PASS"
```

The first run should expose the current false positive.

- [ ] **Step 3: Run RED tests**

```bash
pytest -q \
  tests/regression/professional/test_v1_6_01_professional_wiring.py \
  tests/integration/presentation/test_field_acceptance_v1_6_0.py
```

Expected: at least the rich-vs-facts and valuation-oracle tests FAIL on baseline `1cb163b...`.

- [ ] **Step 4: Commit the RED characterization**

```bash
git add tests/regression/professional tests/integration/presentation
git commit -m "test: expose v1.6 professional wiring gaps"
```

### Task 2: Implement focused financial/capital canonical modules

**Files:**
- Create: `src/research_os/application/professional_modules.py`
- Modify: `src/research_os/application/plan.py`
- Test: `tests/unit/application/test_professional_modules.py`

**Interfaces:**
- Consumes: `ResearchRunCommand.financial`, `KPI_METRICS`, `FINANCIAL_FACT_SNAPSHOT`.
- Produces: `FINANCIAL_TIME_SERIES`, `RESEARCH_OPERATING_EVIDENCE`, `CASH_FLOW_QUALITY_BRIDGE`, `CAPITAL_EFFICIENCY`, `CAPITAL_FUNDING_LOOP`, `VALIDATION_FINANCIAL`.

- [ ] **Step 1: Write unit RED tests for typed projection and missingness**

Tests must assert typed projection, evidence lineage preservation, and that missing input never becomes a numeric zero. Funding Loop tests must cover a substantive distributor case and an insufficient-evidence case.

- [ ] **Step 2: Run the focused tests and confirm failure**

```bash
pytest -q tests/unit/application/test_professional_modules.py -k 'financial or capital'
```

- [ ] **Step 3: Implement `FinancialResearchModule` and `CapitalResearchModule`**

Use existing typed artifact value models and existing capital domain services. `professional_modules.py` may adapt command input into those services, but must not duplicate formulas already owned by `capital/` or metrics registries.

- [ ] **Step 4: Add modules to `ResearchPlanCompiler` in dependency order**

Required prefix:

```python
(
    ResolvedStrategyModule(strategy),
    KpiProviderModule(strategy, self._registry),
    FinancialResearchModule(command.financial),
    CapitalResearchModule(command.financial),
    ...,
)
```

Use `ModuleSpec.requires` for real dependency ordering; tuple order must not be the only correctness mechanism.

- [ ] **Step 5: Run unit + application integration tests**

```bash
pytest -q tests/unit/application tests/integration/application
```

- [ ] **Step 6: Commit** `feat: project financial and capital research artifacts`.

### Task 3: Implement semantic/thesis/driver modules

**Files:**
- Modify: `src/research_os/application/professional_modules.py`
- Modify: `src/research_os/application/plan.py`
- Test: `tests/unit/application/test_professional_modules.py`
- Test: `tests/regression/professional/test_v1_6_01_professional_wiring.py`

**Interfaces:**
- Consumes: `ResearchRunCommand.thesis`, `KPI_METRICS`, capital artifacts, prior `THESIS_PORTFOLIO`.
- Produces: `DRIVERS_GRAPH`, `THESIS_SEMANTIC_SIGNAL_ASSESSMENT`, `SEMANTIC_CLAIMS`, enriched thesis semantics through existing typed contracts.

- [ ] **Step 1: Add RED tests for cycle/moat claim strength** using existing semantic enums and ensure technical-barrier evidence cannot become realized economic moat without the required economic evidence.
- [ ] **Step 2: Add RED test that thesis/semantic artifacts appear in a rich manufacturing run**.
- [ ] **Step 3: Implement modules by calling existing thesis/semantic services**; no presentation wording here.
- [ ] **Step 4: Run focused tests**.

```bash
pytest -q tests/unit/application/test_professional_modules.py -k 'thesis or semantic or driver'
pytest -q tests/regression/professional/test_v1_6_01_professional_wiring.py -k manufacturing
```

- [ ] **Step 5: Commit** `feat: wire driver thesis and semantic artifacts`.

### Task 4: Implement expectation, forecast and peer modules

**Files:**
- Modify: `src/research_os/application/professional_modules.py`
- Modify: `src/research_os/application/plan.py`
- Test: `tests/unit/application/test_professional_modules.py`

**Interfaces:**
- Consumes: `command.expectations`, `command.forecasting`, `command.peers`.
- Produces: `EXPECTATION_SNAPSHOT`, `EXPECTATION_QUALITY`, `EXPECTATION_GAP`, `EXPECTATION_CONSENSUS_DISTRIBUTION`, `FORECAST_EVALUATION`, `PEERS_NORMALIZED`.

- [ ] **Step 1: Write RED tests for consensus vintage/gap and missing-data behavior**.
- [ ] **Step 2: Write RED forecast benchmark-discipline test**; insufficient benchmark evidence must not become a strong supported result.
- [ ] **Step 3: Write RED peer normalization test**; comparison-basis mismatch remains typed fail-closed.
- [ ] **Step 4: Implement minimal modules using existing domain services/models**.
- [ ] **Step 5: Run** `pytest -q tests/unit/application/test_professional_modules.py -k 'expectation or forecast or peer'`.
- [ ] **Step 6: Commit** `feat: wire expectation forecast and peer artifacts`.

### Task 5: Implement valuation routing/execution/reconciliation modules

**Files:**
- Modify: `src/research_os/application/professional_modules.py`
- Modify: `src/research_os/application/plan.py`
- Test: `tests/unit/application/test_professional_modules.py`
- Test: `tests/regression/professional/test_v1_6_01_professional_wiring.py`

**Interfaces:**
- Consumes: `command.valuation`, `PEERS_NORMALIZED`, forecast/financial artifacts when required by existing valuation services.
- Produces: `VALUATION_ROUTING`, `VALUATION_EXECUTION`, `VALUATION_RESULT`, `VALUATION_RECONCILIATION`.

- [ ] **Step 1: Write RED model-fitness/routing tests**; model downgrade rationale remains economic and typed.
- [ ] **Step 2: Write RED reconciliation tests** for `INTERSECTION`, `CROSS_CHECK_BAND`, `MODEL_DISAGREEMENT`, `NOT_COMPARABLE` using the existing service.
- [ ] **Step 3: Implement valuation modules**. Typed externally-computed execution/ranges may be projected with lineage; application code must not invent unavailable model internals.
- [ ] **Step 4: Make the original side-channel characterization GREEN because final result now contains valuation artifacts**.
- [ ] **Step 5: Run focused valuation and professional-wiring tests**.
- [ ] **Step 6: Commit** `feat: wire canonical valuation artifacts`.

### Task 6: Implement sensitivity, monitoring, methodology and prior-run modules

**Files:**
- Modify: `src/research_os/application/professional_modules.py`
- Modify: `src/research_os/application/plan.py`
- Test: `tests/unit/application/test_professional_modules.py`

**Interfaces:**
- Consumes: `command.readiness.sensitivities`, `command.monitoring`, resolved strategy/plugin coverage.
- Produces: `SCENARIO_SENSITIVITIES`, `MONITORING_PLAN`, `MONITORING_PRIOR_RUN_REVIEW`, `METHODOLOGY_DISCLOSURE`.

- [ ] **Step 1: Write RED sensitivity lineage/caveat tests**; result-bearing sensitivity retains assumptions/model boundary/applicability/caveats.
- [ ] **Step 2: Write RED monitoring next-event tests**.
- [ ] **Step 3: Write RED no-plugin methodology/limitation test for hospitality**; no hotel KPI fabrication.
- [ ] **Step 4: Implement modules**.
- [ ] **Step 5: Run focused tests**.
- [ ] **Step 6: Commit** `feat: wire sensitivity monitoring and methodology artifacts`.

### Task 7: Make Decision consume canonical professional states

**Files:**
- Modify: `src/research_os/application/plan.py`
- Create if needed: `src/research_os/application/decision_inputs.py` if state mapping would otherwise overload `plan.py`.
- Test: `tests/unit/application/test_professional_decision.py`
- Test: `tests/regression/professional/test_v1_6_01_professional_wiring.py`

**Interfaces:**
- Consumes: thesis/semantic, capital/funding, expectation, valuation artifacts.
- Produces: `DECISION_RECORD`, `DECISION_STATE_PROVENANCE`.

- [ ] **Step 1: Write RED tests proving defaults no longer dominate**; distributor funding risk must appear in provenance and be able to affect Decision through canonical artifacts.
- [ ] **Step 2: Write RED valuation/expectation provenance test**.
- [ ] **Step 3: Refactor `PortfolioDecisionModule` to derive `DecisionContext` from `ResearchStateView`**; no company-specific compiler flags.
- [ ] **Step 4: Run unit and regression tests**.
- [ ] **Step 5: Commit** `feat: derive decisions from canonical research states`.

### Task 8: Close Readiness and M1 integration

**Files:**
- Modify only if needed: `src/research_os/readiness/service.py`
- Test: `tests/integration/application/test_professional_research_run.py`
- Test: `tests/regression/professional/test_v1_6_01_professional_wiring.py`

**Interfaces:**
- Consumes: final canonical ArtifactSnapshot + Completion result.
- Produces: correct `ResearchReadinessAssessment`.

- [ ] **Step 1: Add RED rich-readiness tests**; substantive artifacts with lineage pass dimensions, facts-only remains incomplete.
- [ ] **Step 2: Add three-company machine-semantic integration tests** using deterministic fixtures and artifact presence/absence assertions, not prose snapshots.
- [ ] **Step 3: Change readiness only if existing substantive/lineage rules cannot express the spec**; prefer fixing producer lineage over weakening readiness.
- [ ] **Step 4: Run M1 verification**.

```bash
pytest -q tests/unit/application tests/integration/application tests/regression/professional
python -m mypy src
ruff check src tests scripts
lint-imports
pytest -q
```

- [ ] **Step 5: Commit M1 closeout** `feat: complete v1.6.01 professional runtime closure`.

---

## M2 — Human-readable Reporting & Presentation

### Task 9: Add RED investor-body quality tests

**Files:**
- Create: `tests/regression/presentation/test_v1_6_01_investor_body.py`

- [ ] **Step 1: Assert forbidden body leakage**: `Schema:`, raw 64-char hashes, `source_url`, `plugin_id`, raw machine reason codes.
- [ ] **Step 2: Assert decision-first required sections and body size budget <= 350 lines excluding audit**.
- [ ] **Step 3: Run and confirm RED on the 1.6.0-style renderer**.
- [ ] **Step 4: Commit RED tests**.

### Task 10: Implement `HumanValueFormatter`

**Files:**
- Modify: `src/research_os/reporting/formatting.py`
- Test: `tests/unit/reporting/test_formatting.py`

- [ ] **Step 1: RED tests** for CNY, percent ratio, days, multiples, percentage points and None.
- [ ] **Step 2: Implement Decimal-safe deterministic display formatting** without changing canonical values.
- [ ] **Step 3: Run tests**.
- [ ] **Step 4: Commit** `feat: add deterministic human value formatting`.

### Task 11: Implement artifact-specific presentation projectors

**Files:**
- Create: `src/research_os/reporting/projectors.py`
- Modify: `src/research_os/reporting/research_view.py`
- Test: `tests/unit/reporting/test_projectors.py`

**Interfaces:**
- Consumes: canonical `ArtifactEnvelope[T]`.
- Produces: curated presentation payload/block with source artifact identity/fingerprint.

- [ ] **Step 1: RED projector tests** for business model/KPI/capital/thesis/valuation/decision/readiness.
- [ ] **Step 2: Implement explicit registry keyed by artifact identity**.
- [ ] **Step 3: Make evidence/preflight audit-only**.
- [ ] **Step 4: Keep generic fallback only for audit/debug, never investor body known artifacts**.
- [ ] **Step 5: Run reporting unit tests**.
- [ ] **Step 6: Commit**.

### Task 12: Compose decision-first report document and strict body/audit split

**Files:**
- Modify: `src/research_os/reporting/models.py`
- Modify: `src/research_os/reporting/composer.py`
- Modify: `src/research_os/reporting/markdown_renderer.py`
- Test: `tests/unit/reporting/test_report_composer.py`
- Test: `tests/regression/presentation/test_v1_6_01_investor_body.py`

- [ ] **Step 1: RED tests for stable section IDs/order**.
- [ ] **Step 2: Add curated section/block presentation contract**.
- [ ] **Step 3: Move `evidence.*` and repository preflight to audit appendix**.
- [ ] **Step 4: Replace raw recursive known-artifact rendering with curated block/table rendering**.
- [ ] **Step 5: Run tests and enforce <=350-line body fixture budget**.
- [ ] **Step 6: Commit**.

### Task 13: Move HTML layout routing to section_id and verify PDF

**Files:**
- Modify: `src/research_os/presentation/html_renderer.py`
- Test: `tests/integration/presentation/test_html_renderer.py`
- Test: `tests/integration/presentation/test_professional_pdf.py`

- [ ] **Step 1: RED test that all known v2 sections have semantic ids/classes and no `report-section-N` fallback**.
- [ ] **Step 2: Implement section_id layout mapping; localized title is display only**.
- [ ] **Step 3: Render real Chromium/Playwright PDFs for fixed fixtures**.
- [ ] **Step 4: Assert first-page text contains decision snapshot/key risk or limitation**.
- [ ] **Step 5: Run M2 verification**.

```bash
pytest -q tests/unit/reporting tests/integration/presentation tests/regression/presentation
python -m mypy src
ruff check src tests scripts
lint-imports
pytest -q
```

- [ ] **Step 6: Commit M2 closeout** `feat: complete v1.6.01 professional reporting presentation`.

---

## M3 — Real-company Acceptance & Release Hardening

### Task 14: Replace side-channel field acceptance with final-result oracle

**Files:**
- Create: `scripts/render_field_acceptance_v1_6_01.py`
- Modify current gate references to `scripts/render_field_acceptance_v1_6_0.py`
- Create: `tests/integration/presentation/test_field_acceptance_v1_6_01.py`

- [ ] **Step 1: RED test: fixture valuation ranges without final valuation artifact cannot PASS research depth**.
- [ ] **Step 2: RED test: presentation non-empty is insufficient when forbidden body leakage exists**.
- [ ] **Step 3: Implement result-based machine/depth/presentation dimensions**.
- [ ] **Step 4: Remove current helper path that computes release PASS from fixture-only reconciliation**.
- [ ] **Step 5: Run tests**.
- [ ] **Step 6: Commit**.

### Task 15: Add fixed three-company current-process fixtures

**Files:**
- Create: `tests/fixtures/field_acceptance/v1_6_01/300034_sz.json`
- Create: `tests/fixtures/field_acceptance/v1_6_01/001287_sz.json`
- Create: `tests/fixtures/field_acceptance/v1_6_01/301073_sz.json`
- Test: `tests/integration/presentation/test_field_acceptance_v1_6_01.py`

- [ ] **Step 1: Build fixtures only from previously PIT-validated evidence at `2026-08-30`**.
- [ ] **Step 2: Encode steel valuation/sensitivity/monitoring/cycle-moat inputs**.
- [ ] **Step 3: Encode distributor funding-loop facts and monitoring input**.
- [ ] **Step 4: Encode hospitality core financial + lease evidence and no compatible plugin expectation**.
- [ ] **Step 5: Assert exact required/forbidden artifact sets by company**.
- [ ] **Step 6: Assert professional report quality constraints**.
- [ ] **Step 7: Commit**.

### Task 16: Wire v1.6.01 acceptance into verification/release gates

**Files:**
- Modify: `src/research_os/release/manifest.py` or current version source.
- Modify: `scripts/verify_release_pipeline.py`
- Modify: `.github/workflows/ci.yml`
- Modify relevant release-contract tests.

- [ ] **Step 1: RED release-contract tests for version/status/packs**.
- [ ] **Step 2: Set Research OS version `1.6.01`; keep API/schema versions unchanged**.
- [ ] **Step 3: Add v1.6.01 current-process acceptance pack to release gate**.
- [ ] **Step 4: Keep historical v1.5.08–v1.5.12 replay isolated and unchanged**.
- [ ] **Step 5: Run release tests**.
- [ ] **Step 6: Commit**.

### Task 17: Full release verification and three-report inspection

- [ ] **Step 1: Run quality**.

```bash
ruff check .
ruff format --check .
python -m mypy src
lint-imports
```

- [ ] **Step 2: Run full test suite**: `pytest -q`.
- [ ] **Step 3: Run `python scripts/verify_release_pipeline.py --stage acceptance`**; current v1.6.01 three-company acceptance PASS and historical replay 5/5 PASS.
- [ ] **Step 4: Run package/security**.

```bash
python -m pip_audit
python -m build
python -m twine check dist/*
python scripts/verify_distribution.py
```

- [ ] **Step 5: Run release gate**.

```bash
python scripts/verify_release_pipeline.py --stage release-gate
git diff --check
```

- [ ] **Step 6: Render and inspect three company Markdown/HTML/PDF outputs**. Steel must show valuation/sensitivity/monitoring; distributor Funding Loop/financing pressure; hospitality fail-closed but core facts/lease limitation. Raw Artifact dump must not dominate investor body.
- [ ] **Step 7: Commit closeout** `release: complete professional research closure v1.6.01`.

---

## Milestone Merge Procedure

For each M1/M2/M3:

1. Work on an isolated feature branch based on latest verified `main`.
2. Run focused tests plus full pytest/quality gates before claiming completion.
3. Push feature branch and wait for GitHub CI success.
4. Merge/fast-forward only after CI success; do not force-push `main`.
5. Re-fetch `main` and freeze its exact HEAD as the next milestone parent.
6. Keep M1/M2/M3 independently reviewable.

## Plan Self-Review Result

- Spec coverage: M1 covers canonical professional semantics/Decision/Readiness; M2 covers human projection/formatting/body-audit/HTML-PDF; M3 covers oracle/three-company/release.
- Placeholder scan: no incomplete implementation placeholders or unspecified test phases remain.
- Type consistency: artifact names match `runtime/core_artifacts.py`; command domains match `application/command.py`; API/schema versions remain 2.0/2.0/2.0/v1.
- Scope: M1→M2→M3 are sequential dependencies and each yields independently testable software, so a single master plan with milestone merge boundaries is appropriate.
