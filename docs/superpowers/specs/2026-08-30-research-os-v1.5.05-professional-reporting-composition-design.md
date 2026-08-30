# Research OS v1.5.05 — Professional Research Reporting & Composition

Date: 2026-08-30

Status: Proposed design for v1.5.05

Baseline: `857663032bb540740473249f62e0f5ac37d11e19` (`Research OS 1.5.4`, `CORE_API_VERSION = 1.0`)

## 1. Problem Statement

Research OS v1.5.04 materially improved field correctness: comparison-basis semantics, explicit external-equity financing, OCF falsifier aliases, driver-specific thesis evidence, funding-aware distributor PE fitness, and broader one-way human-readable projections are now in place.

The remaining field-test problem is no longer primarily incorrect machine state. It is that the final human-facing output still behaves like a readable projection of many research artifacts rather than a professional investment-research composition.

Three-company output acceptance using 钢研高纳 (`300034.SZ`), 中电港 (`001287.SZ`) and 君亭酒店 (`301073.SZ`) exposed the same structural gap from different business models:

- manufacturing results contain relevant metrics and questions, but the report does not automatically compress product mix, capacity/capex, working capital and cash conversion into one company-specific investment conflict;
- distributor results correctly expose growth, working-capital expansion, debt, negative OCF, financing cost, factoring and PE-fitness constraints, but the final view does not automatically present the causal chain as one investment bridge;
- hospitality is safely identified without being misclassified as distributor when the business is lease-heavy, but the absence of a Hospitality Plugin must become a concise, material capability limitation rather than a long generic report or a fabricated professional hotel thesis.

The v1.5.04 `HumanReadableResearchView` is therefore a successful semantic projection but not yet a complete buy-side report composition contract.

## 2. Design Goal

v1.5.05 will add a professional reporting composition layer that turns already-canonical research artifacts into a concise, company-specific, decision-useful report without becoming a second research engine.

Required one-way flow:

```text
ResearchRunResult
    -> HumanReadableResearchView
    -> ResearchReportComposer
    -> ResearchReportDocument
    -> Markdown / HTML / PDF renderers
```

The Composer may select, rank, group, deduplicate, summarize and format existing human-readable research material. It must not calculate, promote, demote or override canonical research states.

## 3. Alternatives Considered

### A. Continue expanding `HumanReadableResearchView`

Pros:
- smallest number of new types;
- preserves one existing presentation entry point.

Cons:
- mixes semantic translation with editorial composition;
- encourages a single ever-growing projection model;
- makes materiality, deduplication and section ordering hard to test independently;
- increases the risk that presentation code begins to infer research meaning.

Decision: rejected as the primary architecture. `HumanReadableResearchView` remains the complete semantic projection boundary.

### B. Let report templates read `ResearchRunResult` directly

Pros:
- fast access to every artifact;
- easy to build rich reports initially.

Cons:
- duplicates semantic translation in templates;
- creates a second path from machine codes to human conclusions;
- risks a second presentation state source;
- weakens the v1.5.03/v1.5.04 invariant that machine state is metadata and presentation is one-way.

Decision: rejected.

### C. Add a pure `ResearchReportComposer`

Pros:
- separates semantic translation from editorial composition;
- can enforce materiality, deduplication and company specificity without recomputing state;
- easy to regression-test against the three field cases;
- keeps renderers dumb and format-specific.

Cons:
- introduces a new public reporting contract;
- requires explicit rules for materiality and section omission.

Decision: selected.

## 4. Scope

v1.5.05 scope is deliberately narrow and reporting-first.

### 4.1 ResearchReportComposer

Add a pure composer that accepts only `HumanReadableResearchView` and returns `ResearchReportDocument`.

It may:
- choose which already-present items are material enough for the main body;
- sort drivers, risks, gaps and monitoring conditions;
- deduplicate repeated risks or limitations across sections;
- group evidence-backed items into one causal investment bridge;
- omit empty/non-material sections;
- move audit metadata to an appendix;
- format large currency values for human reading;
- create section-level summaries derived only from already-human-readable values and their relationships.

