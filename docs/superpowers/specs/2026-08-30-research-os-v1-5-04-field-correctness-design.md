# Research OS v1.5.04 Field-Correctness Design

## Problem Statement

Research OS v1.5.03 was exercised against three companies at one frozen baseline and one point in time:

- repository: `zoucx80-rgb/Research-OS` (`1350382205`)
- branch: `main`
- frozen commit: `d7a6d041ae23f2464b4aeff45d4d98e5d00f0b01`
- Research OS: display `v1.5.03`, SemVer `1.5.3`, Core API `1.0`
- decision timestamp: `2026-08-30T00:00:00Z`
- companies, in order: `300034.SZ`, `001287.SZ`, `301073.SZ`

The baseline correctly preserves PIT lineage, routes the three business models, isolates primary-industry execution, keeps unsupported Hospitality coverage incomplete, and exposes many professional evidence gaps. The field test also found correctness defects that can produce false validation failure, narrative overreach, false dilution language, incomparable incremental ratios, or an overly permissive PE route. The full professional view additionally omits material artifacts that already exist in the canonical result.

v1.5.04 is a PATCH release. It corrects those failures without adding a second router, completion policy, decision engine, presentation state, or company-specific rule.

## Evidence from the Three-Company Field Test

### Steel / advanced manufacturing — `300034.SZ`

The 2026 interim report published on 2026-08-25 supported manufacturing classification, period-aware H1 KPIs, fact-specific drivers, mixed thesis signals, and explicit capability gaps for orders/backlog, capacity/utilization/yield, and raw-material/qualification constraints. Revenue grew 13.04%, gross margin declined, receivables grew materially faster than revenue, and operating cash flow improved. The thesis correctly remained mixed/weakening.

The same valid filing failed `Financial Sanity` because the reported 13.04% YoY value is rounded to two decimal percentage points while `check_yoy` requires near-exact equality. The professional view also omitted the canonical financial-sanity, capital-efficiency, forecast-discipline and temporal-event artifacts.

### Electronic-component distribution — `001287.SZ`

The 2026 interim report supported distributor classification and period-aware DSO/DIO/DPO/CCC metrics. It simultaneously showed very high revenue/profit growth, negative operating cash flow, large receivables/inventory growth, short-debt expansion and a debt-funded Funding Loop. Thin consensus correctly remained low quality and pre-event.

Four failures appeared:

1. rounded 164.19% reported YoY growth failed `Financial Sanity`;
2. the thesis engine emitted an `active` “Growth converts to cash” thesis despite negative `ocf`, because its falsifier looked for `cfo` only;
3. positive change in reported book equity was labelled `EQUITY_DILUTION`, although retained earnings are not equity issuance;
4. `delta_nwc` calculated from year-end to H1 and `delta_revenue` calculated H1-over-H1 were accepted in one incremental ratio without comparable-period metadata.

The current valuation router can also promote PE from analyst-supplied fitness scores even when the canonical distributor Funding Loop is debt-funded with negative OCF.

### Hospitality — `301073.SZ`

The 2026 interim report correctly routed the company to `hospitality`. Material right-of-use assets and lease liabilities correctly suppressed the low-owned-PPE distributor heuristic. With no compatible Hospitality Plugin, the runtime produced an `industry_strategy` Coverage Gap, retained a coverage-limited generic graph, generated no specialized thesis/claim, and left completion incomplete.

This is correct fail-closed behavior. Missing RevPAR decomposition, ADR, OCC, same-store, maturity-curve, direct/managed mix, unit economics and lease-adjusted returns are plugin/data/methodology gaps rather than reasons to put hotel logic in Core. The rounded 1.41% reported revenue growth nevertheless reproduced the same cross-industry financial-sanity false failure.

## Cross-Case Review

### What worked

- Repository preflight, PIT filtering, lineage and reproducible snapshots remained canonical.
- Router classifications were correct for manufacturing, distribution and lease-heavy hospitality.
- Primary-industry plugin isolation prevented cross-industry KPI contamination.
- Driver lineage was fact-specific for supported drivers.
- Manufacturing professional questions distinguished capability gaps from evidence gaps.
- Hospitality coverage failed closed: a generic graph did not create a specialized thesis.
- Event-relative consensus quality exposed thin or pre-event consensus.
- Funding Loop preserved missing factoring/receivable-transfer evidence as missing rather than economic zero.
- `ResearchCompletionGate` remained the only completion authority.

### Core defects exposed across cases

- Published rounded YoY values can fail financial validation in every industry.
- Falsifier metric aliases are not canonical, so evidence can exist without triggering a falsifier.
- Delta-period comparability is not enforced before incremental capital/funding ratios.
- Material canonical artifacts are absent from the complete human-readable projection.

