# Research OS v1.5.10 — Professional Research Completeness & Continuous Validation

## Status

Approved in chat on 2026-08-31. Baseline: `zoucx80-rgb/Research-OS@a3e82b3cc80b871b559ac9f5cd29e18e97b8e98d` (Research OS 1.5.9, Core API 1.0).

Development is isolated on `v1.5.10-professional-research-completeness`. Intermediate commits may exist on the temporary branch, but `main` MUST receive exactly one squashed v1.5.10 release commit. Historical releases are not rewritten.

## Goal

Close the remaining gap between a structurally complete report and a decision-useful professional research process by adding typed, PIT-safe research-completeness artifacts and continuous-validation artifacts. Preserve the single canonical flow:

`ResearchContext/ResearchInputs -> canonical runtime -> ResearchRunResult -> HumanReadableResearchView -> ResearchReportDocument -> Markdown -> HTML -> PDF`.

Reporting and presentation may format existing canonical artifacts only. They must never retrieve external data, manufacture missing observations, invent thresholds, or recompute investment states.

## Scope

### 1. Operating Evidence Snapshot

Add an immutable canonical artifact for disclosed operating evidence that does not fit generic financial facts. Supported families are intentionally generic:

- order/backlog/contract-liability observations;
- capacity/utilization/yield observations;
- certification/customer-acceptance milestones;
- segment/product revenue, growth and margin observations;
- subsidiary revenue/profit/loss observations;
- capex/CIP/transfer-to-fixed-assets observations;
- customer concentration and receivable-aging observations.

Each observation must carry a stable metric/category identity, value or text, period/as-of, source/evidence ids and optional entity/segment label. Missing observations remain missing. No company name or company-specific threshold belongs in production logic.

### 2. Financial Time Series

Add typed `FinancialTimeSeries`/point contracts capable of carrying up to multi-year quarterly/annual observations already supplied to the run. The series layer must preserve period identity and evidence lineage and must not interpolate missing quarters.

The human view/report should expose deterministic trend tables suitable for later chart rendering. Actual chart rendering is deferred.

### 3. Cash-Flow Quality Bridge

Add an explicit analytical artifact for cash-flow quality using only supplied/canonical inputs:

- net profit;
- operating cash flow;
- working-capital contribution when supplied;
- non-cash/other adjustment when supplied;
- capex cash;
- simplified FCF;
- methodology label explaining simplified FCF is not FCFF.

The bridge may perform arithmetic only when all required source inputs are explicitly present and must retain formula version and lineage. It may never silently infer a working-capital split from a single OCF number.

### 4. Consensus Distribution & Expectation Dispersion

Extend the existing PIT `ConsensusVintage` model with an additive multi-source distribution contract. A distribution may summarize source-count, low/median/high, dispersion and source identities for a metric/forecast period from explicitly supplied vintages.

The service must reject post-decision vintages and must not treat a single-source estimate as broad consensus. Expectation-gap logic continues to use auditable PIT inputs.

### 5. Peer/Product-Line Comparison

Extend peer contracts so comparisons can be scoped by product/segment, peer role, period and metric definition. Normalization must continue to fail closed on incompatible accounting/period/business-model definitions.

The report may show product-line or segment comparisons only when normalized comparable observations are supplied. International peers are supported as ordinary peer records; no external retrieval occurs inside Core.

### 6. Sensitivity & Scenario Assumptions

Add typed, explicit assumptions for scenario/sensitivity analysis. A sensitivity result must identify:

- driver identity;
- base assumption;
- shock definition;
- affected metric;
- result or range;
- formula/model version;
- evidence/assumption ids.

Review examples such as nickel ±10%, step-down pricing, utilization, depreciation and growth are allowed as fixture/user assumptions, never global hard-coded rules. Probabilities are analyst assumptions and must be labeled as such.

### 7. Monitoring Rules & Event Calendar

Add typed `MonitoringRule` and `VerificationEvent`/calendar contracts. Rules carry metric, operator, threshold, period/frequency, rationale, source type and provenance. Thresholds are configurable run inputs, not methodology constants.

The event calendar supports a rolling horizon and known/pending verification events such as reporting dates, certification reviews, capacity milestones, major-order disclosures or consensus refreshes. Unknown dates remain undated/pending rather than fabricated.