It may not:
- read raw company evidence directly;
- access the Web or a Knowledge Provider;
- calculate financial metrics;
- change Decision State, Completion, Thesis State, Funding Loop, Forecast or Valuation State;
- manufacture missing Hospitality analysis;
- reinterpret a machine result more optimistically or pessimistically.

### 4.2 Investment Decision Snapshot

Add a stable first-page `InvestmentDecisionSnapshot` projection composed from existing human-readable fields.

It must support:
- company identity and decision timestamp;
- business model;
- current fundamental / thesis / expectation / valuation states;
- canonical research decision state;
- 3–5 material drivers;
- 1–3 material risks or contradictions;
- one concise primary thesis statement;
- next verification event;
- evidence confidence;
- material capability/evidence limitation count and the most important limitation.

This snapshot is editorial composition only. All state values are copied from canonical results.

### 4.3 Company-Specific Investment Bridge

Add a human-readable causal bridge built from the existing Driver Graph, Funding Loop, thesis artifacts and valuation driver bridge.

The bridge is a sequence of already-supported nodes such as:

```text
Operating fact / driver
-> financial effect
-> cash / capital effect
-> thesis implication
-> valuation implication
```

The Composer may collapse adjacent nodes and translate labels. It may not invent a missing edge.

Expected field behavior:
- manufacturing: product/capacity/capex -> margin/cash -> ROIC/FCF -> thesis -> valuation;
- distributor: growth -> AR/inventory/NWC -> funding -> financing cost/OCF -> valuation fitness;
- hospitality without plugin: stop at the supported generic edge and explicitly surface the capability break.

### 4.4 Expectation Gap Output Contract

v1.5.04 exposes expectation quality and state but not a sufficiently structured human-facing expectation-gap object.

Add an additive `ExpectationGapResult` / human-readable projection with, when evidenced:
- driver or metric;
- market expectation value/range or directional expectation;
- Research OS view/value/range;
- gap direction and magnitude when mathematically valid;
- source count;
- consensus freshness;
- post-material-event status;
- evidence quality/confidence;
- limitation when consensus is thin or missing.

No expectation gap may be created when market expectation evidence is insufficient. A missing consensus remains missing.

### 4.5 Valuation Result Contract

`ValuationExecution` currently records selected/executed model, inputs, assumptions, scenario rationale, lineage and driver bridge, but it does not standardize the numeric valuation output.

Add an additive `ValuationResult` contract with optional fields suitable for multiple methods:
- `currency`;
- `valuation_date`;
- `equity_value` / `enterprise_value` when applicable;
- `per_share_value` when applicable;
- `base_case`, `bull_case`, `bear_case` values/ranges;
- `primary_range_low`, `primary_range_high`;
- `current_price` and implied upside/downside when evidenced;
- method-specific result payload;
- sensitivity rows or key sensitivity descriptors;
- result evidence/assumption lineage.

The contract must not force false precision. Any field without supported inputs remains missing.

The Composer uses this contract to explain:
1. why the primary model was selected;
2. what alternatives were downgraded;
3. the resulting valuation range;
4. which assumptions dominate sensitivity.

### 4.6 Monitoring / Conviction Contract

Expose an additive human-readable monitoring block from canonical thesis/falsifier/temporal artifacts:
- next verification event;
- conviction-up conditions;
- thesis-broken conditions;
- key metrics to monitor;
- evidence gaps whose resolution can change conviction.

The Composer must not define new economic thresholds. Thresholds must already exist in falsifiers, claims, monitoring artifacts or other canonical state.

### 4.7 Evidence Presentation

Main-body evidence should use a concise `Claim -> Evidence -> Economic Interpretation` presentation.

The main body should not dump raw evidence IDs. Full evidence IDs, source timestamps, formula versions, plugin IDs, component fingerprints and repository SHA remain available in an audit appendix.

No evidence lineage is discarded; only its default display location changes.

### 4.8 Materiality and Deduplication

Add deterministic composition rules.

Main-body priority should favor:
1. canonical decision/thesis contradictions;
2. critical drivers;
3. material Funding Loop risks;
4. valuation-driving assumptions;
5. material expectation gaps;
6. next verification events and falsifiers;
7. material capability/evidence gaps.

