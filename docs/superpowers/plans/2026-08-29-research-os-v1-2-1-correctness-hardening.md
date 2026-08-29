# Research OS v1.2.1 Correctness Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Research OS `1.2.1` as a company-neutral correctness-hardening release for A-share research, fixing interim-period arithmetic, missing-value coercion, KPI applicability truthfulness, completion consistency and version drift without adding company-specific behavior.

**Architecture:** Add a small shared period-semantic contract, make funding classification evidence-aware, make KPI registry resolution distinguish generic CorePack from specialized business-model support, make `ResearchCompletionGate` the only completion policy authority, and centralize runtime version metadata. Preserve existing v1.2 request shapes and avoid database/schema changes.

**Tech Stack:** Python 3.11+, Pydantic, pytest, existing Research OS domain/orchestration modules, GitHub Actions, existing release gate.

**Spec:** `docs/superpowers/specs/2026-08-29-research-os-v1-2-1-correctness-hardening-design.md`

## Global Constraints

- Repository is exactly `zoucx80-rgb/Research-OS`; work directly on `main` only.
- No feature/release branches, no force push, no historical tag/snapshot rewrites.
- Version target is exactly `1.2.1`.
- No ticker/company-specific code or company-specific financial fixtures.
- Valid v1.2 request shapes remain accepted, including `facts: dict`, `safety=None`, and free-text `claimed_conclusions`.
- No database migration.
- Missing data remains missing; `None != 0`.
- Interim period-sensitive metrics never silently assume 365 days.
- CorePack alone never makes specialized KPI analysis PASS.
- `ResearchCompletionGate` is the single completion-policy owner.
- Every behavioral task follows RED -> minimal GREEN -> targeted regression -> commit.

---

## File Structure

**Create**
- `src/research_os/period/__init__.py` — public period-semantic exports.
- `src/research_os/period/models.py` — `ReportingPeriod` and period-type contract.
- `src/research_os/period/resolver.py` — period-day resolution and period-aware turnover helpers.
- `src/research_os/version.py` — single Python runtime version constant.
- `tests/unit/period/test_period_semantics.py` — Q1/H1/Q1-Q3/FY/custom/leap-year matrix.
- `tests/unit/kpi/test_period_sensitive_packs.py` — distributor/manufacturing integration with period context.
- `tests/unit/kpi/test_applicability.py` — specialized-pack truthfulness.
- `tests/unit/completion/test_consistency.py` — completion/result/report propagation contract.
- `tests/unit/test_version_consistency_v1_2_1.py` — all version surfaces agree.
- `tests/regression/research_patterns/test_v1_2_1_correctness_patterns.py` — anonymous cross-cutting regression patterns.

**Modify**
- `src/research_os/kpi/base.py` — resolution metadata and MetricResult reason support if needed.
- `src/research_os/kpi/finance_core.py` — period-aware turnover arithmetic.
- `src/research_os/kpi/distributor.py` — consume shared period semantics; distinguish period/annualized turns where needed.
- `src/research_os/kpi/manufacturing.py` — consume shared period semantics.
- `src/research_os/capital/engine.py` — preserve missing funding inputs and produce `unknown` when classification is not evidenced.
- `src/research_os/completion/gate.py` — claim-capability normalization and single policy.
- `src/research_os/reporting/summary.py` — consume `ResearchCompletionResult` rather than re-defining COMPLETE.
- `src/research_os/decision/models.py` — use runtime version source.
- `src/research_os/orchestration.py` — period context, KPI applicability status, funding unknown status, completion propagation, version fallback.
- `src/research_os/__init__.py` — expose centralized version.
- `src/research_os/release/runtime.py` / `src/research_os/release/gate.py` — register new semantic regressions.
- `scripts/release_gate_v1_1.py` — keep historical filename for compatibility, emit current runtime version.
- `.github/workflows/ci.yml` — run targeted v1.2.1 semantic regressions before migration/full suite/release gate.
- `pyproject.toml`, `research_os_version.json`, `CHANGELOG.md`, `README.md`, `docs/prompts/stock_research.md` — release metadata/behavioral documentation.

---

### Task 1: Period Semantics and Period-Sensitive KPI Arithmetic