### Distributor-specific but reusable methodology defects

- Book-equity change is conflated with external equity financing and dilution.
- PE can remain primary under a canonical debt-funded, negative-OCF Funding Loop.

### Plugin, methodology and data gaps

- Manufacturing orders/backlog, customer acceptance, utilization, yield, qualification and capex productivity need an advanced Manufacturing Plugin and better primary data.
- Hospitality needs a dedicated plugin and hotel operating dataset.
- Lease-adjusted ROIC/DCF and richer scenario valuation need a methodology extension.
- Forecast promotion, benchmark evidence, consensus dispersion and structured Evidence Quality need broader future work.

## Field-Test Issue Log

| Issue ID | Company | Stage | Type | Observed behavior | Expected behavior | Severity | Cross-industry | Core change | Alternative layer | Root cause | Direction |
|---|---|---|---|---|---|---|---|---|---|---|---|
| FIN-ROUND-001 | all three | Financial Sanity | Financial Semantics | valid two-decimal reported YoY values fail | ordinary filing rounding passes; material errors fail | P1 | yes | yes | none | equality tolerance ignores display precision | use half-basis-point absolute tolerance |
| THESIS-OCF-002 | `001287.SZ` | Thesis/Falsifiers | Thesis | negative `ocf` leaves cash thesis active | canonical OCF alias triggers and weakens/falsifies thesis | P1 | yes | yes | none | emitted `cfo` key differs from evidence `ocf` | canonical alias resolver and `ocf` emission |
| THESIS-LINEAGE-003 | `001287.SZ` | Thesis lineage | Thesis | financing thesis cites the entire evidence set | thesis cites supporting driver/signal evidence only | P2 | yes | yes | none | all evidence used as fallback support | union fact-specific supporting-driver evidence |
| FUND-EQUITY-004 | `001287.SZ` | Funding Loop | Financial Semantics | positive book equity change becomes dilution | only explicit external equity financing/dilution drives those states | P1 | reusable | yes | Distributor Pack | ambiguous `delta_equity` semantics | separate reported equity change, external financing and dilution |
| PERIOD-DELTA-005 | `001287.SZ` | Capital/Funding/KPI | Financial Semantics | incomparable deltas form ratios | missing/mismatched bases preserve a missing metric and diagnostic | P1 | yes | yes | plugins consume contract | delta values carry no comparison basis | shared comparison-basis contract |
| VAL-PE-006 | `001287.SZ` | Valuation Fitness | Valuation | PE can be primary under debt-funded negative OCF | canonical funding risk prevents PE from primary status | P1 | reusable | yes | methodology | router ignores Funding Loop state | pass canonical funding context and penalize PE |
| VIEW-MATERIAL-007 | all three | HumanReadableResearchView | Reporting | material existing artifacts are omitted | one-way view exposes them without recalculation | P2 | yes | yes | reporting | presenter contract is incomplete | additive read-only projections |
| MFG-CAP-008 | `300034.SZ` | Professional Questions | Industry Plugin | questions exist but specialist capabilities do not | explicit capability gaps remain visible | P3 | no | no | Manufacturing Plugin/data | v1.5.03 intentionally has generic manufacturing pack | defer |
| HOTEL-CAP-009 | `301073.SZ` | Strategy/Questions | Industry Plugin | no hotel KPI/question pack | coverage gap remains explicit without fake thesis | P3 | no | no | Hospitality Plugin/data | plugin intentionally absent | defer |
| STATE-LINEAGE-010 | all three | State Provenance | State Provenance | caller can label a state `derived` without runtime lineage validation | derived-state lineage is validated | P2 | yes | later | methodology/runtime | provenance is descriptive, not validated | v1.5.05 candidate |
| FORECAST-011 | all three | Forecast | Forecast | production chain has only `NOT_APPLICABLE` placeholder | promoted models carry benchmark evidence | P3 | yes | no in patch | Forecast methodology | no promoted forecast methodology | v1.5.05+ |
| EVIDENCE-VIEW-012 | all three | Evidence Quality | Reporting/Evidence | no structured quality/gap summary beyond existing coverage artifacts | canonical evidence-quality artifact feeds view | P2 | yes | later | evidence methodology | no canonical quality aggregation | v1.5.05 candidate |

## Gap Prioritization

### v1.5.04 — must do