### 8. Continuous Validation / Prior-Run Review

Build on existing forecast error, calibration and postmortem primitives to create a typed prior-run review artifact containing:

- prior thesis/driver expectation;
- actual observed result when available;
- hit/miss/unknown status;
- forecast error records;
- expectation error/consensus revision when supplied;
- thesis-state changes;
- process-change candidates.

No retrospective score is produced when the previous prediction or current actual is absent.

### 9. Methodology Disclosure

Expose a report-safe methodology disclosure generated from repository contracts, not invented thresholds. It must explain:

- Research OS one-way architecture;
- distinction among facts/calculations/statistical evidence/assumptions;
- PIT and lineage rules;
- state provenance;
- what a monitoring threshold means;
- simplified FCF vs FCFF;
- why incomplete evidence produces an incomplete research-depth state.

Do not publish fictitious metric weights or threshold rules that do not exist in code.

### 10. Report Composition

Add decision-useful sections when corresponding artifacts exist:

1. Executive Summary / three positive and three negative or limiting signals when supplied by canonical view;
2. Core Financial Trend / time series;
3. Operating Evidence / segments/subsidiaries/capacity/orders/certification;
4. Cash-Flow Quality;
5. Peer/Product-Line Comparison;
6. Consensus Dispersion;
7. Sensitivity/Scenario;
8. Monitoring Rules & 12-month verification calendar;
9. Prior-Run Review;
10. Methodology & Glossary summary.

Empty sections are omitted. Raw ids and technical diagnostics stay in the audit appendix.

## Research Completeness Gate v1.5.10

The existing `presentation_status` and `research_depth_status` remain. Add deterministic coverage diagnostics for:

- time-series coverage;
- operating-evidence coverage;
- cash-flow decomposition coverage;
- consensus breadth/dispersion coverage;
- peer-comparison coverage;
- sensitivity/scenario coverage;
- monitoring/event coverage;
- prior-run validation coverage;
- methodology disclosure presence.

Coverage may be `PASS`, `INCOMPLETE`, or `NOT_APPLICABLE`. A release-grade fixture must declare which dimensions are required. The gate fails closed when a required dimension is missing; it never creates data to pass itself.

## Steel-Research Acceptance Pattern

The manufacturing regression should be capable of expressing, when supplied by PIT evidence:

- product revenue/margin divergence;
- order/capacity/certification evidence or explicit gaps;
- subsidiary profit divergence;
- 5-year/quarterly financial trend without interpolation;
- OCF working-capital bridge when inputs exist;
- receivable aging;
- product-line peers;
- multi-source consensus range/dispersion;
- explicit raw-material/pricing/utilization/depreciation sensitivity assumptions;
- configurable monitoring thresholds;
- forward verification-event calendar;
- prior-run prediction review.

These are archetype capabilities, not company-specific production rules.

## Non-Goals / Deferred

- no automatic web/broker/expert/interview retrieval in Core;
- no claim that expert interviews, order surveys, patent databases or tender databases were performed unless evidence is actually supplied;
- no hard-coded universal risk thresholds from the review examples;
- no Hospitality Plugin in this release;
- no DCF/forecast engine rewrite;
- no dashboard/web app;
- no chart rendering engine in v1.5.10; only chart-ready typed datasets;
- no autonomous trading or portfolio execution.

## Compatibility

- Research OS target: `1.5.10`;
- Core API remains `1.0`;
- new fields/contracts are additive and defaultable;
- v1.5.09 report documents and historical release tests remain replayable;
- no database migration is expected;
- presenter/composer/renderer component versions change only if their behavior actually changes.

## Release Acceptance

`READY: v1.5.10 stable` requires fresh evidence on the final squashed `main` commit:

- new unit/integration/regression tests pass;
- historical release contracts pass;
- full pytest passes;
- Release Gate passes;
- v1.5.09 field acceptance remains green;
- v1.5.10 manufacturing completeness fixture proves the new artifact chain and fail-close missingness;
- README, CHANGELOG, migration note and stock-research protocol are synchronized;
- no company-specific facts/thresholds appear in reusable production logic;
- `main` contains exactly one new commit relative to the v1.5.09 baseline for this release.