**Files:**
- Create: `src/research_os/period/__init__.py`
- Create: `src/research_os/period/models.py`
- Create: `src/research_os/period/resolver.py`
- Create: `tests/unit/period/test_period_semantics.py`
- Create: `tests/unit/kpi/test_period_sensitive_packs.py`
- Modify: `src/research_os/kpi/base.py`
- Modify: `src/research_os/kpi/finance_core.py`
- Modify: `src/research_os/kpi/distributor.py`
- Modify: `src/research_os/kpi/manufacturing.py`

**Interfaces:**
- Produces: `ReportingPeriod`, `resolve_period_days(period) -> int | None`, `turnover_days(avg_balance, flow, period) -> float | None`, `period_turns(flow, avg_balance) -> float | None`, `annualized_turns(flow, avg_balance, period) -> float | None`.
- Existing `pack.calculate(facts)` remains callable. Period metadata is supplied through reserved facts such as `reporting_period` / `period_days` or a compatible helper extracted inside the pack; do not require callers to adopt a wholly new request type.

- [ ] **Step 1: Write failing period-semantic tests**

```python
from datetime import date
from research_os.period.models import ReportingPeriod
from research_os.period.resolver import resolve_period_days, turnover_days


def test_h1_turnover_days_uses_explicit_period_days():
    p = ReportingPeriod(period_type="H1", period_days=181, is_cumulative=True)
    assert turnover_days(50.0, 200.0, p) == 50.0 / 200.0 * 181


def test_interim_period_without_length_is_missing():
    p = ReportingPeriod(period_type="H1", is_cumulative=True)
    assert resolve_period_days(p) is None
    assert turnover_days(50.0, 200.0, p) is None


def test_fy_leap_year_derives_366_days():
    p = ReportingPeriod(period_type="FY", period_start=date(2028,1,1), period_end=date(2028,12,31), is_cumulative=True)
    assert resolve_period_days(p) == 366


def test_q1_q3_is_cumulative_not_standalone_q3():
    p = ReportingPeriod(period_type="Q1_Q3", period_days=274, is_cumulative=True)
    assert turnover_days(75.0, 300.0, p) == 75.0 / 300.0 * 274
```

- [ ] **Step 2: Add failing pack regressions**

Use synthetic distributor/manufacturing facts where the old hard-coded `*365` result differs from H1/Q1-Q3 expected values. Assert missing when interim `period_days` is absent. Assert annual FY compatibility remains correct.

- [ ] **Step 3: Run targeted tests and confirm RED**

Run:

```bash
pytest -q tests/unit/period/test_period_semantics.py tests/unit/kpi/test_period_sensitive_packs.py
```

Expected: FAIL because period module/period-aware pack behavior does not exist.

- [ ] **Step 4: Implement minimal shared period contract**

Implement a frozen Pydantic `ReportingPeriod` with `period_type`, optional dates, optional positive `period_days`, and `is_cumulative`. `resolve_period_days` prioritizes explicit days, derives inclusive calendar days from dates, allows FY 365 fallback only when no dates/days exist, and returns `None` for interim periods without length.

- [ ] **Step 5: Route both existing packs through shared helpers**

Remove duplicated `*365` arithmetic from Distributor and `finance_core.turnover_days`. Preserve valid annual behavior. Add explicit `inventory_turns_period` / `inventory_turns_annualized` if needed while preserving legacy `inventory_turns` compatibility for FY inputs.

- [ ] **Step 6: Run targeted tests and existing KPI tests**

```bash
pytest -q tests/unit/period tests/unit/kpi
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/research_os/period src/research_os/kpi tests/unit/period tests/unit/kpi
git commit -m "fix: make KPI periods explicit"
```

---

### Task 2: Missing-Safe Funding Loop

**Files:**
- Modify: `tests/unit/capital/test_engine.py`
- Modify: `src/research_os/capital/engine.py`
- Modify: `src/research_os/orchestration.py`

**Interfaces:**
- `FundingLoopResult.funding_state` supports `unknown`.
- Partial evidence may yield valid `reason_codes` while classification stays `unknown`.
- Orchestration maps `unknown` to `Funding Loop = INSUFFICIENT_EVIDENCE`.

- [ ] **Step 1: Write failing missing-value tests**

