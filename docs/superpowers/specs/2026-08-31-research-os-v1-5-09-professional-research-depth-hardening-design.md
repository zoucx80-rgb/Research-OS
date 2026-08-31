# Research OS v1.5.09 — Professional Research Depth & Field Acceptance Hardening

## Status

Design approved in chat after v1.5.08 field-output review. This specification hardens the already-existing research/reporting pipeline exposed by real-company PDF acceptance. It does not create a second research engine and does not weaken PIT, lineage, missing-value, or single-source-of-truth rules.

Baseline for this design:

- Repository: `zoucx80-rgb/Research-OS`
- Baseline `main` HEAD: `c590507e15c8c386f08d190de84c51c3621a7be4`
- Research OS: `1.5.8`
- Core API: `1.0`

## Problem Statement

v1.5.08 successfully established the professional Markdown -> HTML -> Playwright PDF presentation pipeline, but real-company field acceptance exposed a gap between presentation completeness and research completeness.

The current field acceptance contract can pass when:

- required section ids exist;
- a small set of body terms exists;
- raw evidence/plugin/internal identifiers are kept out of the body;
- the business model is correct.

That is insufficient to prove that a final investment-research report is professionally complete. A report may therefore be structurally valid yet omit core absolute financial facts, company-specific operating conflicts, expectation evidence, executable valuation outputs, and sufficiently concrete monitoring conditions.

The same review exposed body-level presentation defects:

- technical/localization fallback messages may leak into material risks;
- English strategy questions may appear in a Chinese report;
- confidence values can render without a scale explanation;
- raw currency values and model-fitness decimals can be shown with poor human readability;
- negative margin change can be verbalized ambiguously;
- research gaps can dominate pages without enough decision-useful operating content.

## Required Data Flow

The one-way architecture remains mandatory:

```text
ResearchContext + ResearchInputs
    -> canonical runtime modules
    -> ResearchRunResult
    -> HumanReadableResearchView
    -> ResearchReportComposer
    -> ResearchReportDocument
    -> Markdown
    -> HTML
    -> PDF
```

Presentation/reporting layers may select, group, rank, deduplicate, localize and format canonical artifacts. They may not fetch external data, read raw company evidence directly, manufacture missing facts, calculate new economic states, or change canonical decisions.

## Scope

### 1. Canonical Financial Fact Snapshot

Add a canonical, lineage-preserving financial fact artifact to the runtime so the report can show decision-useful absolute values without reading raw evidence from Reporting.

The artifact should be produced from `ResearchContext.facts` after PIT/lineage validation and include only facts already present in the canonical context. It must preserve value, unit/semantic type, period identity when available, and evidence ids.

Initial supported fact families:

- revenue;
- revenue growth;
- attributable net profit;
- gross profit / gross margin / margin change;
- operating cash flow;
- capex cash;
- accounts receivable begin/end/change or growth;
- inventory begin/end/change or growth;
- debt begin/end/change when supplied;
- PPE/fixed assets begin/end;
- period start/end/type/days.

No missing value may be inferred. Derived changes may only appear when they already exist as canonical facts/calculated evidence, or when a dedicated runtime analytical artifact explicitly performs that calculation with lineage and formula version. Reporting itself must not derive them.

Expected artifact identity: `financial.fact_snapshot` (exact model/file names may follow existing repository conventions during implementation).

### 2. Human-Readable Core Financial Table

`HumanReadableResearchView` should project the canonical financial fact snapshot into a compact professional table suitable for first-pass investment review.

For each available metric the view should retain:

- metric label;
- current value;
- comparison value when supplied;
- change/growth when supplied;
- period/comparison semantics;
- evidence ids for appendix traceability;
- human-readable interpretation label only when the canonical signal is unambiguous.

Examples of acceptable display semantics:

- `2026H1 营收 20.53亿元，同比增长 13.04%`;
- `应收账款 12.21亿元 -> 19.57亿元，期末较年初 +60.28%`;
- `毛利率同比下降 2.66pct`.

Reporting must not convert a negative `margin_change` into wording such as “利润率改善”.

### 3. Company-Specific Operating Evidence Coverage

Field acceptance fixtures may include real, PIT-compliant operating facts beyond generic accounting lines. The runtime/reporting path must carry these facts only through supported strategy/KPI/driver artifacts; the report may not bypass the canonical pipeline.

For manufacturing acceptance, examples of acceptable evidence families include:

