# Research Completion Safety Gates Design

**Date:** 2026-08-29
**Baseline:** `zoucx80-rgb/Research-OS@8b23c6f8196a5d96aa3ebc19d9f4ecb4a05532c2`
**Baseline version:** `1.1.0`
**Scope:** Research-OS repository development only.

## Goal

Eliminate seven production failure modes observed in a real distributor research run by moving enforceable rules out of prompts and into typed contracts, validators, orchestration gates, report validation, release checks, and regression tests.

## Non-negotiable invariants

- No Time Travel.
- No Fabricated Data.
- Facts ≠ Calculations ≠ Statistical Evidence ≠ Assumptions.
- Everything Has Lineage.
- Models Beat Simple Benchmarks.
- Research Signal ≠ Auto Trading.
- Historical research snapshots remain immutable.
- Existing release tags remain immutable.
- Development and publication occur only on long-lived branch `main`; no feature branch or PR is required for this task.

## Failure modes and root causes

1. **Repository Discovery Contamination**: repository identity is described in prompt/AGENTS but is not represented by a reusable runtime contract that can reject a mismatched repository or a changed HEAD.
2. **Fabricated Preflight Evidence**: no formal validation currently rejects placeholder-looking SHAs or verifies that required files were read from one frozen HEAD and carry real blob SHAs.
3. **Tool Completion != Research Completion**: `ResearchOS.complete_run()` returns a `ResearchRun` after orchestration succeeds, but no machine-readable final research completion gate independently evaluates all required modules.
4. **Financial Unit / Scale Corruption**: evidence stores a generic `value` and optional `unit`, while no central validator normalizes Chinese financial units, recomputes identities, detects scale mismatches, or blocks valuation/decision/reporting on failure.
5. **Unsupported Expectation Gap**: `ExpectationService` supports PIT vintages, but `decompose_surprise()` accepts arbitrary expected dictionaries and can emit beat/miss labels without an auditable expectation contract.
6. **Invalid Decision State**: the decision engine uses a legal `Literal` enum, but reporting/completion has no explicit validation boundary preventing arbitrary strings such as `NEUTRAL` from entering final artifacts.
7. **Valuation Declaration / Execution Mismatch**: valuation routing selects model fitness but there is no execution contract proving the selected model equals the model actually used, no required scenario lineage, and no driver-bridge requirement.

## Architecture

### 1. Repository preflight contract

Add `research_os.preflight` with immutable models:

- `RepositoryPreflightEvidence`
  - `repository_full_name`
  - `repository_id`
  - `branch`
  - `head_sha`
  - `head_commit_message`
  - `agents_blob_sha`
  - `research_prompt_blob_sha`
  - `verified_at`
  - `agents_ref`
  - `research_prompt_ref`
- `PreflightValidator`

Validation rules:

- exact repository name/id/branch match the official identity;
- SHA values are full 40-hex Git object IDs;
- obvious placeholder/repeated-pattern SHAs are rejected;
- required file refs must equal `head_sha`;
- blob SHAs must be non-placeholder 40-hex values;
- any mismatch raises a validation error and blocks a research run.

This contract does not perform network access itself. Connectors/agents collect raw GitHub evidence; the contract validates it deterministically.

### 2. Evidence lineage strengthening

Extend `Evidence` compatibly with optional fields:

- `raw_value`
- `normalized_value`
- `period`
- `version`

Keep existing `value` for backward compatibility. Add typed lineage contracts for calculations and assumptions:

- `CalculationLineage(formula, input_evidence_ids, output, unit, calculation_version)`
- `AssumptionLineage(label="ASSUMPTION", value, unit, rationale, source_evidence_ids)`

No schema migration is required because these are in-memory/domain contract additions in this release; persistent storage remains compatible.

### 3. Financial sanity gate

Add `research_os.validation.financial` with:

