# Research OS v1.5.02 — Semantic Research Integrity Design

## Status

Approved implementation direction from the v1.5.01 three-company regression on 2026-08-30.

- Display version: `v1.5.02`
- Code SemVer: `1.5.2`
- Baseline: `main@64d265c4981bdac513064a44680508941160257c`
- Core API: `1.0` (unchanged)

## Field-test inputs

The v1.5.01 re-run on 钢研高纳, 中电港 and 君亭酒店 confirmed that period-safe routing and business-model coverage-gap semantics work, but exposed recurring integrity gaps:

1. `DecisionSummaryPresenter` translates only the final decision summary. `StrategyResolution`, `CoverageGap`, KPI metrics, Driver Graph, Thesis artifacts and valuation routing remain outside the canonical human-readable surface.
2. Missing primary industry coverage does not constrain `DriverThesisModule`; a hospitality company without a hospitality plugin can still receive a generic active thesis that looks professionally complete.
3. Funding-loop stress is not propagated into `DecisionContext.material_risk`, so severe debt-funded working-capital growth can be understated by the decision state.
4. `ConsensusVintage.source_count` and `source_quality` exist but are not assessed or presented, so thin/stale expectations can look equivalent to strong current consensus.
5. Primary and secondary industry plugins can both enter the canonical KPI chain, creating cross-pack contamination risk for mixed-business companies.
6. Completion aggregation can incorrectly promote a coverage-limited fallback Driver Graph to PASS merely because a graph object exists.

These are semantic-integrity and research-boundary problems. They do not justify redesigning `ResearchRuntime`, `ResearchRunResult`, snapshots, or `ResearchCompletionGate`.

## Goals

### G1 — Canonical end-to-end human-readable research view

Add a one-way presenter built directly from `ResearchRunResult`:

```text
ResearchRunResult
    ↓
ResearchViewPresenter
    ↓
HumanReadableResearchView
```

It must include human-readable views for:

- business-model classification and classification status;
- selected industry/methodology plugins;
- coverage gaps;
- KPI metrics and missing reasons;
- funding-loop state and reason codes;
- Driver Graph nodes/relations;
- Thesis / Anti-Thesis / Falsifiers;
- expectation snapshot quality;
- valuation routing status;
- existing human-readable decision/completion summary.

Raw machine identifiers remain audit metadata. Human-facing labels/explanations are primary. The presenter must never calculate or change research state.

### G2 — Coverage-aware narrative

When the routed primary business model has no compatible industry strategy plugin, generic modules may continue, but Research OS must not present a generic active thesis as if specialized industry coverage exists.

Required behavior:

- `DriverThesisModule` may build a generic Driver Graph for continuity;
- the graph is explicitly marked generic/coverage-limited;
- no active Thesis/Claim is produced for the unsupported primary industry;
- module status is `INSUFFICIENT_EVIDENCE`;
- Completion remains controlled only by `ResearchCompletionGate`;
- the completion aggregation layer must preserve the evidence-insufficient Driver Graph status even when the fallback graph object exists;
- the human-readable view explains that generic drivers are informational fallback, not specialized industry research.

This preserves the existing rule: missing specialized evidence cannot be narratively filled.

### G3 — Business-model module status truthfulness

`BusinessModelModule` must not return `PASS` merely because some evidence exists.

- `classification_status=classified` -> `PASS`
- `unsupported_taxonomy` -> `INSUFFICIENT_EVIDENCE`
- `insufficient_evidence` -> `INSUFFICIENT_EVIDENCE`

The profile remains available as an artifact so downstream coverage diagnostics can still run.

### G4 — Funding-loop material-risk bridge

Decision state must be able to reflect severe financing risk already present in canonical artifacts.

Automatic material risk is true when Funding Loop is `stressed`, or when it is `debt_funded` and both `DEBT_FUNDS_NWC` and `NEGATIVE_OCF` are present.

`DecisionModule` passes this boolean into the existing `DecisionContext.material_risk` field. No second risk engine is introduced.

This should move severe debt-funded working-capital cases toward `RISK_REVIEW` without changing the legal decision-state set.

### G5 — Expectation quality assessment

Use the existing `ConsensusVintage.source_count` and `source_quality`; do not create a duplicate consensus schema.

Add a non-directional quality assessment with machine state and reasons, based on:

- source count;
- source quality;
- age of consensus vintage relative to `decision_ts`.

Initial deterministic rules:

- source count < 3 -> thin consensus;
- source quality < 0.5 -> low source quality;
- vintage age > 90 days -> stale consensus;
- none of the above -> adequate.

Quality assessment does not invent an expectation direction and does not override PIT validation. It is presented as confidence context.

### G6 — Structured industry report contributions

Keep the existing `report_contributions()` plugin contract, but make built-in Manufacturing and Distributor plugins return non-empty structured contributions.

`ReportContribution` gains backward-compatible optional human-research metadata:

- `title`
- `description`
- `research_questions`

Manufacturing contributions should highlight production/capacity, working capital/cash conversion and capital efficiency. Distributor contributions should highlight working capital, financing loop, financing cost and impairment sensitivity.

