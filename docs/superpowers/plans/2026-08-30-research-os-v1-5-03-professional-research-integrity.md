# Research OS v1.5.03 Professional Research Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make high-level research states, Thesis/Driver claims, professional research questions, quantitative presentation, expectation freshness, and lease/factoring economics evidence- and provenance-aware without creating a second research-state engine.

**Architecture:** Extend existing canonical contracts additively. The runtime remains `ResearchContext + ResearchInputs → ResearchEngine → ResearchRunResult → ResearchViewPresenter`; Completion remains owned solely by `ResearchCompletionGate`. New professional semantics are artifacts/provenance attached to existing modules, not parallel decision logic.

**Tech Stack:** Python 3.12, Pydantic v2, pytest, existing Research OS plugin/runtime/reporting architecture.

**Spec:** `docs/superpowers/specs/2026-08-30-research-os-v1-5-03-professional-research-integrity-design.md`

## Global Constraints

- Display version `v1.5.03`; code SemVer `1.5.3`.
- `CORE_API_VERSION = "1.0"`.
- No time travel, no fabricated evidence, missing remains missing.
- Presentation is one-way and cannot calculate Completion or Decision.
- No full Hospitality plugin in this release.
- Factoring exposure is not automatically treated as debt.
- Backward compatibility for existing `ResearchInputs` string state fields is required.

---

### Task 1: State provenance contract

**Files:**
- Create: `src/research_os/runtime/provenance.py`
- Modify: `src/research_os/runtime/inputs.py`
- Modify: `src/research_os/runtime/builtin_modules.py`
- Test: `tests/regression/research_patterns/test_v1_5_03_professional_integrity.py`

**Interfaces:**
- Produces `StateInput(value, source, evidence_ids, method)` and `resolve_state_input(...)`.
- `DecisionModule` produces artifact `decision.state_provenance`.

- [ ] Write failing tests proving legacy strings resolve as `analyst_assumption`, explicit derived inputs retain provenance, and DecisionModule emits provenance.
- [ ] Run the focused test file and confirm RED.
- [ ] Add `StateInput` and optional provenance-aware inputs without removing legacy fields.
- [ ] Resolve provenance inside DecisionModule and emit the artifact.
- [ ] Run focused tests and confirm GREEN.

### Task 2: Driver-specific lineage and evidence-driven Thesis

**Files:**
- Modify: `src/research_os/drivers/graph.py`
- Modify: `src/research_os/drivers/models.py`
- Modify: `src/research_os/thesis/service.py`
- Modify: `src/research_os/runtime/builtin_modules.py`
- Test: `tests/regression/research_patterns/test_v1_5_03_professional_integrity.py`

**Interfaces:**
- Driver graph builder consumes fact-specific evidence mapping.
- Produces artifact `thesis.signal_assessment`.

- [ ] Add failing tests proving manufacturing Driver nodes do not receive unrelated Evidence IDs and positive Thesis is blocked when signals are mixed/insufficient.
- [ ] Confirm RED.
- [ ] Add conservative manufacturing driver nodes and fact/evidence mapping.
- [ ] Add `ThesisSignalAssessment` and signal gate; keep distributor cash-quality Thesis but expand falsifiers when corresponding metrics exist.
- [ ] Confirm focused GREEN and v1.5.02 regression compatibility.

### Task 3: Structured professional question coverage

**Files:**
- Modify: `src/research_os/reporting/contributions.py`
- Modify: `src/research_os/plugins/builtins.py`
- Modify: `src/research_os/runtime/factory.py`
- Modify: `src/research_os/runtime/builtin_modules.py`
- Test: `tests/regression/research_patterns/test_v1_5_03_professional_integrity.py`

**Interfaces:**
- Adds `ResearchQuestionSpec`, `ResearchQuestionAssessment`.
- Runtime artifact: `report.question_assessments`.

- [ ] Add RED tests for Manufacturing order/utilization questions and Distributor factoring questions.
- [ ] Add additive question specs to contributions.
- [ ] Evaluate questions against capabilities and fact/evidence keys; never invent an answer.
- [ ] Preserve legacy `research_questions` list.
- [ ] Confirm GREEN.

### Task 4: Quantitative presentation semantics

**Files:**
- Modify: `src/research_os/kpi/base.py`
- Modify: `src/research_os/kpi/manufacturing.py`
- Modify: `src/research_os/kpi/distributor.py`
- Modify: `src/research_os/reporting/research_view.py`
- Test: `tests/unit/reporting/test_research_view.py`

