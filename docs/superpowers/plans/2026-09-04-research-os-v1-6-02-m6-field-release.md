# Research OS 1.6.02 M6 Field Acceptance and Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve every M1-M5 canonical semantic through Snapshot 2.0, HTTP API v1, Markdown, HTML, and PDF; prove the result on the three fixed real-company cases; freeze the changed v1.6.01 field behavior as historical replay; and release Research OS 1.6.02 through manifest-selected gates.

**Architecture:** M6 adds no research calculation. It extends the existing generic presenter/projector/composer chain with declarative mappings for the nine new artifact IDs, validates canonical-to-presentation semantic fingerprints, and keeps renderers value-preserving. The current `field-v1.6.02` profile executes the latest pipeline; v1.6.01 moves to an immutable exact-commit replay because enabling the hospitality plugin intentionally changes its former no-plugin result.

**Tech Stack:** Python 3.12, Pydantic v2, Snapshot Schema 2.0, FastAPI HTTP API v1, pytest, Hypothesis, Markdown/HTML, Playwright/Chromium PDF, Ruff, mypy, import-linter, build, twine, pip-audit.

**Spec:** `docs/superpowers/specs/2026-09-04-research-os-v1-6-02-professional-research-semantic-closure-design.md`

## Global Constraints

- M1-M5 targeted packs must pass before M6 integration begins.
- Add no calculation of temporal changes, benchmark statistics, valuation gaps, decision rules, sufficiency, hotel KPIs, or funding values to reporting or presentation.
- Keep Core API `2.0`, Plugin API `2.0`, Snapshot Schema `2.0`, and HTTP API `v1`; new artifacts use the existing generic envelopes.
- Old Snapshot 2.0 payloads must continue to decode. Unknown artifact types and changed fingerprints continue to fail closed.
- The current field profile is `field-v1.6.02` and executes current source; it is not registered as an immutable historical replay.
- Freeze v1.6.01 at `fd4ce2a83187a251ea60df0d203271e1778fff6b`. Do not preserve its no-hospitality-plugin assertion in current production behavior and do not add a runtime compatibility switch.
- Keep v1.5.08-v1.5.12 replay profiles, release tags, and historical snapshots unchanged.
- Current field fixtures may contain only traceable company evidence available by the fixed `decision_ts`; no generated research output or fabricated realized outcome may be used as input.
- Company identifiers and field expectations stay in tests/fixtures/scripts, never in `src/research_os`.
- The release is incomplete until the verified local `HEAD` equals verified `origin/main` and the release pipeline is rerun on that exact commit.

---

## File Structure

- Modify `src/research_os/reporting/projectors/` and its registry for declarative projection of M1-M5 artifacts.
- Modify `src/research_os/reporting/research_view.py`, `composer.py`, and `markdown_renderer.py` only where generic section mapping or value formatting is required.
- Modify `src/research_os/semantics/preservation.py` to fingerprint all new investor-visible semantic projections.
- Use the existing HTML/PDF presentation pipeline without adding research logic.
- Create `scripts/render_field_acceptance_v1_6_02.py` and `tests/fixtures/field_acceptance/v1_6_02/cases.json` as the current field profile.
- Create integration/regression tests for reporting, Snapshot, HTTP API, current field output, historical replay, and release governance.
- Modify `src/research_os/release/{manifest,verification,replays}.py`, `scripts/verify_release_pipeline.py`, version metadata, documentation, and CI/release tests.

---

### Task 1: Project every M1-M5 artifact without recomputation

**Files:**
- Modify: `src/research_os/reporting/projectors/__init__.py`
- Modify: `src/research_os/reporting/projectors/_core.py`
- Modify: `src/research_os/reporting/projectors/_market.py`
- Modify: `src/research_os/reporting/projectors/_monitoring.py`
- Modify: `src/research_os/reporting/projectors/_registry.py`
- Modify: `src/research_os/reporting/projectors/_shared.py`
- Modify: `src/research_os/reporting/research_view.py`
- Test: `tests/unit/reporting/test_v1_6_02_projectors.py`
- Test: `tests/regression/professional/test_v1_6_02_professional_wiring.py`

**Interfaces:**
- Consumes: the nine canonical artifact envelopes defined by M1-M5.
- Produces: `PresentedArtifact` payloads with the original envelope fingerprint and a lossless display projection validated in Task 2.