Repeated economic meaning must be shown once in the main narrative and referenced elsewhere rather than copied verbatim.

No LLM-only opaque scoring is allowed inside the deterministic core Composer. Materiality rules must be inspectable and regression-testable.

### 4.9 Human Number Formatting

Add display-only number scaling:
- large CNY values may display as 亿元 / 万元 while preserving the machine value;
- percentages, days and multiples retain existing period semantics;
- the formatter must never change calculation inputs or result precision stored in canonical artifacts.

## 5. Lease-Heavy Presentation Guard

v1.5.05 will add a presentation-level guard for lease-heavy businesses.

When canonical evidence/profile indicates material right-of-use assets or lease liabilities, the report must avoid unqualified language such as:
- “现金转化极佳” solely because OCF / net profit is high;
- “轻资产” solely because PPE is low;
- “低资本占用” without lease-adjusted qualification.

The guard does not calculate lease-adjusted ROIC/FCF. It adds an explicit limitation to human presentation when the relevant methodology is absent.

This is cross-industry semantic safety, not Hospitality-specific Core logic.

## 6. HumanReadableResearchView Changes

`HumanReadableResearchView` remains the canonical complete human-readable projection.

Additive fields may include:
- expectation gap projection;
- valuation result projection;
- monitoring/conviction projection;
- lease-heavy presentation limitation;
- evidence citation descriptors needed by the Composer.

The View must remain loss-aware and audit-friendly. It does not perform materiality filtering for the final report.

The presentation fingerprint will be bumped for v1.5.05.

## 7. ResearchReportDocument Contract

Introduce a format-neutral document model, for example:

```text
ResearchReportDocument
  metadata
  decision_snapshot
  sections[]
  audit_appendix
  composition_version
```

A section should contain typed blocks rather than raw free-form template strings, such as:
- narrative block;
- metric table;
- causal bridge;
- thesis/anti-thesis block;
- expectation gap table;
- valuation table;
- monitoring checklist;
- limitation callout;
- evidence note.

Renderers consume this document and must not read `ResearchRunResult`.

## 8. Report Section Policy

The standard report may retain the conceptual section inventory already defined by `ResearchReportModel.standard()`, but v1.5.05 changes it from a static title list into an omission-aware composition policy.

Recommended main body:
1. Investment Decision Snapshot
2. Core Investment Conflict / Driver Bridge
3. Business & Industry Context
4. Financial Quality & Capital Efficiency
5. Thesis / Anti-Thesis / Falsifiers
6. Market Expectations & Expectation Gap
7. Forecast Discipline
8. Valuation & Scenario Analysis
9. Monitoring Checklist
10. Material Research Limitations

Appendix:
- detailed KPI inventory;
- complete Coverage Gap inventory;
- complete Evidence Ledger/provenance;
- plugin/version/component fingerprints;
- repository/SHA/snapshot metadata;
- module execution statuses.

Empty sections are omitted rather than rendered as template noise.

## 9. Compatibility

- `CORE_API_VERSION` remains `1.0` unless implementation proves an unavoidable incompatible public API change.
- Existing `ResearchRunResult`, Completion Gate, Decision Engine, Thesis Engine, Funding Loop and Router remain canonical.
- Existing v1.5.04 snapshots remain readable.
- New reporting and valuation fields are additive with safe defaults.
- Existing integrations consuming `HumanReadableResearchView` continue to work; consumers opting into `ResearchReportDocument` receive the new composition behavior.

## 10. Non-Goals

v1.5.05 will not add:
- a Hospitality Plugin;
- lease-adjusted DCF/ROIC methodology;
- an advanced Manufacturing Plugin;
- a Forecast subsystem rewrite;
- a second Decision Engine;
- a second Completion source;
- company-specific logic in Core;
- web/data retrieval inside Reporting;
- LLM-generated facts or unsupported narrative filling;
- a trading/action execution system.

## 11. Testing Strategy

Implementation must be TDD-first.

### 11.1 Permanent three-case reporting regressions

