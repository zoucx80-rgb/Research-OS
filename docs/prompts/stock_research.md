# Research OS — Stock Research Invocation Protocol

This document defines the canonical prompt expansion for company / stock research using Research OS.

It is a **research-use protocol**, not a repository-development protocol. Unless the user explicitly asks to change Research OS, company research must not modify the `Research-OS` repository.

## Short Invocation

When the user says any equivalent of:

- `按 Research OS 完整研究 <公司> <代码>，decision_ts=<日期>`
- `用最新 Research OS 分析 <公司> <代码>`
- `Research OS 完整分析 <公司> <代码>`

expand the request into the protocol below.

If `decision_ts` is omitted and the user clearly requests a current-state research report, resolve it to the current date and state the resolved date explicitly. Historical research requires an explicit `decision_ts`.

## Step 0 — Repository Identity Preflight

The only valid Research OS repository is:

- `repository_full_name = zoucx80-rgb/Research-OS`
- `repository_id = 1350382205`
- `default_branch = main`

Required sequence:

1. Resolve exactly `zoucx80-rgb/Research-OS`.
2. Verify repository id `1350382205` and branch `main`.
3. Read current `main` HEAD and freeze that 40-hex SHA for the entire run.
4. Read root `AGENTS.md` and this canonical prompt from that exact frozen SHA.
5. Record real blob SHAs for required repository files.
6. Validate the collected evidence with the repository preflight contract.

Do not use generic web search to discover or substitute a Research OS repository. Do not accept forks, mirrors, similarly named repositories, placeholder SHAs, or file refs that are not pinned to the frozen HEAD. A preflight failure stops the research run.

## Baseline Fingerprint

The final research report must record at least repository full name and id, branch and frozen commit SHA, Research OS version, Core API version where available, and `decision_ts`.

`latest main` is used only to discover the starting SHA. Once frozen, later changes to `main` do not enter the run. Runtime, package and public metadata version surfaces must agree; version drift is a validation failure.

## Company Evidence Isolation

Company facts must be re-established for the current research run. Do not use project memory, previous chats, another company's analysis, cached conclusions, or unrelated repositories as company-fact evidence.

A previous versioned Research Snapshot may be used only when the user explicitly requests an incremental update or historical reproduction based on that snapshot.

Prioritize primary sources: company announcements and regulatory filings; annual/interim/quarterly reports; exchange and regulator disclosures; official investor-relations materials; then other traceable sources when primary evidence is unavailable.

## Hard Research Invariants

Strictly enforce:

- **No Time Travel** — material evidence must satisfy `publish_ts <= decision_ts`.
- **No Fabricated Data** — missing facts remain missing; `None` is not economic zero.
- **Period Truthfulness** — period-sensitive balance/flow metrics use the actual or explicitly resolved reporting period; interim periods must not silently assume 365 days.
- **Facts ≠ Calculations ≠ Statistical Evidence ≠ Assumptions**.
- **State Provenance** — derived state, analyst assumption, external-model state and manual override remain distinguishable.
- **Everything Has Lineage** — preserve raw/normalized value, unit, period, scope, version, evidence and formula/assumption lineage where applicable.
- **Models Beat Simple Benchmarks** before production promotion.
- **Research Signal ≠ Auto Trading**.
- **Completion ≠ Bullish**.

If reliable evidence cannot be obtained, preserve canonical `INSUFFICIENT_EVIDENCE` rather than filling the gap for narrative completeness. In human-facing output, translate it to readable language such as `证据不足` plus an explanation; the internal code may remain secondary audit metadata but **must not be the primary research conclusion**.

## Canonical Runtime and Plugin Resolution

Normal stock research is invoked with company/security, decision timestamp, evidence and run-scoped analytical inputs. The caller does not manually choose an industry strategy plugin in normal use.

Canonical sequence:

1. construct `ResearchContext` and `ResearchInputs` from the frozen baseline and current-run inputs;
2. route the company's business model;
3. build a run-scoped compatible plugin registry;
4. automatically resolve eligible stable industry and methodology plugins;
5. execute the capability dependency graph;
6. evaluate the single `ResearchCompletionGate`;
7. freeze one canonical `ResearchRunResult` and versioned snapshot;
8. project the same canonical result into a human-readable research view.

`experimental` plugins require explicit opt-in. Plugin overrides are exceptional, explicit and auditable.

Canonical industry execution follows the **primary business model only**. Secondary business models remain classification and coverage metadata. Unsupported secondary models may still produce Coverage Gaps, but compatible secondary plugins are not automatically co-executed in the primary KPI / Driver / Thesis chain.

Industry and methodology plugins are orthogonal. `ResearchEngine` itself remains unaware of company, industry or plugin identities.

## Coverage Integrity

Do not conflate business-model classification failure with missing industry strategy coverage:

- `business_model_taxonomy` — usable evidence does not fit the current standard taxonomy;
- `business_model_evidence` — evidence is insufficient to classify the business model;
- `industry_strategy` — the business model is represented but no compatible specialized strategy plugin exists.