This is not a full Manufacturing-depth rewrite and not a Hospitality plugin.

### G7 — Primary industry strategy isolation

The canonical professional research chain must follow the **primary business model only**.

- the resolver may recognize multiple business models;
- only the primary model's compatible industry plugin is selected into `industry_plugins` for canonical KPI / Driver / Thesis execution;
- secondary models remain classification and coverage metadata;
- an unsupported secondary model still emits an `industry_strategy` Coverage Gap;
- a compatible secondary plugin may be recorded in resolver rationale as available coverage metadata, but is not co-executed automatically;
- methodology resolution consumes capabilities from the canonical primary industry strategy, not a union of secondary industry packs.

This prevents a secondary Distributor or Manufacturing signal from contaminating the primary KPI and Driver Graph while preserving visibility into mixed-business companies.

## Human-readable research-view models

Introduce `research_os.reporting.research_view`.

Recommended read-only models:

- `HumanReadableCoverageGap`
- `HumanReadablePluginSelection`
- `HumanReadableMetric`
- `HumanReadableFundingLoop`
- `HumanReadableDriverNode`
- `HumanReadableDriverEdge`
- `HumanReadableThesis`
- `HumanReadableExpectationQuality`
- `HumanReadableValuationModel`
- `HumanReadableResearchView`

The view embeds the existing `HumanReadableDecisionSummary` rather than creating another decision summary.

`ResearchViewPresenter.version = "semantic-research-view@1.0.0"`.

Unknown machine codes use the same safe fallback principle as v1.5.01: readable explanation first, raw code only as metadata.

## Driver / thesis coverage semantics

`DriverGraphResult` gains backward-compatible fields:

```python
coverage_scope: Literal["specialized", "generic"] = "specialized"
coverage_limited: bool = False
coverage_reason: str | None = None
```

`DriverThesisModule` must inspect `strategy.resolution`.

If the primary business model has an `industry_strategy`, `business_model_taxonomy`, or `business_model_evidence` gap and no compatible primary industry pack is present:

- build generic drivers with `coverage_scope="generic"`;
- set `coverage_limited=True`;
- set a structured coverage reason;
- return no theses or claims;
- return `INSUFFICIENT_EVIDENCE`;
- completion must keep Driver Graph at `INSUFFICIENT_EVIDENCE` rather than promoting it solely because a graph exists.

If specialized primary coverage exists, preserve current behavior.

## Presentation semantics

The presenter must localize at least:

- business-model classification statuses;
- coverage-gap types and reason codes;
- built-in plugin IDs;
- KPI metric IDs for Manufacturing and Distributor packs;
- metric statuses and common missing reason codes;
- funding states (`unknown`, `self_funded`, `mixed`, `equity_funded`, `debt_funded`, `stressed`);
- built-in Driver Graph names and relations;
- built-in Thesis templates and falsifier metric names;
- expectation quality states/reasons;
- valuation routing states (`PRIMARY`, `SECONDARY`, `SANITY_CHECK`, `LOW_CONFIDENCE`, `NOT_APPLICABLE`).

Dynamic user/company-specific readable text may pass through unchanged when it is already human-readable.

## Snapshot/version semantics

No snapshot schema redesign is required. Existing snapshots continue storing canonical machine artifacts. `report_version` becomes `semantic-research-view@1.0.0` so a human presentation revision is auditable. The coverage-aware driver model is fingerprinted as `core:driver-thesis@1.1.0`.

## Non-goals

v1.5.02 must NOT:

- add a Hospitality Industry Plugin;
- implement RevPAR/ADR/OCC production KPI calculations;
- add aerospace/manufacturing company-specific logic to Core;
- rewrite DistributorPack or FundingLoop thresholds wholesale;
- restate derecognized factoring as balance-sheet debt automatically;
- redesign the DecisionEngine state set;
- create a second Completion Gate, ResearchRunResult or Snapshot service;
- duplicate the existing expectation consensus schema;
- infer fundamental/valuation/expectation states from prose.

## Release gates

v1.5.02 adds regression gates for:

1. unresolved business-model classification cannot report Business Model Router `PASS`;
2. unsupported primary industry coverage cannot produce an active specialized thesis;
3. generic fallback Driver Graph is explicitly coverage-limited and remains evidence-insufficient in completion;
4. severe debt-funded negative-OCF Funding Loop propagates material risk into `RISK_REVIEW`;
5. end-to-end ResearchView renders CoverageGap/KPI/Driver/Thesis/Valuation semantics without raw machine codes as primary labels;
6. thin/stale consensus is explicitly identified using the existing fields;
7. built-in industry plugins provide structured report contributions;
8. secondary industry plugins cannot contaminate the primary KPI chain while secondary Coverage Gaps remain visible;
9. v1.5.01 semantic and v1.4 architecture/correctness gates remain green;
10. full pytest and Release Gate pass.

## Compatibility

All changes to existing Pydantic models use defaults. Existing plugin manifests, `BusinessModelProfile`, `CoverageGap`, `DriverGraphResult`, `ResearchInputs`, canonical results and snapshots remain loadable. `CORE_API_VERSION` remains `1.0`.
