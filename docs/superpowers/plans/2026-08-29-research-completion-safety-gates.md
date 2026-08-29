# Research Completion Safety Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add machine-enforced preflight, financial sanity, expectation evidence, valuation execution, decision, completion, and temporal consistency gates, plus distributor regression coverage, so the seven observed Research OS failure modes cannot silently reach a final report.

**Architecture:** Extend current v1.1 contracts rather than replace existing modules. New validators live in focused packages and orchestration composes them before downstream valuation/decision/report completion. Existing legal decision-state types, KPI registry, PIT filtering, snapshots, and release infrastructure remain the source of truth.

**Tech Stack:** Python 3.12, Pydantic 2, pytest, existing Research OS services and GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-08-29-research-completion-safety-gates-design.md`

## Global Constraints

- Repository: `zoucx80-rgb/Research-OS` only.
- Long-lived branch: `main` only; do not create feature branches or PRs.
- Preserve No Time Travel, No Fabricated Data, lineage separation, model benchmark discipline, and research-only decision outputs.
- Do not alter historical tags or snapshots.
- Use TDD: regression test must fail for the intended missing behavior before production implementation.
- Check remote `main` before every write and never force-push.
- Final release must pass targeted tests, full pytest, release gate, PIT/golden, migrations, secret review, and GitHub Actions.

---

### Task 1: Repository preflight contract

**Files:**
- Create: `src/research_os/preflight/__init__.py`
- Create: `src/research_os/preflight/models.py`
- Create: `src/research_os/preflight/validator.py`
- Create: `tests/unit/preflight/test_validator.py`

**Produces:** `RepositoryPreflightEvidence`, `PreflightValidator.validate()`.

- [ ] Write regression tests rejecting `abcdefabcdefabcdefabcdefabcdefabcdef1234`, repository/name/id/branch mismatches, and required file refs not equal to frozen HEAD.
- [ ] Verify those tests fail because preflight contracts do not exist.
- [ ] Implement immutable Pydantic preflight evidence and deterministic validation of exact identity, full 40-hex object IDs, placeholder patterns, blob IDs, and frozen refs.
- [ ] Run preflight tests green.

### Task 2: Evidence lineage and financial sanity gate

**Files:**
- Modify: `src/research_os/domain/evidence.py`
- Create: `src/research_os/domain/lineage.py`
- Create: `src/research_os/validation/__init__.py`
- Create: `src/research_os/validation/financial.py`
- Create: `tests/unit/validation/test_financial_sanity.py`
- Modify: `tests/unit/domain/test_evidence.py`

**Produces:** compatible optional raw/normalized evidence fields, `CalculationLineage`, `AssumptionLineage`, `FinancialSanityValidator`.

- [ ] Add failing tests for the 655.25/634.01/2.123 gross-profit corruption, 2.123/655.25 vs 3.24% margin mismatch, 759,900,097 × 23 market-cap mismatch, wrong YoY, 115.2 vs 11.52 same-metric conflict, and unit normalization for 元/千元/万元/百万元/亿元.
- [ ] Verify RED.
- [ ] Implement normalization to base yuan and deterministic formula/cross-report/scale validation.
- [ ] Ensure hard failures are returned as `FAIL`, not warnings.
- [ ] Run financial and evidence tests green.

### Task 3: Expectation evidence gate

**Files:**
- Modify: `src/research_os/expectations/models.py`
- Modify: `src/research_os/expectations/surprise.py`
- Create: `src/research_os/expectations/validation.py`
- Create: `tests/unit/expectations/test_evidence_gate.py`

**Produces:** `ExpectationEvidence`, `ExpectationAssessment`, `ExpectationEvidenceValidator`.

- [ ] Write failing test: `beat expectations` without a baseline must fail.
- [ ] Write failing test: absent baseline with no unsupported conclusion must yield `INSUFFICIENT_EVIDENCE`.
- [ ] Write failing test: expectation publish timestamp after decision timestamp is rejected.
- [ ] Implement the contract and route surprise labels through validated expectation evidence.
- [ ] Run expectation tests green.

### Task 4: Valuation execution and driver bridge

**Files:**
- Create: `src/research_os/valuation/execution.py`
- Modify: `src/research_os/valuation/router.py`
- Create: `tests/unit/valuation/test_execution.py`

**Produces:** `ValuationExecution`, `ValuationExecutionResult`, `ValuationExecutionValidator`.

- [ ] Write failing test: selected model `ps` and executed model `pe` => `VALUATION_GATE_FAIL`.
- [ ] Write failing distributor test requiring the driver path Revenue → Gross Profit → Working Capital → Financing Requirement → Financing Cost → Credit / Inventory Loss → Net Profit / Cash Economics → Valuation.
- [ ] Implement selected/executed equality, fitness/evidence checks, assumption and lineage fields, and distributor driver-bridge validation.
- [ ] Run valuation tests green.

### Task 5: Decision, completion, and temporal consistency gates

**Files:**
- Create: `src/research_os/decision/validation.py`
- Create: `src/research_os/completion/__init__.py`
- Create: `src/research_os/completion/models.py`
- Create: `src/research_os/completion/gate.py`
- Create: `src/research_os/events/validation.py`
- Create: `tests/unit/decision/test_validation.py`
- Create: `tests/unit/completion/test_gate.py`
- Create: `tests/unit/events/test_temporal_validation.py`

**Produces:** validation driven by the existing `ResearchDecisionState`, `ResearchCompletionGate`, `NextVerificationEventValidator`.

- [ ] Write failing test: `NEUTRAL` is invalid.
- [ ] Write failing test: tool/process completion with required valuation incomplete => `FINAL_STATUS=INCOMPLETE`.
- [ ] Write failing test: already-used interim report listed as next verification event => FAIL.
- [ ] Implement module statuses `PASS|FAIL|INSUFFICIENT_EVIDENCE|NOT_APPLICABLE` and final status `COMPLETE|INCOMPLETE`.
- [ ] Reuse the actual decision Literal through Pydantic validation; do not duplicate the enum.
- [ ] Implement dated event > reference time and used-evidence conflict checks.
- [ ] Run decision/completion/events tests green.

### Task 6: Distributor KPI regression coverage

**Files:**
- Modify: `src/research_os/kpi/distributor.py`
- Modify: `tests/unit/kpi/test_distributor_pack.py`
- Modify: `tests/integration/test_distributor_complete_run.py` as needed.

**Produces:** additional distributor metrics with evidence dependency metadata.

- [ ] Add failing tests for Inventory Turns, Gross Profit / Working Capital, credit impairment / gross profit, inventory impairment / gross profit, revenue growth vs working-capital growth, and Incremental ROIC.
- [ ] Implement only when source facts are present; preserve missing otherwise.
- [ ] Update `metric_dependencies` so orchestration can attach evidence IDs.
- [ ] Run distributor unit/integration tests green.

### Task 7: Orchestration, reporting, and release integration

**Files:**
- Modify: `src/research_os/orchestration.py`
- Modify: `src/research_os/reporting/summary.py`
- Modify: `src/research_os/release/gate.py`
- Modify: `src/research_os/release/runtime.py`
- Modify: `scripts/release_gate_v1_1.py`
- Modify: `tests/integration/test_research_os_orchestrator.py`
- Modify: `tests/unit/reporting/test_summary.py`
- Modify: `tests/unit/release/test_release_gate.py`
- Modify: `tests/unit/release/test_runtime_checks.py`

**Produces:** hard prerequisite ordering and machine-readable final completion state.

- [ ] Add failing integration test proving financial sanity failure prevents valuation, decision state, and final completion.
- [ ] Add failing reporting test proving unsupported decision/expectation output cannot be rendered as a completed research result.
- [ ] Add release-gate tests requiring preflight, financial sanity, expectation evidence, valuation execution, decision validation, completion, temporal consistency, and distributor KPI regression checks.
- [ ] Integrate validators in causal order without breaking valid existing complete runs.
- [ ] Update release script banner/version dynamically from version metadata rather than hard-coded `v1.1.0`.
- [ ] Run orchestration/reporting/release tests green.

### Task 8: Version and documentation

**Files:**
- Modify: `research_os_version.json`
- Modify: `pyproject.toml`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `docs/prompts/stock_research.md`
- Create: `docs/migrations/v1.1-to-v1.2.md`

**Produces:** Research OS `1.2.0` documentation and migration guidance.

- [ ] Update version metadata to `1.2.0` because the change adds backward-compatible validation contracts and methodology gates.
- [ ] Document the new gates, compatibility behavior, expectation `INSUFFICIENT_EVIDENCE` policy, and final completion semantics.
- [ ] Keep the stock-research prompt shorter by delegating enforceable behavior to runtime contracts.

### Task 9: Full verification and remote publication

- [ ] Re-read remote `main` and reconcile if it changed unexpectedly.
- [ ] Run targeted regression suite for all 13 required cases.
- [ ] Run full `pytest -q`.
- [ ] Run `python scripts/release_gate_v1_1.py` (or renamed compatible gate if implementation changes the filename).
- [ ] Run migration smoke tests upgrade head / downgrade base / upgrade head.
- [ ] Run PIT/golden tests explicitly.
- [ ] Review changed files for unrelated modifications.
- [ ] Search changes for secrets/credentials/private keys.
- [ ] Commit verified changes to `main` only and push.
- [ ] Re-read remote HEAD, commit message and changed files.
- [ ] Confirm GitHub Actions final status is green; if not, inspect logs, fix on `main`, and repeat verification.
- [ ] Only then report `RESEARCH_OS_UPGRADE_STATUS = COMPLETE`.