- unit normalization for `元`, `千元`, `万元`, `百万元`, `亿元`;
- `FinancialMetricObservation` carrying metric, period, scope, unit, version, raw value, normalized value and evidence IDs;
- `FinancialSanityInput` containing observations plus declared calculations;
- `FinancialSanityResult(status, errors, normalized_metrics)`;
- `FinancialSanityValidator`.

Hard checks:

- gross profit = revenue - COGS;
- gross margin = gross profit / revenue;
- YoY = current / previous - 1;
- market cap = shares outstanding × price;
- target price = scenario market cap / shares outstanding;
- same metric/period/scope/version cannot conflict after normalization;
- magnitude-ratio checks explicitly flag common ×10/×100/×10000 contamination;
- invalid or missing required arithmetic lineage yields FAIL, not warning.

A failed financial sanity gate blocks valuation execution, decision state generation, and final completion.

### 4. Expectation evidence gate

Add `ExpectationEvidence` and `ExpectationAssessment` contracts. A supported market-expectation conclusion requires:

- expectation source;
- expectation publish timestamp;
- expectation period;
- metric;
- expected value;
- actual value;
- computed surprise;
- vintage identifier;
- expectation publish timestamp <= decision timestamp.

`ExpectationEvidenceValidator` returns `PASS`, `FAIL`, or `INSUFFICIENT_EVIDENCE`.

Terms such as beat/miss/fully priced/priced in/expectation gap/surprise cannot be promoted to a supported conclusion without a validated baseline. Missing baseline must be represented as `INSUFFICIENT_EVIDENCE` rather than inferred from growth.

### 5. Valuation execution contract

Add immutable contracts:

- `ValuationExecution`
  - `selected_model`
  - `model_fitness_score`
  - `selection_reason`
  - `executed_model`
  - `inputs`
  - `assumptions`
  - `scenario_logic`
  - `lineage`
  - `driver_bridge`
- `ValuationExecutionValidator`

Hard rule: `selected_model == executed_model`, else `VALUATION_GATE_FAIL`.

For distributor scenarios, driver bridge must cover the causal path:

`Revenue → Gross Profit → Working Capital → Financing Requirement → Financing Cost → Credit / Inventory Loss → Net Profit / Cash Economics → Valuation`.

Missing material evidence lowers model fitness or causes `INSUFFICIENT_EVIDENCE`; it must not be replaced with fabricated forecast inputs. Incompatible valuation models remain separate and are never mechanically averaged.

### 6. Decision state validation

Reuse the actual `ResearchDecisionState` declaration from `research_os.decision.models`; do not duplicate a stale enum.

Add `validate_decision_state(value)` that instantiates/validates the existing Pydantic decision model or TypeAdapter and rejects any other string. `NEUTRAL` is therefore invalid.

The completion gate must not accept a decision state when prerequisite hard gates have failed.

### 7. Research completion gate

Add `research_os.completion` with:

- `ModuleStatus = PASS | FAIL | INSUFFICIENT_EVIDENCE | NOT_APPLICABLE`;
- `ResearchCompletionInput` containing named module statuses;
- `ResearchCompletionResult(final_status, blocking_modules, module_statuses)`;
- `ResearchCompletionGate`.

Required modules:

- Repository Preflight
- PIT Validation
- Evidence Lineage
- Financial Sanity
- Business Model Router
- KPI Pack
- Capital Efficiency
- Funding Loop
- Driver Graph
- Thesis
- Anti-Thesis
- Falsifiers
- Expectation Evidence
- Forecast Discipline
- Valuation Fitness
- Valuation Execution
- Decision State
- Next Verification Event
- Temporal Consistency

`FINAL_STATUS` is only `COMPLETE` or `INCOMPLETE`.

Policy:

- any `FAIL` => `INCOMPLETE`;
- `INSUFFICIENT_EVIDENCE` is not automatically equivalent to FAIL, but modules whose output is required to support a claimed conclusion remain blocking;
- expectation evidence may be `INSUFFICIENT_EVIDENCE` only if the report explicitly carries that state and makes no beat/miss/priced-in conclusion;
- valuation execution may be `INSUFFICIENT_EVIDENCE` only if no valuation conclusion or legal research decision state depends on a fabricated valuation output;
- tool/process completion never sets final completion directly.

