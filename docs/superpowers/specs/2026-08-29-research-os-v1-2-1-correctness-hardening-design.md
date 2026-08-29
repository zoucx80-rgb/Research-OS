# Research OS v1.2.1 Correctness Hardening — Design

**Status:** Approved for implementation  
**Date:** 2026-08-29  
**Target version:** `1.2.1`  
**Repository:** `zoucx80-rgb/Research-OS`  
**Development branch:** `main` only

## 1. Purpose

Research OS v1.2.1 is a PATCH-level correctness hardening release. It does not add company-specific logic and does not attempt to expand Research OS into every possible business-model-specific KPI pack. Its purpose is to make existing research behavior truthful and numerically correct across A-share companies and reporting periods.

The design is motivated by defects exposed during a real Research OS v1.2.0 company run, but all implementation and regression fixtures must be generalized and synthetic. No security code, ticker-specific branch, company-specific financial number, valuation conclusion, thesis, or decision state may be embedded into the methodology repository as a golden truth.

The five correctness themes are:

1. Period Semantics
2. Missing Value Semantics
3. KPI Applicability Truthfulness
4. Completion Policy Single Source of Truth
5. Version Governance

## 2. Non-Negotiable Invariants

The existing Research OS invariants remain authoritative:

- No Time Travel
- No Fabricated Data
- Facts != Calculations != Statistical Evidence != Assumptions
- Everything Has Lineage
- Models Beat Simple Benchmarks before production promotion
- Research Signal != Auto Trading
- historical snapshots and historical release tags remain immutable

v1.2.1 adds the following explicit correctness invariants:

- `None != 0`.
- Missing data must not silently become a numerical fact.
- Period-sensitive ratios must not assume 365 days for interim cumulative flows.
- A KPI Pack module must not report PASS merely because a generic CorePack exists when no specialized pack supports the routed business model.
- Research completion has one policy owner: `ResearchCompletionGate`.
- Runtime and public version surfaces must agree on `1.2.1`.

## 3. Scope Boundary

### 3.1 In Scope

- Add a shared reporting-period contract used by period-sensitive KPI calculations.
- Correct DSO/DIO/DPO and analogous turnover-day semantics for Q1, H1, Q1-Q3, FY and custom periods.
- Distinguish period turns from annualized turns where a metric exposes turnover counts.
- Preserve missing funding inputs instead of coercing them to zero.
- Allow funding analysis to report partial reason codes while returning `unknown` when funding-state classification lacks evidence.
- Make KPI Pack completion reflect actual specialized-pack applicability.
- Make `ResearchCompletionGate` the only final completion-policy authority; reporting consumes its result rather than redefining completion.
- Normalize legacy free-text claimed conclusions into fixed claim capabilities internally while preserving the existing public input shape.
- Remove stale `1.1.0` runtime defaults and enforce one Research OS version source.
- Add targeted and integration regression coverage plus new Release Gate checks.
- Update version metadata, changelog and public documentation as required for `1.2.1`.

### 3.2 Explicitly Out of Scope

- No ticker- or company-specific code.
- No company-specific research facts in methodology fixtures.
- No new ConsumerPack, ResourcePack, FinancialPack, SoftwarePack or ProjectPack merely to make coverage look broader.
- No full replacement of `facts: dict` with a typed FinancialFact graph.
- No new database migration.
- No full restatement/supersession graph.
- No complete Forecast Engine.
- No Decision Engine redesign.
- No new legal `ResearchDecisionState` values.
- No full `ValuationOutput` contract.
- No rewriting/deleting historical snapshots or release tags.
- No additional development branches.

Those larger changes belong to v1.3 or later.

## 4. Period Semantics

### 4.1 Shared Contract

Introduce a small shared period-semantic unit under `src/research_os/period/`.

A `ReportingPeriod` must represent at least:

- `period_type`: `Q1 | H1 | Q1_Q3 | FY | CUSTOM`
- `period_start`: optional date
- `period_end`: optional date
- `period_days`: optional positive integer
- `is_cumulative`: boolean

The period resolver must prefer explicit `period_days`, otherwise derive days from explicit start/end dates where possible.

For `FY`, if no explicit period length is supplied, a safe annual fallback is allowed. If a year can be established from period boundaries, leap-year day count should be used; otherwise 365 is the compatibility fallback for a true FY flow.

For `Q1`, `H1`, `Q1_Q3` and `CUSTOM`, missing period length must not silently fall back to 365. Period-sensitive metrics become missing with an explicit reason such as `PERIOD_LENGTH_REQUIRED`.