- product/segment revenue and margin mix;
- order/backlog/customer acceptance evidence when disclosed;
- capacity/utilization/yield/product-mix evidence when disclosed;
- capex, construction-in-progress and transfer-to-fixed-assets evidence;
- customer concentration or collection structure when material.

For distributor acceptance, examples include:

- AR/inventory/payables changes;
- debt/factoring/financing cash flow;
- financing cost and impairment burden;
- product/category mix when disclosed.

For hospitality acceptance, examples include:

- RevPAR/ADR/OCC;
- managed vs direct-operated mix;
- opened/pipeline hotel/room counts;
- lease/ROU/liability exposure.

Absence remains a visible evidence/capability gap.

### 4. Professional Research Depth Gate

Extend field acceptance so a real-company run reports two distinct statuses:

1. `presentation_status` — structural/rendering/ID-leakage/PDF pipeline acceptance;
2. `research_depth_status` — professional investment-research completeness.

A final field-acceptance result is release-grade only when both pass, unless a fixture explicitly declares that it is testing an intentionally incomplete evidence state.

The depth gate must support deterministic requirements such as:

- required canonical financial fact keys;
- minimum number of material drivers;
- minimum number of company-specific evidence-backed operating facts;
- minimum thesis/anti-thesis/falsifier coverage;
- at least one explicit investment conflict/contradiction when the supplied evidence is mixed;
- minimum monitoring coverage;
- expectation completeness state;
- valuation completeness state;
- maximum allowed untranslated/internal-fallback text in the body: zero;
- required body language/locale for locale-controlled reports;
- required provenance coverage for material body claims.

The gate must never invent evidence to satisfy itself. It should fail or mark incomplete when required research inputs are absent.

### 5. Expectation and Valuation Completeness Policy

A report with no auditable consensus snapshot or no executable valuation evidence must continue to say so. The fix is not to fabricate values.

Instead:

- `research_depth_status` should become `INCOMPLETE` when the fixture requires a professional complete report but auditable expectation or valuation evidence is absent;
- intentionally incomplete fixtures may declare expected incompleteness and test the limitation path;
- real-company release acceptance fixtures intended to prove full-report readiness should provide PIT-compliant expectation and valuation inputs when available.

Valuation output should prefer interpretable values/ranges over raw fitness decimals. Fitness scores may remain available in methodology detail or appendix, with rounded human display in the body.

### 6. Material Risk Hygiene

`InvestmentDecisionSnapshot.material_risks` and related first-screen blocks must exclude implementation diagnostics, localization fallbacks, unmapped semantic codes, plugin identifiers and other technical/reporting defects.

If a semantic mapping is missing:

- record it as a presentation diagnostic/audit limitation;
- do not elevate it into an economic risk;
- test that no fallback text can appear under “关键风险”.

### 7. Chinese Localization Contract

Chinese professional reports must not display raw English strategy questions in normal body sections.

Use stable semantic identities or deterministic translation mappings rather than brittle free-text replacement. If a question has no Chinese mapping:

- render a localized capability-gap category/label;
- preserve the raw question only in audit metadata if needed;
- mark the missing mapping as a presentation diagnostic.

Do not mutate plugin machine identities merely to satisfy display localization.

### 8. Human Number Formatting

Body-level rendering rules:

- CNY absolute values: compact to `亿元` / `万元` where appropriate;
- percentages: professional precision, generally 2 decimals unless a contract requires otherwise;
- percentage-point changes: use `pct`/`个百分点` semantics, not `%` when the underlying fact is a margin delta;
- days: reasonable 1–2 decimal precision;
- multiples and model fitness: avoid six-decimal display in the main body;
- raw machine values remain unchanged in canonical artifacts and audit output.

### 9. Evidence Confidence Display

Do not render an unexplained scalar such as `证据置信度 1`.

The human projection must include either:

- a normalized label plus scale, e.g. `高（1.00 / 1.00）`;
- or a documented categorical label generated from an existing canonical confidence contract.

No new investment state may be inferred from formatting.

### 10. Composer Density and Section Policy

The Composer should prioritize decision-useful content before research-process metadata.

Preferred main-body order:

1. Investment Decision Snapshot;
2. Core Financial Changes;
3. Core Investment Conflict / Causal Bridge;
4. Business / Segment / Operating Evidence;
5. Capital Efficiency & Funding Loop;
6. Thesis / Anti-Thesis / Falsifiers;
7. Expectations / Forecast;
8. Valuation / Scenarios;
9. Monitoring;
10. Material Limitations / Research Gaps.