```python
def test_negative_ocf_without_funding_inputs_does_not_invent_funding_state():
    r = CapitalEfficiencyEngine().funding_loop({"operating_cash_flow": -10.0})
    assert r.funding_state == "unknown"
    assert "NEGATIVE_OCF" in r.reason_codes
    assert "DEBT_FUNDS_NWC" not in r.reason_codes


def test_known_zero_debt_is_not_missing():
    r = CapitalEfficiencyEngine().funding_loop({
        "delta_nwc": 10.0,
        "delta_debt": 0.0,
        "delta_equity": 0.0,
        "operating_cash_flow": 15.0,
    })
    assert r.funding_state == "self_funded"
```

Add cases for missing `delta_nwc`, missing debt, missing equity, missing OCF, and fully evidenced debt-funded/stressed classifications.

- [ ] **Step 2: Run targeted tests and confirm RED**

```bash
pytest -q tests/unit/capital/test_engine.py
```

Expected: at least the missing-input classification test fails because existing code coerces missing to zero.

- [ ] **Step 3: Implement minimal evidence-aware classification**

Use explicit `is None` checks. Never use `value or 0` for research facts. Only compute ratios/classifications when required operands are known.

- [ ] **Step 4: Update orchestration status mapping**

`Funding Loop = PASS` only when the result is meaningfully classified; `unknown` becomes `INSUFFICIENT_EVIDENCE`.

- [ ] **Step 5: Run capital + orchestration integration tests**

```bash
pytest -q tests/unit/capital tests/integration/test_research_safety_context.py
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/research_os/capital/engine.py src/research_os/orchestration.py tests/unit/capital/test_engine.py tests/integration/test_research_safety_context.py
git commit -m "fix: preserve missing funding evidence"
```

---

### Task 3: KPI Applicability Truthfulness

**Files:**
- Create: `tests/unit/kpi/test_applicability.py`
- Modify: `tests/unit/kpi/test_registry.py`
- Modify: `src/research_os/kpi/base.py`
- Modify: `src/research_os/orchestration.py`

**Interfaces:**
- Registry exposes whether a specialized pack supports the routed primary model.
- CorePack is generic infrastructure, not proof of specialized KPI coverage.

- [ ] **Step 1: Write failing registry/applicability tests**

```python
def test_core_pack_only_is_not_specialized_support():
    registry = KpiPackRegistry.default()
    profile = BusinessModelProfile(
        company_id="synthetic-consumer",
        primary_model="consumer",
        secondary_models=[],
        confidence=0.9,
        evidence_ids=["e1"],
        router_version="router@test",
    )
    resolution = registry.resolve_with_status(profile)
    assert [p.pack_id for p in resolution.specialized_packs] == []
    assert "consumer" in resolution.unsupported_models
```

Add supported manufacturing/distributor cases.

- [ ] **Step 2: Add failing orchestration regression**

Synthetic primary `consumer` with only CorePack must yield `validation_statuses["KPI Pack"] == "INSUFFICIENT_EVIDENCE"`, never PASS.

- [ ] **Step 3: Run targeted tests and confirm RED**

```bash
pytest -q tests/unit/kpi/test_registry.py tests/unit/kpi/test_applicability.py tests/integration/test_research_safety_context.py
```

- [ ] **Step 4: Implement minimal resolution metadata**

Add a focused `KpiPackResolution` (or equivalent internal result) that retains CorePack, specialized packs and unsupported models while preserving legacy `resolve(profile) -> list[packs]` for compatibility if existing callers rely on it.

- [ ] **Step 5: Make orchestration status truthful**

PASS requires specialized support for the primary routed model. Do not create fake industry packs.

- [ ] **Step 6: Run KPI + integration tests and commit**

```bash
pytest -q tests/unit/kpi tests/integration/test_research_safety_context.py
git add src/research_os/kpi/base.py src/research_os/orchestration.py tests/unit/kpi tests/integration/test_research_safety_context.py
git commit -m "fix: report unsupported KPI models"
```

---

### Task 4: Completion Single Source of Truth

**Files:**
- Create: `tests/unit/completion/test_consistency.py`
- Modify: `tests/unit/reporting/test_completion_validation.py`
- Modify: `src/research_os/completion/gate.py`
- Modify: `src/research_os/reporting/summary.py`
- Modify: `src/research_os/orchestration.py`