`Q1_Q3` means cumulative first-three-quarter flow and must not be treated as a standalone Q3 flow.

### 4.2 Period-Sensitive KPI Rules

Centralize turnover-day arithmetic so all packs reuse the same implementation.

For average balance `B`, period flow `F`, and explicit period days `D`:

`turnover_days = B / F * D`

If balance or flow is missing, or flow is zero, return missing.

For turnover counts:

- `*_turns_period = F / B`
- `*_turns_annualized = (F / B) * annual_days / D`

Annualized turns are only valid when period length is known.

Existing legacy metric IDs should be preserved where practical. When an existing ID has ambiguous annualization semantics, v1.2.1 must either attach a reason/metadata-compatible interpretation or add explicit period/annualized variants without silently changing a valid annual input.

### 4.3 Packs Affected

At minimum:

- DistributorPack DSO/DIO/DPO/CCC and inventory turns
- ManufacturingPack AR days and inventory days
- shared `finance_core.turnover_days`

Future packs must reuse this period-semantic layer rather than writing their own `* 365` logic.

## 5. Missing Value Semantics

### 5.1 General Rule

Research facts distinguish:

- known numerical zero
- known non-zero value
- missing/unknown value
- not applicable

No research module may use Python truthiness (`value or 0`) when doing so collapses missing values into factual zero.

### 5.2 Funding Loop

`CapitalEfficiencyEngine.funding_loop` must preserve missing `delta_nwc`, `delta_debt`, `delta_equity` and operating cash flow.

A funding state may be classified only when the required facts for that classification are known.

Examples:

- negative OCF alone may produce reason `NEGATIVE_OCF`, but cannot prove `debt_funded` or `stressed` without debt/NWC evidence.
- known `delta_debt == 0` is different from `delta_debt is None`.
- insufficient facts produce `funding_state = "unknown"`.

Orchestration must map an unknown/inadequately evidenced funding result to `Funding Loop = INSUFFICIENT_EVIDENCE`, not PASS.

## 6. KPI Applicability Truthfulness

### 6.1 Problem

The router can classify several business models, while the default KPI registry currently contains CorePack, ManufacturingPack and DistributorPack. A CorePack-only resolution must not make the KPI Pack module PASS for a routed model with no specialized KPI support.

### 6.2 Resolution Contract

Add a small resolution result, for example `KpiPackResolution`, containing:

- core pack
- resolved specialized packs
- requested/routed business models
- unsupported models

The exact public shape may remain internal if that is sufficient to preserve API compatibility.

Completion semantics:

- primary model has a supported specialized pack -> KPI Pack may PASS, subject to existing calculation rules.
- primary model has no specialized pack -> KPI Pack = `INSUFFICIENT_EVIDENCE`.
- unsupported secondary models are recorded but do not automatically invalidate a supported primary pack unless policy explicitly requires them.

Do not create placeholder industry packs merely to make status PASS.

## 7. Completion Policy Single Source of Truth

### 7.1 Authority

`ResearchCompletionGate` is the single policy owner for final completion.

The canonical data flow is:

`module statuses -> ResearchCompletionGate -> ResearchCompletionResult -> snapshot/reporting/API`

Reporting must consume completion output rather than redefining a second independent COMPLETE policy.

### 7.2 Claim Capabilities

Maintain backward compatibility with the existing `claimed_conclusions: list[str]` input, but normalize internally to fixed capabilities:

- `FUNDAMENTAL`
- `EXPECTATION`
- `FORECAST`
- `VALUATION`
- `DECISION`

Legacy expectation-related terms such as `beat`, `miss`, `priced_in`, `expectation_gap`, and `expectation` map to `EXPECTATION`.

Legacy valuation terms such as `valuation`, `target_price`, `fair_value` map to `VALUATION`.

A claim capability must not be emitted as validated if its required evidence module is not PASS.

A Research Decision State remains a research state, not an automatic target-price claim. A non-valuation research state such as `RISK_REVIEW` may exist without a validated target price, provided no unsupported valuation claim is made and Completion policy treats remaining modules according to their applicability.

### 7.3 Reporting Consistency

Runtime, snapshot and report must surface the same:

- `final_status`
- `blocking_modules`
- `module_statuses`

The following states are regressions and must be rejected by tests:

- runtime COMPLETE / report INCOMPLETE
- runtime INCOMPLETE / report COMPLETE

## 8. Version Governance

Introduce one runtime version source, preferably `src/research_os/version.py`:

`RESEARCH_OS_VERSION = "1.2.1"`

Python runtime defaults must import/use that source rather than hard-code old versions.

The release must verify consistency among:

- `src/research_os/version.py`
- package `__version__`
- `pyproject.toml`
- `research_os_version.json`
- DecisionContext/DecisionStateRecord runtime default
- orchestration fallback
- reporting default
- release-gate output

Any stale runtime `1.1.0` default is a release failure.

## 9. Backward Compatibility

v1.2.1 remains a PATCH release.

Valid v1.2 inputs should continue to work. Existing shapes including `ResearchRunRequest(..., safety=None)`, `facts: dict`, and free-text `claimed_conclusions` remain accepted.

Incorrect historical behaviors are intentionally not preserved:

- interim flows silently multiplied by 365
- missing funding facts silently converted to zero
- unsupported business-model KPI analysis reported PASS because CorePack exists
- conflicting completion semantics between runtime and report
- stale runtime version metadata

No schema migration is required.

## 10. Test Strategy

All new regression fixtures are synthetic and company-neutral.

### 10.1 Period Matrix

Cover:

- FY 365 days
- leap-year FY 366 days when dates establish the year
- Q1 90/91-day examples
- H1 181/182-day examples
- Q1-Q3 273/274-day examples
- custom explicit days
- interim period missing `period_days` -> missing / `PERIOD_LENGTH_REQUIRED`
- zero flow -> missing
- missing average balance -> missing
- period turns vs annualized turns

### 10.2 Missing-Value Matrix

Cover:

- `delta_nwc=None`
- `delta_debt=None`
- `delta_equity=None`
- `ocf=None`
- known zeros for each input
- partial reason-code production without unsupported funding-state classification

### 10.3 KPI Applicability

Cover at least:

- distributor -> specialized pack -> PASS candidate
- manufacturing -> specialized pack -> PASS candidate
- consumer/resource/software/project/financial primary model without specialized pack -> `INSUFFICIENT_EVIDENCE`
- CorePack-only resolution never causes KPI Pack PASS

### 10.4 Completion Consistency

The same `ResearchCompletionResult` must be propagated through orchestration, snapshot and reporting.

Claim-capability parameterized tests must distinguish unsupported expectation/valuation claims from research runs that make no such claim.

### 10.5 Version Consistency

Add a single regression that compares all public/runtime version surfaces and fails on any mismatch.

## 11. Release Gate

Retain all v1.2 release checks and add or expand semantic checks for:

- `period_semantics`
- `missing_value_semantics`
- `kpi_applicability`
- `completion_consistency`
- `version_consistency`

Recommended CI order:

1. install package
2. targeted v1.2.1 semantic tests
3. existing v1.2 migration smoke
4. full `pytest -q`
5. full Research OS Release Gate

Successful release output must state:

`READY: v1.2.1 stable`

## 12. Expected Files

Likely production changes:

- `src/research_os/period/__init__.py`
- `src/research_os/period/models.py`
- `src/research_os/period/resolver.py`
- `src/research_os/semantics/missing.py` only if a shared helper materially reduces duplication
- `src/research_os/version.py`
- `src/research_os/kpi/base.py`
- `src/research_os/kpi/finance_core.py`
- `src/research_os/kpi/distributor.py`
- `src/research_os/kpi/manufacturing.py`
- `src/research_os/capital/engine.py`
- `src/research_os/completion/gate.py`
- `src/research_os/completion/models.py` if needed
- `src/research_os/reporting/summary.py`
- `src/research_os/decision/models.py`
- `src/research_os/orchestration.py`
- `src/research_os/__init__.py`
- release/version metadata and docs

Implementation must remain minimal; files listed here are candidates, not a requirement to touch every path.

## 13. Acceptance Criteria

v1.2.1 is complete only if all of the following hold:

1. Period Correctness — period-sensitive KPIs no longer silently use 365 for interim cumulative flows.
2. Missing Integrity — missing values never silently become factual zeros in the funding path.
3. KPI Applicability Integrity — no specialized pack means no false KPI PASS.
4. Completion Consistency — runtime/snapshot/report expose one final completion result.
5. Version Integrity — all runtime/public version surfaces agree on `1.2.1`.
6. Backward Compatibility — valid v1.2 call shapes remain accepted.
7. No Company-Specific Logic — all new regression fixtures are synthetic and methodology-only.
8. Full Regression — all existing v1.2 tests and release gates still pass in addition to new v1.2.1 checks.
9. No database migration, extra branch, force push, historical tag rewrite or historical snapshot rewrite.
10. After release verification, rerun a real company research acceptance test against the new frozen v1.2.1 `main`; keep company-specific facts external to the repository and use the result only to validate general methodology behavior.