- [ ] **Step 1: Write RED registry and payload-preservation tests**

```python
def test_new_canonical_artifacts_are_presented_without_value_changes(run_v1_6_02):
    view = ResearchViewPresenter().present(run_v1_6_02)
    expected_ids = {key.artifact_id for key in NEW_V1_6_02_ARTIFACT_KEYS}
    assert expected_ids <= {item.artifact_id for item in view.artifacts}
    for key in NEW_V1_6_02_ARTIFACT_KEYS:
        envelope = run_v1_6_02.artifacts.envelope(key)
        assert envelope is not None
        presented = view.artifact(key.artifact_id)
        assert presented is not None
        assert presented.value_fingerprint == envelope.value_fingerprint
        assert presented.schema_version == key.schema_version
        assert presented.type_id == key.value_type.__qualname__
```

- [ ] **Step 2: Extend only declarative artifact mappings**

Map the new artifacts to existing sections:

```text
financial.temporal_analysis        -> financial
research.sufficiency               -> readiness
forecast.benchmark_evidence        -> expectation
valuation.market_anchor            -> valuation
valuation.market_gap               -> valuation
decision.input_assessment          -> decision
decision.derivation                -> decision
industry.capability_assessment     -> scope
capital.funding_loop_bridge        -> capital
```

Each projector may translate labels, enum display text, and field order. It must select fields already present in the canonical value and may not calculate ratios, changes, thresholds, status, or conclusions.

- [ ] **Step 3: Guard the semantic boundary in source tests**

Extend the professional wiring regression so projector/composer/renderer source cannot import domain services such as `TemporalAnalysisService`, `TimeSeriesBacktester`, `ValuationMarketGapService`, `DecisionEngine`, `ResearchSufficiencyEvaluator`, `MetricCalculator`, or `FundingLoopAnalyzer`.

- [ ] **Step 4: Run and commit**

```bash
pytest -q tests/unit/reporting/test_v1_6_02_projectors.py tests/regression/professional/test_v1_6_02_professional_wiring.py tests/unit/reporting/test_v1_6_current_reporting.py
git add src/research_os/reporting tests/unit/reporting/test_v1_6_02_projectors.py tests/regression/professional/test_v1_6_02_professional_wiring.py
git commit -m "feat: project v1.6.02 research semantics"
```

### Task 2: Preserve semantics through Composer, Markdown, HTML, and PDF

**Files:**
- Modify: `src/research_os/reporting/composer.py`
- Modify: `src/research_os/reporting/markdown_renderer.py`
- Modify: `src/research_os/semantics/preservation.py`
- Test: `tests/regression/presentation/test_v1_6_02_investor_body.py`
- Test: `tests/integration/presentation/test_v1_6_02_section_ids.py`
- Test: `tests/integration/presentation/test_v1_6_02_semantic_preservation.py`

**Interfaces:**
- Consumes: `HumanReadableResearchView` with canonical value fingerprints.
- Produces: sectioned report document and Markdown/HTML/PDF with unchanged semantic meaning.

- [ ] **Step 1: Write RED section and decision-density tests**

```python
def test_v1_6_02_investor_body_contains_new_decision_semantics(document):
    body = render_markdown(document).split("## 审计附录", maxsplit=1)[0]
    assert "跨期趋势" in body
    assert "样本外基准" in body
    assert "市场隐含差距" in body
    assert "决策推导" in body
    assert "研究充分性" in body
    assert "行业能力缺口" in body


def test_report_never_turns_missing_hotel_metrics_into_zero(document):
    body = render_markdown(document)
    assert "ADR：缺失" in body
    assert "OCC：缺失" in body
    assert "RevPAR：缺失" in body
    assert "ADR：0" not in body
```

- [ ] **Step 2: Compose new blocks using existing section order**

Add the projected artifacts to their mapped sections. Keep existing v1.6.01 sensitivity, next-verification-event, first-page decision/risk, and audit-appendix behavior unchanged. Bump only presenter/composer/renderer fingerprints whose emitted structure actually changes.

- [ ] **Step 3: Extend semantic preservation validation**

For each new artifact, compare the canonical semantic projection with its presented and composed projection. Exclude only audit-only lineage identifiers from investor-visible comparison; preserve statuses, reasons, values, units, periods, comparison bases, caveats, and missingness. Report mismatches as typed `SemanticViolation` records with artifact ID and field path.