State provenance, implementation diagnostics, detailed module status, raw ids and method fingerprints belong in the appendix unless specifically needed to explain a material limitation.

Empty sections remain omitted. Sparse gap sections should not create visually dominant blank pages when preceding content can flow normally.

### 11. Real-Company Field Fixtures

Upgrade the existing v1.5.08 three-company field fixtures into v1.5.09 depth-regression fixtures without making company facts part of methodology truth.

The fixtures remain test data only and must preserve original-source provenance and `publish_ts <= decision_ts`.

At minimum they should exercise:

- manufacturing: product/margin/cash/AR/capex conflict;
- distributor: growth -> AR/inventory -> funding -> financing cost/impairment -> cash/valuation-fitness conflict;
- lease-heavy hospitality: operating KPI improvement vs ADR/lease-capital constraints and plugin/capability limitations.

Do not hard-code company names or values into reusable runtime/composer logic.

## Compatibility

- Core API remains `1.0` unless implementation proves an incompatible public contract unavoidable.
- New runtime/view/document fields should be additive and defaultable.
- Existing v1.5.08 snapshots and report documents remain readable where currently supported.
- Existing one-way reporting boundary remains enforced.
- No database migration is expected.
- No web/data retrieval is added to Reporting or Presentation.

## Non-Goals

Not part of this fix:

- full Hospitality Plugin implementation;
- new external consensus provider;
- new market-price provider;
- lease-adjusted DCF/ROIC engine;
- charting subsystem;
- LLM-generated company facts;
- automatic trading signals;
- redesign of the v1.5.08 Playwright PDF backend unless a concrete rendering defect is found by regression testing.

## TDD / Regression Requirements

Implementation must begin with failing tests for the exposed defects.

Required regressions:

1. Core financial absolute values reach `ResearchReportDocument` through canonical runtime/view artifacts, never raw-evidence access from Reporting.
2. Missing financial facts remain missing.
3. Negative margin change renders as deterioration, never “改善”.
4. CNY values compact in the body while machine values remain unchanged.
5. Evidence confidence includes a human scale/label.
6. Technical/localization fallback cannot appear in first-screen material risks.
7. Chinese body contains no raw English strategy question text.
8. Research-depth acceptance fails/incompletes when required core facts are absent even if all section ids exist.
9. Research-depth acceptance fails/incompletes when full-report fixtures lack required expectation/valuation evidence.
10. Intentionally incomplete fixtures can assert expected incompleteness without being mistaken for a full professional PASS.
11. Manufacturing depth fixture contains evidence-backed product/margin/cash/AR/capex conflict.
12. Distributor depth fixture preserves growth -> working capital -> funding -> financing burden -> cash/valuation causal ordering.
13. Lease-heavy hospitality fixture keeps lease limitation visible and does not infer “light asset” solely from low PPE.
14. Main body keeps raw evidence ids/plugin ids/internal reason-code fields out; appendix retains traceability.
15. Presentation pipeline hash-chain and Playwright PDF tests remain green.

Final verification:

- targeted runtime/reporting/presentation tests;
- field acceptance tests for all three company archetypes;
- architecture boundary tests;
- PIT/no-time-travel tests;
- full `pytest`;
- release gate;
- verify final remote `main` HEAD.

## Versioning

This is intended as a backward-compatible correctness/completeness hardening release:

- Research OS target: `1.5.9`;
- Core API target: `1.0`;
- bump only component versions whose public behavior changes.

If implementation requires an incompatible public data contract, stop and re-evaluate SemVer before release.

## Acceptance Criteria

The change is complete only when:

1. a professional report can show core absolute financial facts from canonical artifacts;
2. Reporting still cannot read raw company evidence or perform new economic calculations;
3. real-company field acceptance distinguishes presentation PASS from research-depth completeness;
4. structural section presence alone can no longer produce a full professional PASS;
5. technical/localization fallbacks cannot surface as economic risks;
6. Chinese reports contain no raw English strategy questions in the body;
7. number/confidence/margin-change semantics are investor-readable;
8. three archetype field fixtures prove materially deeper, company-specific research output while reusable logic remains company-agnostic;
9. missing expectation/valuation evidence remains explicit and blocks full-depth PASS where required;
10. PIT and evidence lineage remain intact;
11. historical v1.5.08 output contracts remain compatible where promised;
12. all targeted, full-suite and release-gate checks pass on the final `main` HEAD.
