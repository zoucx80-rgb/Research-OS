# Research OS v1.5.11 — Semantic Correctness & Comparison-Basis Safety

## Status

Approved design for implementation on `v1.5.11-semantic-correctness`.

Baseline: `Research OS 1.5.10` at `05a3ba99edc02ac93ee9fdf1130485da7e6fa8ab`.
Core API remains `1.0` unless implementation proves an unavoidable public-contract break.

## Problem

v1.5.10 improved research completeness, but a line-by-line validation of a manufacturing field report exposed general semantic correctness defects that can affect any company:

1. directional signal labels are plain strings and can contradict the numeric direction;
2. growth rates with incompatible comparison bases can be compared as if they were homogeneous;
3. `MIXED` evidence is treated as a weakening thesis even when no prior directional thesis exists;
4. waiting-for-confirmation theses can receive falsifiers that do not logically falsify the thesis;
5. missing expectation evidence is represented as `MIXED`, conflating missingness with a directional market signal;
6. evidence quality can be displayed as if it were whole-research confidence;
7. presentation can leak `None`, duplicate semantically equivalent facts, and expose precise model-fitness decimals as if they were objective measurements.

These are system-level issues. Production logic MUST NOT branch on company/security identifiers or hard-code facts for any acceptance company.

## Non-negotiable architecture

The research pipeline remains one-way:

`ResearchContext + ResearchInputs -> canonical runtime artifacts -> ResearchRunResult -> HumanReadableResearchView -> ResearchReportDocument -> Markdown -> HTML -> PDF`

Reporting/presentation MUST NOT repair or recompute canonical research semantics. Presentation may only format, deduplicate already-equivalent display facts, localize, suppress null display values, and select professional display granularity.

Historical v1.5.05–v1.5.10 replay contracts remain frozen and independently reproducible.

## 1. Typed signal contract

Introduce a canonical structured signal representation for thesis assessment.

Required fields:

- `metric`
- `direction`: `POSITIVE | NEGATIVE | NEUTRAL | UNKNOWN`
- `semantic_label`
- `value` when available
- `comparison_basis` when relevant
- `evidence_ids`
- optional `reason_code`

`ThesisSignalAssessment` keeps backward-compatible human string projections if needed, but canonical decision logic MUST use typed signals.

Direction-specific language MUST be derived from sign/direction. A negative margin change must not produce a label containing “改善”. Examples:

- positive margin change -> `毛利率改善`
- negative margin change -> `毛利率下降`
- positive OCF -> `经营现金流为正`
- negative OCF -> `经营现金流为负`

No company-specific wording belongs in the signal service.

## 2. Comparison-basis safety

Cross-metric comparisons require an explicit comparability check.

Define normalized comparison basis metadata sufficient to distinguish at least:

- `YOY_PERIOD` — same-period year-on-year flow comparison;
- `END_VS_BEGIN` — point-in-time stock change over the reporting period;
- `QOQ_PERIOD` — sequential period flow comparison;
- `POINT_IN_TIME` — level at a date;
- `UNKNOWN`.

A cross-metric growth comparison may produce a directional conclusion only when both metrics have compatible basis and economic type.

The system MUST treat stock-change vs flow-YoY comparisons as `NOT_COMPARABLE`. For example, receivables `period-end vs year-start` growth cannot be asserted to be “faster than revenue” when revenue growth is H1 YoY.

When evidence metadata is insufficient, the safe outcome is `NOT_COMPARABLE` / no directional signal, not an inferred risk conclusion.

Aggregated concepts such as trade receivables or net working capital must enter canonical evidence as typed facts/observations with explicit components and basis. Reporting MUST NOT construct them ad hoc from arbitrary raw rows.

## 3. Thesis lifecycle semantics

Separate evidence assessment from lifecycle transition.

Signal assessment states remain evidence-oriented, but thesis lifecycle must support an unresolved state that does not imply deterioration. Add a canonical thesis state equivalent to `UNRESOLVED` / `WAITING_CONFIRMATION` for a newly observed mixed evidence set.

Rules:

- mixed current-period evidence with no prior directional thesis -> unresolved/waiting confirmation;
- `WEAKENING` is allowed only when an existing directional thesis is supplied and new evidence weakens it;
- `FALSIFIED` is allowed only when explicit falsifiers logically contradict the directional thesis;
- unresolved/waiting-confirmation research uses `resolution_conditions`, `conviction_up_conditions`, and `deterioration_conditions`; it MUST NOT invent a “thesis broken” condition merely to satisfy a schema;
- falsifiers remain explicit, auditable, metric-based rules, not hidden thresholds.

Backward-compatible historical thesis replay remains available through versioned modules/classes where necessary.

## 4. Expectation missingness

Extend expectation state semantics to distinguish absence of evidence from directional disagreement.

Current active contract MUST support at least:

- `UNDER_EXPECTED`
- `IN_LINE`
- `OVER_EXPECTED`
- `MIXED`
- `UNKNOWN` (or equivalent explicit insufficient-evidence state)

Rules:

- no PIT-compliant expectation snapshot/consensus -> `UNKNOWN`;
- heterogeneous valid expectation evidence can be `MIXED`;
- Decision Engine MUST treat `UNKNOWN` as missing information, not as a negative/directional market signal;
- presentation label for `UNKNOWN` is `市场预期证据不足` (or equivalent), with explanation that no auditable PIT expectation conclusion is available.

Legacy explicit analyst input `MIXED` remains valid when intentionally supplied and provenance-tagged.

## 5. Evidence confidence semantics

Do not present a 0–1 evidence-quality value as total research confidence.

The active human-readable/reporting layer must distinguish:

- evidence quality/confidence for the evidence actually admitted to the run;
- research completeness/coverage;
- decision confidence only if a separate canonical contract actually supplies it.

A display such as `1.00 / 1.00` must be labeled `已采纳证据质量` rather than unqualified `证据置信度` when it is only evidence quality.

No presentation layer may synthesize a combined confidence score.

## 6. Presentation integrity

The active presenter/composer/renderer must enforce generic presentation safety without changing research meaning:

- no literal Python `None` in investor-facing body;
- duplicate aliases representing the same canonical semantic fact are shown once (e.g. `ocf` and `operating_cash_flow` when values/basis are identical);
- decision timestamps use investor-facing date formatting while audit metadata retains exact timestamps;
- quantitative comparison basis is shown when it materially changes interpretation (`同比`, `期末较期初`, etc.);
- precise valuation-fitness scores remain available in audit/provenance, while the main body displays professional categorical suitability and explanation; no fake precision;
- internal machine IDs remain audit-only under existing rules.

## 7. Correctness gates

Add generic synthetic regression coverage. Tests MUST NOT rely on the identity or facts of the three historical acceptance companies.

Required cases:

1. negative margin change produces negative/downward wording and never “改善”;
2. positive margin change produces improvement wording;
3. stock-change receivables growth vs YoY revenue growth is `NOT_COMPARABLE` and cannot produce `应收增速显著快于收入`;
4. comparable YoY-vs-YoY receivables and revenue metrics may produce a working-capital signal when an explicit rule is satisfied;
5. mixed evidence with no prior thesis produces unresolved/waiting-confirmation, not weakening;
6. an explicit prior directional thesis can transition to weakening under contradictory new evidence;
7. unresolved thesis has no false thesis-broken condition;
8. absent expectation evidence -> `UNKNOWN`, not `MIXED`;
9. explicit provenance-aware analyst `MIXED` remains `MIXED`;
10. report body contains no literal `None`;
11. semantic aliases are deduplicated;
12. precise valuation fitness remains auditable but body wording is categorical;
13. historical v1.5.05–v1.5.10 replay remains green.

## 8. Field validation

After generic regressions pass, run the latest active pipeline against a manufacturing acceptance fixture derived from real primary-source evidence to validate the general system in field conditions.

The field fixture may contain company-specific facts because fixtures are test data. Production source code, generic thresholds, labels, routers, state machines and renderer rules MUST NOT contain the acceptance company/security identifier or bespoke conditions.

Field validation must inspect both machine artifacts and rendered Markdown/HTML/PDF where applicable. Passing keyword presence alone is insufficient; semantic correctness assertions are required.

## 9. Versioning and release discipline

Target release: `Research OS 1.5.11`.

Expected active component version bumps where behavior changes:

- thesis semantic service/models: versioned through release metadata/gate;
- professional research view: `1.6.0` if active presenter contract changes;
- report composer: bump only if document contract changes;
- professional Markdown renderer: bump if investor-facing formatting changes;
- HTML/PDF adapters remain unchanged unless a verified defect requires modification.

`main` release history requirement:

- all development occurs on `v1.5.11-semantic-correctness`;
- intermediate TDD commits are allowed on the feature branch;
- after feature-branch full CI is green, create one squash release commit whose parent is the v1.5.10 stable main commit;
- fast-forward `main` to that one commit;
- run fresh exact-HEAD CI on final `main`;
- verify `v1.5.10 -> v1.5.11` is exactly one commit.

## 10. Non-goals

v1.5.11 does not:

- add company-specific production rules;
- fabricate orders, capacity, certification, consensus, peer or valuation data;
- implement a Hospitality Plugin;
- add trading execution or portfolio management;
- redesign the HTML/PDF engine;
- silently derive trade-receivable aggregates from unrelated presentation rows;
- introduce hidden universal thresholds merely because an acceptance example used one.

## Acceptance definition

v1.5.11 is releasable only when:

- generic semantic correctness tests are green;
- comparison-basis safety is fail-closed;
- thesis lifecycle and expectation missingness are semantically consistent;
- investor-facing output has no `None`, duplicate semantic facts or fake precision violations covered by the contract;
- historical replay gates remain green;
- active field validation passes without production identity branches;
- full pytest and Release Gate pass on the feature branch;
- the final squash commit is the only v1.5.11 commit added to `main`;
- fresh CI passes on that exact final `main` SHA.