- [ ] **Step 4: Verify all output formats**

The integration test renders Markdown and HTML, renders PDF when `RESEARCH_OS_RUN_PDF_INTEGRATION=1`, extracts every PDF page, and checks that the same status/value/unit/basis tokens are present. It also reruns the existing first-page contract.

- [ ] **Step 5: Run and commit**

```bash
pytest -q tests/regression/presentation/test_v1_6_02_investor_body.py tests/integration/presentation/test_v1_6_02_section_ids.py tests/integration/presentation/test_v1_6_02_semantic_preservation.py tests/regression/presentation/test_v1_6_01_investor_body.py tests/integration/presentation/test_v1_6_01_section_ids.py
git add src/research_os/reporting src/research_os/semantics/preservation.py tests/regression/presentation tests/integration/presentation
git commit -m "feat: preserve v1.6.02 report semantics"
```

### Task 3: Prove Snapshot 2.0 and HTTP API v1 round trips

**Files:**
- Modify: `tests/unit/snapshots/test_codec.py`
- Modify: `tests/property/snapshots/test_canonicalization_properties.py`
- Create: `tests/integration/runtime/test_v1_6_02_snapshot_roundtrip.py`
- Create: `tests/integration/api/test_v1_6_02_generic_artifacts.py`
- Modify: `tests/contract/api/test_openapi_v1.py`

**Interfaces:**
- Consumes: M1-M5 `ArtifactEnvelope` values in the existing catalog.
- Produces: identical decoded values and unchanged generic HTTP response envelopes.

- [ ] **Step 1: Write RED codec/catalog round-trip tests**

```python
@pytest.mark.parametrize("key", NEW_V1_6_02_ARTIFACT_KEYS)
def test_v1_6_02_artifact_round_trips_through_snapshot_codec(key, complete_result):
    snapshot = SnapshotService().build(command=command(), result=complete_result)
    decoded = SnapshotCodec().decode(SnapshotCodec().encode(snapshot))
    assert decoded.artifacts.require(key) == complete_result.artifacts.require(key)
```

Include a property test for deterministic encoding and tamper failure. Verify old Snapshot 2.0 fixtures without the new optional artifacts still decode; do not add defaults to their stored payloads.

- [ ] **Step 2: Confirm catalog registration is sufficient**

The current codec resolves value types from the core artifact catalog. Register missing keys through M1-M5 `core_artifacts.py`; change codec implementation only if a failing test proves the catalog path is insufficient. Do not change envelope fields, hash projection, or `ArtifactKey` identity. If such a change appears necessary, stop for contract/version review.

- [ ] **Step 3: Exercise generic API reads**

Create a run through the HTTP API, list artifacts, read each new artifact, persist/reload its snapshot, and assert the existing response shape remains `{artifact_id, schema_version, type_id, payload, ...}`. OpenAPI must gain no version-specific route and retain HTTP API `v1`.

- [ ] **Step 4: Run and commit**

```bash
pytest -q tests/unit/snapshots tests/property/snapshots tests/integration/runtime/test_v1_6_02_snapshot_roundtrip.py tests/integration/api/test_v1_6_02_generic_artifacts.py tests/contract/api/test_openapi_v1.py
git add tests/unit/snapshots tests/property/snapshots tests/integration/runtime/test_v1_6_02_snapshot_roundtrip.py tests/integration/api/test_v1_6_02_generic_artifacts.py tests/contract/api/test_openapi_v1.py
git commit -m "test: verify v1.6.02 snapshot and api round trips"
```

### Task 4: Add the current three-company field profile

**Files:**
- Create: `scripts/render_field_acceptance_v1_6_02.py`
- Create: `tests/fixtures/field_acceptance/v1_6_02/cases.json`
- Modify: `tests/fixtures/field_acceptance/v1_6_02/300034.SZ.json`
- Modify: `tests/fixtures/field_acceptance/v1_6_02/001287.SZ.json`
- Modify: `tests/fixtures/field_acceptance/v1_6_02/301073.SZ.json`
- Create: `tests/integration/presentation/test_field_acceptance_v1_6_02.py`

**Interfaces:**
- Consumes: exactly `300034.SZ`, `001287.SZ`, and `301073.SZ` with one fixed timezone-aware `decision_ts` and evidence available by that timestamp.
- Produces: `field-v1.6.02` machine result plus Markdown, HTML, PDF, snapshot descriptor, and per-case acceptance manifest.