A recognized `hospitality` company without a Hospitality Plugin therefore has an `industry_strategy` Coverage Gap. It must not be silently mapped to Manufacturing or Distributor.

When primary industry coverage is unavailable, a generic Driver Graph may be retained only as an informational fallback. It must be explicitly described as **通用驱动，仅供信息参考**, remain coverage-limited, and must not generate an active specialized Thesis/Claim. `ResearchCompletionGate` remains authoritative.

### Professional question coverage — v1.5.03+

For Research OS v1.5.03 or later, professional-looking research questions are not themselves evidence of professional coverage. Structured industry questions must preserve, where defined:

- question identity and text;
- required capability IDs;
- required/expected evidence keys;
- current answerability/coverage status;
- evidence actually supporting the answer;
- missing capabilities or missing evidence.

If a Manufacturing plugin asks about backlog, utilization, yield, product mix or qualification but those capabilities/evidence are absent, report the question as unanswered/partially covered. Never fill the answer narratively.

## Presentation Contracts

### v1.5.01 Decision-summary compatibility

`DecisionSummaryPresenter` remains the narrow compatibility surface:

```text
ResearchRunResult
    ↓
DecisionSummary
    ↓
DecisionSummaryPresenter
```

For zh-CN output, the semantic direction remains:

```text
machine code → localized label → localized explanation
```

Raw enum names, reason codes, plugin IDs, Python object representations, internal field names and debug diagnostics may be retained as secondary technical metadata but not as primary research conclusions.

Presentation must never calculate, promote, demote or otherwise modify completion, decision, thesis, fundamental, expectation, valuation, funding or coverage state.

### v1.5.02+ End-to-end research view

Complete human-facing stock research uses `ResearchViewPresenter`, not only the narrow `DecisionSummaryPresenter`.

### v1.5.03 Professional Research View

For v1.5.03, the canonical full human presentation fingerprint is **`professional-research-view@1.1.0`**.

Required one-way direction:

```text
ResearchRunResult
    ↓
ResearchViewPresenter
    ↓
HumanReadableResearchView
```

The professional view should expose, from the same canonical result where available:

- baseline/version identity;
- business-model classification and classification status;
- primary industry and methodology plugin selections;
- Coverage Gaps and professional-question assessments;
- KPI values and validity;
- Funding Loop and economic financing exposures;
- Driver Graph nodes/relations, coverage scope and driver-specific lineage;
- Thesis / Anti-Thesis / Falsifiers and thesis-signal assessment;
- market-expectation quality, including event-relative freshness;
- valuation routing and valuation execution/assumption lineage;
- high-level state provenance;
- the same canonical Decision/Completion result.

The presenter is a read-only projection. It does not become a second research engine.

## State Provenance — v1.5.03+

`fundamental_state`, `valuation_state`, and `expectation_state` must retain their source semantics. If legacy string inputs are used, human-facing output must identify them as analyst assumptions rather than claiming they were derived by Research OS.

Where provenance-aware state inputs exist, preserve source class (`derived`, `analyst_assumption`, `external_model`, `manual_override` or the current canonical equivalent), supporting evidence IDs and method/model metadata. Human prose must match that source.

A statement such as “基本面改善” must not be followed by “当前证据证明……” when the canonical state is only an analyst-supplied assumption.

## Driver and Thesis Integrity — v1.5.03+

Driver lineage should be fact-specific. Do not attach the complete evidence set to every driver merely to satisfy a formal lineage requirement. A critical driver should identify the evidence supporting that driver or explicitly remain under-supported.

The built-in Thesis layer must not assume `Fundamentals improve` solely because a supported industry plugin is present. Directional evidence must support the thesis. Mixed or weakening evidence must remain mixed/weakening/insufficient rather than being forced into a positive statement.

Manufacturing research should connect supported operating evidence such as revenue, margin, receivables, inventory, capex and cash generation. Specialized drivers such as backlog, utilization, yield, qualification or product mix may enter only when corresponding capabilities/evidence exist.

## Quantitative Presentation Semantics — v1.5.03+

Human-facing KPI output must preserve the machine value while also providing readable display semantics where known:

- formatted value;
- display unit (`%`, days, x, currency, etc.);
- reporting-period label;
- reporting-period days for period-sensitive metrics;
- whether a value/turnover rate is annualized.

Example: a machine value `0.0501` with percent semantics should be shown primarily as approximately `5.01%`; an H1 receivable-days value should be labeled with its H1/181-day period semantics rather than appearing as an unqualified annual DSO.

## Expectation Quality and Event-relative Freshness

Expectation quality uses existing source count, source quality and calendar vintage age. Fewer than 3 sources, low source quality, or an old vintage remain visible limitations.

For v1.5.03+, when a latest material event timestamp is available, compare the consensus vintage against that event. If `consensus_as_of < latest_material_event_ts`, record that the consensus **predates the latest material event / has not absorbed the latest material information**, even if it is less than 90 days old.