1. **Rounded YoY validation** (`FIN-ROUND-001`) — prevents false hard-gate failure in all three cases.
2. **Canonical OCF falsification and thesis-specific lineage** (`THESIS-OCF-002`, `THESIS-LINEAGE-003`) — prevents an active cash-quality thesis from contradicting primary evidence.
3. **Explicit equity-financing semantics** (`FUND-EQUITY-004`) — prevents retained earnings/book-equity change from being presented as dilution.
4. **Delta comparison-basis contract** (`PERIOD-DELTA-005`) — prevents incomparable interim deltas from becoming professional-looking ratios.
5. **Funding-aware PE fitness guard** (`VAL-PE-006`) — prevents PE from primary status under the existing severe distributor Funding Loop signal.
6. **Material-artifact projection** (`VIEW-MATERIAL-007`) — exposes existing financial-sanity, capital-efficiency, forecast-discipline and next-event artifacts from the same canonical result.

### v1.5.05 candidates

- validate evidence IDs and derivation methods for `StateInput(source="derived")`;
- create one canonical Evidence Quality / Evidence Gap artifact;
- structure consensus dispersion and source composition;
- promote forecast/benchmark evidence into the production chain;
- strengthen valuation execution with explicit scenario results and calculation checks;
- add canonical conviction-up and thesis-broken monitoring conditions where they do not duplicate falsifiers/events.

### v1.5.06+ / future plugins

- Hospitality Plugin and hotel operating dataset;
- lease-adjusted ROIC, EV/EBITDA and DCF methodology;
- advanced Manufacturing Plugin for orders, acceptance, capacity, yield and qualification;
- richer Knowledge Providers, peer normalization and expectation datasets.

## Design Principles

- PATCH-first, correctness-first and evidence-first.
- Core API remains `1.0`.
- No company IDs, company names or company-specific thresholds in production code.
- No second Router, Completion Gate, Decision Engine or presentation state.
- Missing or ambiguous semantics remain missing; `None` is not zero.
- Existing canonical artifacts are projected, not recomputed, by reporting.
- Historical snapshots and release tags remain immutable.
- New fields are additive; behavior becomes more conservative only where v1.5.03 could assert an invalid result.

## Scope and Contracts

### 1. Rounded YoY financial validation

`FinancialSanityValidator.check_yoy` accepts ordinary report rounding to two decimal percentage points with `abs_tol=0.00005`. A value outside that boundary still fails. Gross-profit, gross-margin, scale and other validation behavior is unchanged.

### 2. Canonical falsifier metrics and thesis lineage

`ThesisService` resolves `cfo`, `ocf` and `operating_cash_flow` to the same canonical operating-cash-flow value when evaluating existing or newly emitted falsifiers. New built-in theses emit `ocf` in falsifiers and verification metrics. Financing-thesis support is the union of evidence IDs attached to the working-capital/financing drivers it actually uses, not the entire PIT evidence set.

Negative OCF triggers at least `weakening`; a second triggered falsifier may produce `falsified` under the existing policy. No separate thesis state is introduced.

### 3. Delta comparison-basis contract

The shared period helper consumes optional facts named `<fact>_comparison_basis`. Ratios between delta facts are valid only when both bases are present, non-empty and equal.

The contract applies to:

- `delta_nwc / delta_revenue` in Capital Efficiency and Distributor Pack;
- `delta_debt / delta_nwc` in Funding Loop and Distributor Pack;
- `(delta_debt + external_equity_financing) / delta_nwc` in Distributor Pack.

Missing bases produce `COMPARISON_BASIS_REQUIRED`; unequal bases produce `COMPARISON_BASIS_MISMATCH`. The affected metric remains missing. Funding Loop may still classify from another independently comparable pair; it exposes additive comparison-basis status/errors for audit.

### 4. Equity financing and dilution semantics

The free-form fact contract distinguishes:

- `delta_equity`: reported book-equity change, informational only;
- `external_equity_financing`: explicit external equity financing during the comparison basis;
- `equity_dilution`: explicit boolean/evidenced dilution flag.

`incremental_equity` means explicit external equity financing. `reported_equity_change` is additive output metadata. `equity_funded`, external-funding ratios and self-funded classification consume `external_equity_financing`. `EQUITY_DILUTION` appears only when `equity_dilution is True`.

The Distributor Pack moves its external-funding metric dependency from `delta_equity` to `external_equity_financing`. Its pack version advances; the built-in distributor plugin version advances without changing API `1.0`.

### 5. Funding-aware valuation fitness

`ValuationContext` receives optional canonical `funding_state` and `funding_reason_codes`. `ValuationModule` reads the already-produced `capital.funding_loop` artifact and passes it to the existing `ValuationRouter`.

For the reusable condition:

```text
business_model == distributor
and funding_state == debt_funded
and NEGATIVE_OCF is present
and model == pe
```

the PE fitness score receives a `0.25` safety multiplier and the routed model records `CASH_FUNDING_RISK_PE_PENALTY`. This makes a normally high generic PE score ineligible for the `PRIMARY` threshold while allowing other models to route through the existing policy. The existing severe Funding Loop condition remains the source; no new risk engine is created.