- [ ] **Step 1: Write RED profile/identity tests**

```python
def test_v1_6_02_profile_uses_exactly_three_fixed_real_companies():
    manifest = load_cases()
    assert manifest["profile_id"] == "field-v1.6.02"
    assert {case["case_id"] for case in manifest["cases"]} == {
        "300034.SZ", "001287.SZ", "301073.SZ"
    }
    assert parse_ts(manifest["decision_ts"]).tzinfo is not None
```

- [ ] **Step 2: Build commands from evidence, never expected outputs**

Adapt the v1.6.01 runner to parse M1 period observations, M2 forecast experiments, M3 valuation requests/market anchors, and M5 industry evidence. Expected acceptance fields are assertions only and must never be passed into `ResearchRunCommand`. Reject every evidence item where `publish_ts` or `available_ts` exceeds `decision_ts`, and reject wrong-company references.

- [ ] **Step 3: Derive acceptance exclusively from final results**

The runner reads final canonical artifacts and checks:

```text
all cases: temporal one-point series cannot PASS; sufficiency and decision derivation disclosed
cross-case: at least one executed PIT/OOS registered benchmark
cross-case: at least one basis-compatible valuation market gap
301073.SZ: hospitality plugin resolved; missing ADR/OCC/RevPAR remain explicit
001287.SZ: quantitative funding-loop bridge equals capital engine output
300034.SZ: unsupported operating capabilities appear as capability/sufficiency gaps
all cases: snapshot integrity and reporting semantic preservation PASS
```

Each generated case manifest records the canonical machine-semantics result, research sufficiency/depth, presentation result, execution completion, research readiness, decision state and derivation, PIT/lineage validation, and Snapshot integrity. The summary computes cross-company thresholds only from these per-case canonical records.

No assertion may call a forecasting, valuation, decision, temporal, industry, or funding calculation service outside the application run.

- [ ] **Step 4: Render and inspect current artifacts**

Write outputs only under a caller-supplied directory, defaulting to `build/field-acceptance-v1.6.02`. The test checks generated file inventories and machine manifests. With PDF integration enabled, extract all pages and assert no clipped headings, missing decision/risk first page, raw enum leakage, blank semantic sections, or missing-value substitution.

- [ ] **Step 5: Run and commit**

```bash
pytest -q tests/integration/presentation/test_field_acceptance_v1_6_02.py
RESEARCH_OS_RUN_PDF_INTEGRATION=1 python scripts/render_field_acceptance_v1_6_02.py --case-manifest tests/fixtures/field_acceptance/v1_6_02/cases.json --output-dir build/field-acceptance-v1.6.02 --repository-root . --commit-sha "$(git rev-parse HEAD)"
git add scripts/render_field_acceptance_v1_6_02.py tests/fixtures/field_acceptance/v1_6_02 tests/integration/presentation/test_field_acceptance_v1_6_02.py
git commit -m "test: add v1.6.02 field acceptance profile"
```

### Task 5: Freeze v1.6.01 and select release verification packs

**Files:**
- Modify: `src/research_os/release/replays.py`
- Modify: `src/research_os/release/verification.py`
- Modify: `src/research_os/release/manifest.py`
- Modify: `scripts/verify_release_pipeline.py`
- Modify: `tests/unit/release/test_historical_replay_v1_6.py`
- Modify: `tests/unit/release/test_release_gate.py`
- Modify: `tests/regression/architecture/test_release_governance.py`

**Interfaces:**
- Consumes: immutable v1.6.01 SHA and M1-M6 test locations.
- Produces: one historical `field-v1.6.01` replay profile plus six selected v1.6.02 verification packs.

- [ ] **Step 1: Write RED replay-isolation tests**

```python
def test_v1_6_01_profile_is_frozen_to_approved_release_commit():
    profile = REPLAY_REGISTRY["field-v1.6.01"]
    assert profile.source_commit_sha == "fd4ce2a83187a251ea60df0d203271e1778fff6b"
    assert profile.expected_product_version == "1.6.01"
    assert profile.expected_core_api_version == "2.0"
    assert profile.frozen is True
```

Run the profile in the isolated historical executor and prove imports, Git HEAD, product version, runner, fixture, and output directory originate from that worktree. Current source must not satisfy the old `NO_COMPATIBLE_INDUSTRY_PLUGIN` assertion.