**Interfaces:**
- `ResearchCompletionGate.evaluate(...)` remains authoritative.
- Add `normalize_claim_capabilities(values: list[str]) -> set[str]` internally.
- Reporting accepts/consumes completion output and must not independently reject a completion result that the gate legitimately produced.

- [ ] **Step 1: Write failing claim-capability tests**

```python
def test_expectation_aliases_normalize_to_expectation_capability():
    assert normalize_claim_capabilities(["beat", "priced_in"]) == {"EXPECTATION"}


def test_valuation_aliases_normalize_to_valuation_capability():
    assert normalize_claim_capabilities(["target_price", "fair_value"]) == {"VALUATION"}
```

Add gate tests proving unsupported expectation/valuation claims block while unclaimed capabilities are not fabricated.

- [ ] **Step 2: Write runtime/report consistency RED test**

Construct a valid `ResearchCompletionResult`, pass it to reporting builder, and assert report `final_status`, blockers and module statuses exactly match it. Include COMPLETE and INCOMPLETE cases.

- [ ] **Step 3: Run targeted completion/reporting tests**

```bash
pytest -q tests/unit/completion tests/unit/reporting
```

Expected: RED because reporting currently owns a second COMPLETE policy and does not carry full completion result.

- [ ] **Step 4: Implement normalized capability policy in completion gate**

Keep legacy strings accepted; normalize before policy evaluation. Do not conflate a research decision state with an automatic target-price/valuation claim.

- [ ] **Step 5: Refactor reporting to consume completion result**

Expose `blocking_modules` and `module_statuses` in the summary/report model as needed. Remove the independent COMPLETE rules that conflict with `ResearchCompletionGate`.

- [ ] **Step 6: Run completion/reporting/integration tests and commit**

```bash
pytest -q tests/unit/completion tests/unit/reporting tests/integration/test_research_safety_context.py
git add src/research_os/completion src/research_os/reporting src/research_os/orchestration.py tests/unit/completion tests/unit/reporting tests/integration/test_research_safety_context.py
git commit -m "fix: unify research completion policy"
```

---

### Task 5: Version Governance and v1.2.1 Release Surfaces

**Files:**
- Create: `src/research_os/version.py`
- Create: `tests/unit/test_version_consistency_v1_2_1.py`
- Modify: `src/research_os/__init__.py`
- Modify: `src/research_os/decision/models.py`
- Modify: `src/research_os/orchestration.py`
- Modify: `src/research_os/reporting/summary.py`
- Modify: `pyproject.toml`
- Modify: `research_os_version.json`
- Modify: `scripts/release_gate_v1_1.py`

**Interfaces:**
- `RESEARCH_OS_VERSION = "1.2.1"` is the Python runtime source.
- Existing `research_os.__version__` remains available.

- [ ] **Step 1: Write failing version-consistency test**

Verify package version, centralized constant, pyproject version, JSON version, default DecisionContext/DecisionStateRecord version, reporting default and orchestration fallback all equal `1.2.1`.

- [ ] **Step 2: Run test and confirm RED**

```bash
pytest -q tests/unit/test_version_consistency_v1_2_1.py tests/unit/test_version_metadata.py
```

Expected: RED because current release is `1.2.0` and stale `1.1.0` defaults remain.

- [ ] **Step 3: Implement centralized runtime version and update surfaces**

Update public metadata to `1.2.1`; import the constant for Python defaults/fallbacks instead of hard-coding `1.1.0`/`1.2.0`.

- [ ] **Step 4: Run version/release-script tests and commit**

```bash
pytest -q tests/unit/test_version_consistency_v1_2_1.py tests/unit/test_version_metadata.py tests/unit/release
git add src/research_os/version.py src/research_os/__init__.py src/research_os/decision/models.py src/research_os/orchestration.py src/research_os/reporting/summary.py pyproject.toml research_os_version.json scripts/release_gate_v1_1.py tests/unit/test_version_consistency_v1_2_1.py tests/unit/test_version_metadata.py tests/unit/release
git commit -m "chore: align v1.2.1 version metadata"
```

---

### Task 6: Cross-Cutting Regression, Release Gate, CI and Documentation