### 6. Material artifacts in the professional view

`ResearchViewPresenter` adds read-only fields for:

- Financial Sanity validation status and scope;
- Capital Efficiency (`roic`, `incremental_roic`, `iwcr`, comparison limitation);
- Forecast Discipline status/reason;
- the canonical next-verification event.

`TemporalModule` emits its input as `temporal.event` alongside its existing validation result. Presentation labels process-validation state explicitly so `PASS` cannot be mistaken for a healthy economic condition. The presentation fingerprint advances to `professional-research-view@1.2.0`.

## Data Model Changes

Additive fields only:

- `CapitalEfficiencyResult.iwcr_reason_code`;
- `FundingLoopResult.reported_equity_change`;
- `FundingLoopResult.comparison_basis_status`;
- `FundingLoopResult.comparison_basis_errors`;
- `RoutedModel.reason_codes`;
- `ValuationContext.funding_state` and `funding_reason_codes`;
- the four human-readable view projections described above.

No SQL/Alembic migration is required. Facts remain carried by the existing lineage-aware fact/evidence boundary.

## Module and Plugin Changes

- `FinancialSanityModule`: behavior changes only through validator tolerance.
- `CapitalEfficiencyModule`: consumes comparison-safe IWCR result.
- `FundingLoopModule`: emits the existing Funding Loop result with additive audit metadata.
- `ValuationModule`: adds an existing-artifact dependency and passes canonical funding context.
- `TemporalModule`: publishes `temporal.event` without changing validation authority.
- `DistributorPack`: comparison-safe incremental/external ratios and explicit equity-financing input.
- `DistributorIndustryPlugin`: version bump for changed KPI semantics.
- `ManufacturingIndustryPlugin`: unchanged.

## Presentation Changes

The professional view remains:

```text
ResearchRunResult -> ResearchViewPresenter -> HumanReadableResearchView
```

It does not infer company economics or completion. All new fields read existing canonical artifacts/module results. Raw codes remain secondary metadata behind Chinese labels and explanations.

## Non-Goals

- no Hospitality Plugin;
- no hotel-specific rules in Core;
- no lease-adjusted valuation or ROIC framework;
- no advanced Manufacturing Plugin;
- no forecast subsystem rewrite;
- no Evidence Quality aggregation engine;
- no consensus dispersion dataset;
- no new decision or completion state;
- no database migration;
- no company-specific regression fixture in production logic.

## Migration and Compatibility

- SemVer advances from `1.5.3` to `1.5.4`; display version is `v1.5.04`.
- `CORE_API_VERSION` remains `1.0`.
- Existing models deserialize because new fields have defaults.
- Callers that want delta ratios/states must now provide explicit matching comparison-basis facts.
- Callers that want equity-funded/self-funded classification must provide `external_equity_financing`, including an evidenced zero where zero is known.
- `delta_equity` remains accepted and is preserved as reported equity change, but it no longer implies financing or dilution.
- Old snapshots remain interpretable with their recorded component versions.

## Risks and Mitigations

- **Conservative missing states increase:** intentional; migration documentation lists new basis/equity inputs.
- **PE guard over-penalizes a valid distributor:** limited to the existing severe conjunction of debt-funded state and negative OCF; it changes fitness, not decision state.
- **Presentation drift:** release tests assert the presenter copies canonical values/statuses without recomputation.
- **Metric alias regression:** compatibility tests retain `cfo` inputs while new output standardizes on `ocf`.
- **Version drift:** release contract checks every public version surface and component fingerprint.

## Acceptance Criteria

1. All three reported rounded YoY fixtures pass, while an error beyond the display-rounding boundary fails.
2. A distributor with negative `ocf` cannot retain an untriggered active cash-conversion thesis; the falsifier is canonical and traceable.
3. Financing-thesis supporting evidence excludes unrelated evidence.
4. Positive `delta_equity` alone never emits `EQUITY_DILUTION` or `equity_funded`.
5. Explicit `external_equity_financing` and `equity_dilution=True` drive their intended semantics.
6. Missing or mismatched delta comparison bases suppress affected ratios and expose a limitation; matching bases preserve valid calculations.
7. A high generic PE score is not primary for a distributor whose canonical Funding Loop is debt-funded with negative OCF.
8. The professional view exposes financial sanity, capital efficiency, forecast discipline and next event from the same `ResearchRunResult`.
9. Hospitality remains correctly routed, coverage-limited and without a specialized thesis.
10. v1.5.01, v1.5.02, v1.5.03 and all earlier gates remain green.
11. Full pytest and Release Gate pass at the exact final remote `main` HEAD.
12. README, changelog, migration guide, stock-research protocol and all version metadata agree on v1.5.04 / 1.5.4 / Core API 1.0.