Add fixtures/golden semantic cases derived from the structural behavior exposed by:
- manufacturing / 钢研高纳-type case;
- distributor / 中电港-type case;
- lease-heavy hospitality-without-plugin / 君亭酒店-type case.

Fixtures must not embed live company facts as reusable methodology truth. They should encode minimal synthetic facts necessary to reproduce the structural behavior.

### 11.2 Required RED regressions

At minimum:
- Composer produces a decision snapshot without recalculating state;
- repeated Funding Loop risks are deduplicated;
- distributor causal bridge preserves growth -> NWC -> funding -> OCF/financing -> valuation order;
- missing expectation consensus does not fabricate an expectation gap;
- thin/pre-event consensus is visibly qualified;
- valuation numeric result remains missing when unsupported;
- valuation scenarios and range render when explicitly supplied;
- hospitality without plugin surfaces a material capability limitation;
- lease-heavy presentation does not label high OCF/NP as unqualified strong cash conversion;
- empty report sections are omitted;
- audit metadata remains present but outside the main body;
- large currency formatting is display-only;
- Composer cannot mutate canonical decision/completion/thesis/valuation state.

### 11.3 Historical gates

Retain all v1.5.01–v1.5.04 correctness and architecture regressions.

Release verification must include:
- targeted reporting tests;
- architecture contracts;
- correctness regressions;
- full pytest;
- Release Gate;
- final verification at exact final `main` HEAD.

## 12. Migration

No database migration is expected.

Additive Python/data-model fields must have defaults so historical serialized artifacts remain readable.

A v1.5.05 migration note will document:
- new optional report-composition API;
- new expectation-gap result fields;
- new valuation-result fields;
- presentation fingerprint/version changes;
- renderer migration from direct view/template access to `ResearchReportDocument` where applicable.

## 13. Versioning

Target public version:
- display: `v1.5.05`
- SemVer: `1.5.5`

This is a PATCH if implementation remains backward compatible and focuses on professional-output correctness/composition. If implementation requires an incompatible public contract, stop and re-evaluate SemVer before release.

## 14. Acceptance Criteria

v1.5.05 is acceptable only when all of the following hold:

1. `ResearchReportComposer` is a pure one-way consumer of `HumanReadableResearchView`.
2. No second Decision, Completion, Thesis, Funding or Valuation state source exists.
3. A stable Investment Decision Snapshot is produced.
4. Material drivers/risks/gaps are ranked and repeated meaning is deduplicated.
5. Main-body company narrative can express the manufacturing and distributor causal conflicts from synthetic regression fixtures.
6. Hospitality without plugin remains explicitly capability-limited rather than fabricated.
7. Expectation Gap has a structured output and never appears without adequate expectation evidence.
8. Valuation results can carry numeric scenario/range outputs with evidence/assumption lineage and preserve missingness.
9. Monitoring output exposes canonical next event, falsifiers and conviction conditions where available.
10. Lease-heavy presentation safety is enforced without pretending lease-adjusted methodology exists.
11. Full audit provenance remains available in the appendix.
12. Empty/noise sections are omitted.
13. Human number formatting improves readability without changing stored values.
14. Historical v1.5.01–v1.5.04 gates remain green.
15. Full pytest and Release Gate pass on final `main` HEAD.

## 15. Deferred After v1.5.05

Candidates for later versions/plugins:
- full Hospitality Plugin: RevPAR/ADR/OCC, same-store, maturity curve, management/direct mix, unit economics;
- lease-adjusted capital return and valuation methodology;
- richer peer normalization;
- richer consensus/expectation data provider;
- advanced manufacturing capacity/yield/product-mix modeling;
- richer deterministic chart specification and PDF visual regression once the report document contract is stable.

## 16. Architectural Invariants

v1.5.05 must preserve:

```text
Facts / Evidence
    -> canonical Research OS modules
    -> ResearchRunResult
    -> HumanReadableResearchView
    -> ResearchReportComposer
    -> ResearchReportDocument
    -> renderer
```

There must be no reverse dependency from Reporting into research-state calculation and no alternate path from raw evidence directly into the final report narrative.
