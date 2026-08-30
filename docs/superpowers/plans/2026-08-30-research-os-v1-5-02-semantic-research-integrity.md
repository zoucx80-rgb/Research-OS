# Research OS v1.5.02 — Semantic Research Integrity Implementation Plan

## Goal

Implement v1.5.02 / SemVer 1.5.2 directly on `main`, preserving the v1.4/v1.5.01 runtime architecture while making research coverage, risk and human-readable presentation consistent end to end.

## Constraints

- `ResearchCompletionGate` remains the only COMPLETE/INCOMPLETE authority.
- `ResearchRunResult` remains the canonical machine result.
- Presentation is one-way and read-only.
- Canonical professional KPI / Driver / Thesis execution follows the primary business model only; secondary models remain classification and coverage metadata.
- No Hotel/Hospitality plugin in this release.
- No company-specific logic.
- No fabricated data or missing-value coercion.
- All behavioral changes require RED → GREEN regression evidence.
- `CORE_API_VERSION` remains `1.0`.

## Task 1 — RED: semantic-integrity regression tests

Add focused tests for:

1. unresolved router classification produces an insufficient Business Model Router module status;
2. missing primary industry coverage generates generic coverage-limited drivers but no active thesis/claim;
3. severe debt-funded negative-OCF funding loop drives DecisionEngine through `material_risk` into `RISK_REVIEW`;
4. end-to-end research view renders coverage gaps, KPI metrics, funding loop, drivers, thesis and valuation states human-readably;
5. expectation quality flags thin and stale consensus using existing `ConsensusVintage` fields;
6. built-in industry plugins return structured non-empty report contributions;
7. a secondary compatible industry plugin cannot contaminate the primary KPI chain;
8. a coverage-limited fallback Driver Graph cannot be promoted to completion PASS merely because the graph object exists.

Commit tests first and verify CI fails for the intended missing behavior.

## Task 2 — Business-model, strategy-isolation and narrative correctness

Files:

- `src/research_os/runtime/builtin_modules.py`
- `src/research_os/runtime/factory.py`
- `src/research_os/plugins/resolver.py`
- `src/research_os/drivers/models.py`
- tests added in Task 1

Changes:

- Business Model module status derives from `classification_status`.
- StrategyResolver executes only the primary business model's industry plugin in the canonical chain.
- Secondary business models remain classification/coverage metadata; unsupported secondary models retain Coverage Gaps, compatible secondary plugins are not co-executed.
- DriverThesisModule consumes `strategy.resolution`.
- Unsupported primary specialized coverage produces a generic, explicitly coverage-limited Driver Graph and no Thesis/Claim.
- Completion aggregation preserves Driver Graph `INSUFFICIENT_EVIDENCE` for coverage-limited fallback graphs.
- Specialized primary-covered paths remain unchanged.

Verify targeted tests green and old resolver/correctness regressions remain compatible.

## Task 3 — Funding-loop material-risk bridge

Files:

- `src/research_os/runtime/builtin_modules.py`
- decision/runtime tests

Changes:

- derive material risk only from canonical funding-loop artifacts;
- `stressed` always material;
- `debt_funded` with both `DEBT_FUNDS_NWC` and `NEGATIVE_OCF` is material;
- pass into existing `DecisionContext.material_risk`.

Do not add a new decision state.

Verify targeted tests green.

## Task 4 — Expectation quality assessment

Files:

- `src/research_os/expectations/validation.py`
- `src/research_os/runtime/builtin_modules.py`
- expectation tests

Add a read-only `ExpectationQualityAssessment` with deterministic quality state and reasons from:

- `source_count`
- `source_quality`
- consensus age relative to decision timestamp.

Store it as `expectation.quality`. Do not replace existing expectation evidence validation.

Verify thin/stale/adequate cases.

## Task 5 — Structured industry report contributions

Files:

- `src/research_os/reporting/contributions.py`
- `src/research_os/plugins/builtins.py`
- `src/research_os/runtime/factory.py`
- plugin contract tests

Add optional metadata to `ReportContribution` and non-empty built-in Manufacturing/Distributor contributions. Preserve protocol compatibility. Persist selected contributions into canonical runtime artifacts before snapshot so presentation does not reconstruct plugin state independently.

Verify both plugins satisfy `IndustryStrategyPack` runtime protocol and contribution content is structured.

## Task 6 — End-to-end ResearchViewPresenter

Files:

- new `src/research_os/reporting/research_view.py`
- `src/research_os/reporting/__init__.py`
- existing `src/research_os/reporting/semantics.py` only where shared helper semantics are needed
- reporting tests

Build a read-only view from one `ResearchRunResult`.

Required sections:

- baseline/version identity;
- business model and classification status;
- primary plugin selections and secondary coverage metadata;
- coverage gaps;
- report contributions;
- KPIs;
- funding loop;
- driver graph and coverage scope;
- thesis/anti-thesis/falsifiers;
- expectation quality;
- valuation routing;
- existing DecisionSummaryPresenter result.

Human labels/explanations must not use raw internal codes as primary text. Raw codes stay metadata.

Verify presenter does not mutate or recompute completion/decision state.

## Task 7 — Release contract and versioning

Files:

- `src/research_os/version.py`
- `pyproject.toml`
- `research_os_version.json`
- `src/research_os/release/runtime.py`
- new `tests/regression/architecture/test_release_contract_v1_5_02.py`
- forward-compatible `tests/regression/architecture/test_release_contract_v1_5_01.py`
- `README.md`
- `CHANGELOG.md`
- `docs/migrations/v1.5.02.md`
- `docs/prompts/stock_research.md`

Set:

- public version `1.5.2`
- display name `v1.5.02`
- report version `semantic-research-view@1.0.0`
- driver model `core:driver-thesis@1.1.0`
- Core API `1.0`

Add release gates for all new correctness properties while retaining earlier v1.5.01/v1.4/correctness gates.

## Task 8 — Verification

Fresh verification on final remote `main`:

1. architecture/runtime/plugin test group;
2. correctness regression group;
3. migration smoke;
4. full `pytest -q`;
5. `python scripts/release_gate_v1_1.py`;
6. inspect remote `main` HEAD and CI logs;
7. confirm no unrelated repositories/files changed and no secrets introduced.

Do not claim release completion unless the exact final remote commit has fresh green evidence.