- [ ] **Step 2: Register M1-M6 verification packs**

Add these exact pack IDs, each referencing the focused tests named in its milestone plan:

```text
v1-6-02-temporal-sufficiency
v1-6-02-forecast-benchmark
v1-6-02-valuation-market-gap
v1-6-02-decision-context
v1-6-02-industry-closure
v1-6-02-field-release
```

Select all six in `CURRENT_RELEASE.verification_packs` while retaining all prior packs. Select `field-v1.6.01` after v1.5.12 in `field_replay_profiles`. The current `field-v1.6.02` profile remains the pipeline's current acceptance command, not an immutable replay entry.

- [ ] **Step 3: Make the pipeline current-profile driven**

Replace the hard-coded v1.6.01 current command with v1.6.02 and verify the fixture declares `profile_id == "field-v1.6.02"`. Preserve generic release-pack resolution and historical replay iteration; do not add a patch-specific runtime module.

- [ ] **Step 4: Run and commit**

```bash
pytest -q tests/unit/release/test_historical_replay_v1_6.py tests/unit/release/test_release_gate.py tests/regression/architecture/test_release_governance.py tests/integration/presentation/test_field_acceptance_v1_6_02.py
python scripts/verify_release_pipeline.py --stage release-gate
git add src/research_os/release scripts/verify_release_pipeline.py tests/unit/release tests/regression/architecture/test_release_governance.py
git commit -m "build: select v1.6.02 release gates"
```

### Task 6: Publish version and migration documentation

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `research_os_version.json`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Create: `docs/migrations/v1.6.02.md`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/unit/test_version_metadata.py`
- Modify: `tests/regression/architecture/test_version_authority_v1_6.py`
- Modify: `tests/regression/architecture/test_release_contract_v1_6_0.py`

**Interfaces:**
- Produces: Research OS `1.6.02` as the single build-safe product version; API/schema versions remain unchanged.

- [ ] **Step 1: Write RED version-authority tests**

```python
def test_v1_6_02_keeps_public_api_versions():
    assert RESEARCH_OS_VERSION == CURRENT_RELEASE.version == "1.6.02"
    assert CORE_API_VERSION == "2.0"
    assert PLUGIN_API_VERSION == "2.0"
    assert SNAPSHOT_SCHEMA_VERSION == "2.0"
    assert HTTP_API_VERSION == "v1"