### 8. Temporal consistency gate

Add `NextVerificationEvent(event_name, event_time, evidence_ids)` and validator enforcing:

- `event_time > reference_time` when a dated next event is supplied;
- an event already used as evidence in the run cannot simultaneously be represented as a future verification event;
- already disclosed reports cannot be listed as future checks.

Undated generic phrases such as “next material disclosure” may remain valid only when explicitly represented as unscheduled monitoring, not as a dated future event.

### 9. Distributor KPI pack enhancement

Enhance the existing `DistributorPack`; do not introduce a competing pack. Add where inputs exist:

- Inventory Turns
- Gross Profit / Working Capital
- Working Capital Intensity
- Financing Cost / Gross Profit (existing metric retained)
- Credit Impairment / Gross Profit
- Inventory Impairment / Gross Profit
- Revenue Growth vs Working Capital Growth
- Funding Loop inputs/score linkage
- ROIC (existing metric retained)
- Incremental ROIC

Every calculated metric declares dependencies so orchestration can attach evidence IDs.

### 10. Orchestration and reporting integration

`ResearchOS.complete_run()` must evaluate prerequisite gates before downstream stages. It must not create valuation/decision/final completion when financial sanity or other hard prerequisites fail.

`ResearchRun` gains machine-readable validation/completion state while retaining existing fields for compatible valid runs.

Reporting models gain typed final status and expectation/valuation evidence state so final artifacts cannot silently print unsupported conclusions.

### 11. Release gate

Extend release checks to include dedicated regression nodes for:

- repository preflight;
- financial sanity;
- expectation evidence;
- valuation execution;
- decision validation;
- research completion;
- temporal consistency;
- distributor KPI additions.

CI remains `pytest -q` plus the release script, but the release script now exercises these new semantic gates.

## Regression acceptance cases

The upgrade is not complete until all of the following are enforced:

1. Revenue 655.25 亿元, COGS 634.01 亿元, declared gross profit 2.123 亿元 => FAIL; correct gross profit is ~21.24 亿元.
2. 2.123 / 655.25 with claimed 3.24% gross margin => FAIL.
3. 759,900,097 shares × price 23 with market cap claimed ~16 亿元 => FAIL.
4. Current/prior revenue inconsistent with declared YoY => FAIL.
5. Same metric/period/scope/version reported as 115.2 亿元 and 11.52 亿元 => FAIL/conflict.
6. “beat expectations” without expectation baseline => FAIL.
7. Missing expectation evidence with no unsupported conclusion => `INSUFFICIENT_EVIDENCE`.
8. selected valuation model PS, executed PE => FAIL.
9. decision state `NEUTRAL` => FAIL.
10. tool run ends while valuation required but incomplete => `FINAL_STATUS=INCOMPLETE`.
11. an already-used interim report listed as next verification event => FAIL.
12. placeholder SHA `abcdefabcdefabcdefabcdefabcdefabcdef1234` => FAIL.
13. preflight file refs not pinned to frozen HEAD => FAIL.

## Versioning

This is a backward-compatible feature/methodology strengthening that adds new public validation contracts and gates without removing v1.1 APIs. Under repository SemVer rules it is a **MINOR** release, targeted as `1.2.0`, not a PATCH. Historical `v1.1.0` remains unchanged.

## Verification before release

- targeted regression tests;
- full `pytest`;
- Research OS release gate;
- migration smoke tests (existing migrations; no new schema migration expected unless implementation discovers persistent-schema necessity);
- financial sanity regressions;
- completion regressions;
- PIT/golden tests;
- changed-file review;
- secret scan;
- GitHub Actions green on final `main` commit;
- remote `main` re-read to confirm final SHA, commit message and changed files.