**Interfaces:**
- `MetricResult` gains optional display metadata.
- `HumanReadableMetric` gains `formatted_value`, `display_unit`, `period_label`, `period_days`, `annualized`.

- [ ] Add RED tests for percent formatting, day metrics, H1/181-day labels, annualized turnover, and preservation of raw value.
- [ ] Add additive metric display metadata and pack-level metadata.
- [ ] Format without changing canonical values.
- [ ] Confirm GREEN.

### Task 5: Event-relative expectation freshness

**Files:**
- Modify: `src/research_os/runtime/inputs.py`
- Modify: `src/research_os/expectations/validation.py`
- Modify: `src/research_os/runtime/builtin_modules.py`
- Modify: `src/research_os/reporting/research_view.py`
- Test: `tests/regression/research_patterns/test_v1_5_03_professional_integrity.py`

**Interfaces:**
- `assess_consensus_quality(..., latest_material_event_ts=None)`.
- Reason code `CONSENSUS_PREDATES_MATERIAL_EVENT`.

- [ ] Add RED test with consensus 34 days old but pre-dating a new H1 filing.
- [ ] Extend inputs and quality model.
- [ ] Mark such consensus LOW without inferring beat/miss direction.
- [ ] Add Chinese semantic presentation.
- [ ] Confirm GREEN.

### Task 6: Lease-aware Router and working-capital financing exposures

**Files:**
- Modify: `src/research_os/router/classifier.py`
- Modify: `src/research_os/kpi/distributor.py`
- Modify: `src/research_os/capital/engine.py`
- Modify: `src/research_os/runtime/builtin_modules.py`
- Modify: `src/research_os/reporting/research_view.py`
- Test: `tests/regression/research_patterns/test_v1_5_03_professional_integrity.py`

**Interfaces:**
- Lease materiality suppresses only the low-PPE Distributor heuristic.
- Funding result gains additive disclosed economic-exposure fields.

- [ ] Add RED test that a lease-heavy hotel description is not biased toward Distributor by low PPE.
- [ ] Add RED tests for factoring metrics and reason code, including “factoring alone does not equal debt/material risk”.
- [ ] Implement lease safeguard.
- [ ] Add distributor factoring/financing metrics and Funding Loop exposure fields/reasons.
- [ ] Confirm GREEN.

### Task 7: ResearchView professional integrity surface

**Files:**
- Modify: `src/research_os/reporting/research_view.py`
- Modify: `src/research_os/reporting/__init__.py`
- Test: `tests/unit/reporting/test_research_view.py`

**Interfaces:**
- Adds state provenance, question assessments, Thesis signal assessment, event freshness, and valuation-execution/assumption-lineage summary.

- [ ] Add RED tests for all new view fields and for process-status/economic-status language separation.
- [ ] Implement one-way presentation from existing artifacts only.
- [ ] Confirm no presenter function invokes DecisionEngine/CompletionGate/ThesisService.
- [ ] Confirm GREEN.

### Task 8: Versioning, release contract, documentation

**Files:**
- Modify: `src/research_os/version.py`
- Modify: `pyproject.toml`
- Modify: `research_os_version.json`
- Modify: `src/research_os/plugins/builtins.py`
- Modify: `src/research_os/kpi/manufacturing.py`
- Modify: `src/research_os/kpi/distributor.py`
- Modify: `src/research_os/release/runtime.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Create: `docs/migrations/v1.5.03.md`
- Modify: `docs/prompts/stock_research.md`
- Create: `tests/regression/architecture/test_release_contract_v1_5_03.py`

**Interfaces:**
- `RESEARCH_OS_VERSION = "1.5.3"`, Core API `1.0`.
- report fingerprint `professional-research-view@1.1.0`.

- [ ] Add RED release-contract tests.
- [ ] Update versions/fingerprints/plugin pack versions and docs.
- [ ] Preserve all previous release-contract tests.
- [ ] Confirm release-contract GREEN.

### Task 9: Full regression and release integration

**Files:**
- Modify only files required by root-cause fixes from verification.

- [ ] Run architecture/runtime/plugin/knowledge regression suite.
- [ ] Run correctness regression suite.
- [ ] Run migration smoke.
- [ ] Run full `pytest -q`.
- [ ] Run `python scripts/release_gate_v1_1.py`; expected final line `READY: v1.5.3 stable`.
- [ ] Open PR from feature branch to `main` and review diff for scope creep.
- [ ] Merge only after feature-branch CI is green.
- [ ] Re-run the exact full CI on final merged `main` HEAD.
- [ ] Freeze final SHA only when merged-main Release Gate prints `READY: v1.5.3 stable`.