```

- [ ] **Step 2: Update the single version leaf and generated metadata**

Change only `RESEARCH_OS_VERSION` in the build-safe leaf. Update `CURRENT_RELEASE.module_versions` for components whose implementation fingerprint changed, set stable status only after every release check passes, then regenerate `research_os_version.json` with `scripts/generate_release_metadata.py`.

- [ ] **Step 3: Document the additive migration**

The migration note lists the nine new artifact IDs, additive command inputs, unchanged API/schema versions, old Snapshot 2.0 decode behavior, no SQL migration, v1.6.01 replay boundary, and the contract-review triggers from the design. CHANGELOG and README describe field evidence and missingness honestly; they must not claim every company has every model or KPI.

- [ ] **Step 4: Update CI acceptance artifact names**

Keep the existing layered jobs and full-history checkout. Change the current acceptance output to v1.6.02, retain historical replay outputs, and upload current Markdown/HTML/PDF/manifests as reviewable artifacts. Leave the frozen v1.6.0 exact-SHA delivery guards unchanged; v1.6.02 adds no new delivery bundle workflow in this milestone.

- [ ] **Step 5: Run and commit**

```bash
python scripts/generate_release_metadata.py
pytest -q tests/unit/test_version_metadata.py tests/regression/architecture/test_version_authority_v1_6.py tests/regression/architecture/test_release_contract_v1_6_0.py
git diff --check
git add src/research_os/version.py src/research_os/release/manifest.py research_os_version.json CHANGELOG.md README.md docs/migrations/v1.6.02.md .github/workflows/ci.yml tests
git commit -m "chore: prepare Research OS 1.6.02 release"
```

### Task 7: Run the complete release and field acceptance matrix

**Files:**
- Verify only; fix failures in their owning milestone files and tests.

**Interfaces:**
- Consumes: the exact release-candidate Git SHA and manifest-selected current/historical verification matrix.
- Produces: fresh static, test, field, replay, security, build, install, and PDF evidence for that SHA.

- [ ] **Step 1: Run static and architectural quality gates**

```bash
python -m ruff format --check .
python -m ruff check .
python -m mypy src
lint-imports
git diff --check
```

- [ ] **Step 2: Run focused packs and the full suite**

```bash
python scripts/verify_release_pipeline.py --stage release-gate
python -m pytest -q
```

Resolve every failure at its semantic owner. Do not loosen expectations, exclude failing files, or move computations into tests/reporting to obtain green output.

- [ ] **Step 3: Run current and historical acceptance**

```bash
RESEARCH_OS_RUN_PDF_INTEGRATION=1 python scripts/verify_release_pipeline.py --stage acceptance
```

Require `field-v1.6.02` current output plus isolated v1.5.08-v1.5.12 and v1.6.01 replay success. Inspect all three current Markdown and HTML reports and every current PDF page against their machine manifests.

- [ ] **Step 4: Run security and distribution verification**

```bash
python -m pip_audit
python -m build
python -m twine check dist/*
python scripts/verify_distribution.py dist/*.whl
```

Verify the wheel contains no fixture, report, replay, secret, cache, or build artifact and that its clean-environment smoke run exposes version `1.6.02` with unchanged public API versions.

- [ ] **Step 5: Record evidence**

Record the exact commit candidate, command exit codes, current field profile, historical replay SHAs, artifact hashes, and any environment-qualified PDF result in the release verification evidence. A skipped PDF integration is not a successful field release.

### Task 8: Final review, direct-main commit, push, and remote verification

**Files:**
- Review all v1.6.02 changes.
- Update release evidence only if the repository's existing release evidence format requires a tracked file.

**Interfaces:**
- Consumes: the fully verified release candidate and latest fetched `origin/main`.
- Produces: a fast-forwarded, remotely verified `main` release whose checks are rerun on the pushed SHA.

- [ ] **Step 1: Reconcile with remote main**

```bash
git fetch origin main
git status --short
git rev-parse HEAD
git rev-parse origin/main
```

If remote `main` moved, inspect and integrate its changes before release. Do not force-push or overwrite newer work.

- [ ] **Step 2: Audit the complete diff**

Confirm M1-M6 spec coverage, canonical ownership, PIT/lineage guards, deterministic ordering, immutable models, no company-specific production branch, no compatibility shim, no secrets, and no unrelated files. Confirm no release tag or historical snapshot changed.

- [ ] **Step 3: Commit and push verified changes**

```bash
git status --short
git diff --name-only
git add --update
git commit -m "feat: release Research OS 1.6.02"
git push origin main
```

Add any newly created, reviewed release-evidence file by its exact path before committing. Use normal fast-forward push only. If implementation was committed milestone-by-milestone as this plan specifies, this final commit contains only final release metadata/evidence changes; do not rewrite the verified milestone commits.

- [ ] **Step 4: Verify the remote commit and rerun release checks**

```bash
git fetch origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
git status --short
RESEARCH_OS_RUN_PDF_INTEGRATION=1 python scripts/verify_release_pipeline.py
```

Do not edit the frozen v1.6.0 delivery guards as part of this release. If a separate v1.6.02 delivery bundle is later authorized, design its immutable-SHA publication flow as a distinct task; never amend or force-push the released main history.

## M6 Definition of Done

- [ ] All nine M1-M5 artifact IDs reach View, Document, Markdown, HTML, PDF, Snapshot, and generic HTTP reads without semantic recomputation.
- [ ] `SemanticPreservationValidator` proves values, states, units, periods, bases, caveats, and missingness survive presentation.
- [ ] `field-v1.6.02` runs exactly the three fixed companies and meets every cross-case P0 threshold from the design.
- [ ] v1.6.01 executes only through its exact frozen SHA; v1.5.08-v1.5.12 remain unchanged.
- [ ] All six v1.6.02 verification packs are selected by the stable release manifest.
- [ ] Product version is `1.6.02`; Core/Plugin/Snapshot/HTTP versions remain `2.0/2.0/2.0/v1`.
- [ ] Static, full test, PDF acceptance, security, build/install, and release pipelines pass on the exact remote-main SHA.
- [ ] No missing data, realized outcome, industry metric, market anchor, or comparison conclusion was fabricated for acceptance.
- [ ] No force-push, long-lived side branch, tag rewrite, historical snapshot mutation, or unrelated repository change occurred.