**Files:**
- Create: `tests/regression/research_patterns/test_v1_2_1_correctness_patterns.py`
- Modify: `src/research_os/release/runtime.py`
- Modify: `src/research_os/release/gate.py`
- Modify: `tests/unit/release/test_ci_contract.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `docs/prompts/stock_research.md`
- Add migration note only if needed to explicitly state "no database migration"; do not create an Alembic revision.

**Interfaces:**
- Release gate registers `period_semantics`, `missing_value_semantics`, `kpi_applicability`, `completion_consistency`, `version_consistency`.
- Final release output: `READY: v1.2.1 stable`.

- [ ] **Step 1: Write anonymous regression patterns**

Include synthetic patterns for:

1. H1 balance/flow period arithmetic.
2. Missing funding inputs preserving unknown.
3. Unsupported routed model not reporting KPI PASS.
4. Runtime/report completion equality.
5. Version surface equality.

Do not include real ticker/company names or copied company financial values.

- [ ] **Step 2: Add failing release/CI contract tests**

Require all five v1.2.1 checks to be registered and CI to run targeted v1.2.1 semantics before migration smoke/full pytest/release gate.

- [ ] **Step 3: Run targeted release tests and confirm RED**

```bash
pytest -q tests/regression/research_patterns/test_v1_2_1_correctness_patterns.py tests/unit/release
```

- [ ] **Step 4: Register new release checks and CI steps**

Preserve all existing v1.2 checks. Add the five new semantic checks; do not remove migration smoke.

- [ ] **Step 5: Update release docs**

CHANGELOG/README/canonical stock research prompt must document period truthfulness, missing-value semantics, KPI applicability and completion single-source behavior without mentioning any company as methodology truth.

- [ ] **Step 6: Run full local-equivalent test commands where available**

```bash
pytest -q tests/integration/storage/test_v1_2_lineage_migration.py
pytest -q
python scripts/release_gate_v1_1.py
```

Expected: all pass; release script prints `READY: v1.2.1 stable`.

- [ ] **Step 7: Commit release integration**

```bash
git add tests/regression src/research_os/release tests/unit/release .github/workflows/ci.yml CHANGELOG.md README.md docs/prompts/stock_research.md
git commit -m "release: finalize v1.2.1 correctness hardening"
```

---

### Task 7: Fresh Remote Verification and Real-Company Acceptance Rerun

**Repository changes:** none unless verification reveals a generalized defect; if a generalized defect is found, return to TDD with a synthetic regression before any production fix.

- [ ] **Step 1: Re-read remote `main` HEAD and verify no concurrent unexpected commit was overwritten.**
- [ ] **Step 2: Verify GitHub Actions for exact final SHA.** Confirm targeted v1.2.1 tests, migration smoke, full pytest and Release Gate all succeed.
- [ ] **Step 3: Compare pre-v1.2.1 baseline to final SHA.** Confirm only expected code/tests/docs/CI/version files changed; no unrelated project files, credentials, extra branches, historical tags or snapshots changed.
- [ ] **Step 4: Freeze final `main` SHA and rerun the canonical stock-research protocol for 中电港 using fresh external evidence with `decision_ts=2026-08-29`.** Company facts remain external to the repository.
- [ ] **Step 5: Specifically verify the acceptance run exercises the repaired semantics:** H1 period-aware working-capital days/turns, missing-safe funding classification, supported DistributorPack applicability, one completion result, and `1.2.1` version fingerprint.
- [ ] **Step 6: Report the research result separately from methodology verification.** If the run remains INCOMPLETE because expectation/forecast/valuation evidence is missing, treat that as a valid completion-gate outcome rather than a software failure.

---

## Plan Self-Review

- Spec coverage: all five v1.2.1 correctness themes, compatibility, no migration, synthetic fixtures, release gate and post-release real-company rerun are mapped to tasks.
- Placeholder scan: no TBD/TODO/"similar to" placeholders are used; each behavioral task contains concrete RED/GREEN commands and expected outcomes.
- Type consistency: period helpers, `FundingLoopResult.funding_state`, KPI resolution semantics, completion propagation and version constant are defined before downstream tasks consume them.
- Scope discipline: full FinancialFact/restatement/forecast/valuation-output/decision redesign remains explicitly excluded from this PATCH release.