Calendar freshness and information freshness are distinct. This quality layer does not invent market direction and does not replace PIT validation.

## Lease-aware Router and Economic Exposure Integrity

For lease-heavy operating models, low owned PPE is not sufficient evidence of a distributor model. When right-of-use assets or lease liabilities are economically material, suppress the low-PPE distributor heuristic according to the pinned Router implementation. Do not reinterpret lease accounting through narrative shortcuts.

For distributor/working-capital research, expose factoring, derecognized receivables, receivable transfers and other working-capital financing when evidenced. These are economic financing exposures but must **not automatically be relabeled as debt**. Preserve their accounting/legal nature and analyze financing burden separately.

Comprehensive lease-adjusted ROIC/DCF is not implied by v1.5.03 unless a compatible methodology explicitly implements it.

## Machine-Enforced Safety Gates

Use the pinned Research OS implementation as the source of truth. Where safety context is available, the run must pass applicable machine contracts before a completed report may be emitted, including Repository Preflight, PIT Validation, Evidence Lineage, Financial Sanity, Business Model Router/specialized coverage, Capital Efficiency/Funding Loop, Driver/Thesis/Falsifiers, Expectation Evidence, Forecast Discipline, Valuation Fitness/Execution, Decision State, Next Verification Event/Temporal Consistency and Research Completion.

Financial sanity is a hard prerequisite. Expectation claims such as beat/miss/priced-in require auditable expectation evidence. Selected and executed valuation methods must remain consistent and retain scenario/assumption/lineage evidence. Only legal `ResearchDecisionState` values may appear as decision states.

Severe canonical Funding Loop evidence may populate the existing material-risk decision input; no parallel risk engine is allowed.

`ResearchCompletionGate` is the **single completion-policy authority**. Reporting must propagate the same `ResearchCompletionResult` (`final_status`, `blocking_modules`, `module_statuses`) and must not independently promote or demote completion.

## Required Research Order

Do not begin with a preferred valuation template. Preserve causal order:

1. Evidence ingestion and PIT filtering
2. Business Model Router and plugin/KPI applicability
3. Financial sanity, period semantics, capital efficiency, Funding Loop and growth quality
4. Driver Graph and driver-specific evidence lineage
5. Professional question coverage assessment
6. Thesis / Anti-Thesis / Falsifiers only where evidence and coverage permit
7. Expectations / surprise / expectation gap plus consensus-quality and event-freshness context
8. Forecast hypotheses and benchmark discipline where evidence permits
9. Valuation Model Fitness and execution where evidence permits
10. Research Decision State with state provenance retained
11. Monitoring / next-verification events
12. Research Completion Gate
13. `ResearchViewPresenter` one-way human-readable projection

Do not mechanically average incompatible valuation methods.

## Required Final Output

Where supported by evidence, include:

- frozen Research OS baseline fingerprint;
- resolved primary strategy/plugin set and Coverage Gaps;
- professional-question coverage and missing evidence;
- final completion state and blocking modules;
- human-readable module statuses;
- Research Decision State;
- State Provenance for high-level fundamental/expectation/valuation states;
- Thesis / Anti-Thesis / Falsifiers or an explicit limitation;
- specialized vs generic Driver Graph scope plus driver-specific evidence;
- period-aware, unit-aware financial/operating KPI presentation;
- Capital Efficiency, Funding Loop and evidenced financing exposures;
- market expectations, consensus quality, event-relative freshness and expectation gap;
- Forecast evidence/limitations;
- Valuation Model Fitness, executed valuation and assumption lineage;
- Evidence Quality / Evidence Gaps;
- key risks;
- next verification events;
- evidence that would increase conviction;
- evidence that would weaken or break the thesis.

A tool or browsing workflow ending successfully does not imply research completion. Canonical `FINAL_STATUS=COMPLETE` may exist only when `ResearchCompletionGate` returns COMPLETE. Otherwise status remains INCOMPLETE and blocking modules must be identified. Human-facing output translates those states without replacing their canonical meaning.

## Research vs. Repository Modification

A stock-research request is read-only with respect to Research OS by default. If research exposes a methodology defect, record it as an OS improvement candidate after completing/stopping the company research; do not silently modify Research OS mid-run.

## Incremental Update Invocation

When the user says an equivalent of `更新 <公司>，按 Research OS，只看上次 snapshot 之后的新证据`, use the latest Research OS `main` for methodology while preserving the prior versioned snapshot as the historical baseline. Produce an Evidence Delta rather than overwriting historical state.

At minimum report what changed, why, what did not change, whether conviction/Decision State changed, falsifier movement, and the next evidence to verify. Human-facing incremental output follows the current professional research-view contract.

## Historical PIT Invocation

Historical research requires explicit `decision_ts`. Prohibit evidence, outcomes, prices, disclosures and hindsight explanations published after that timestamp. Human-readable presentation may evolve by version, but it must never alter frozen canonical machine semantics of the historical snapshot.
