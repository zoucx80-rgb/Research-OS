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
5. Record real blob SHAs for the required repository files.
6. Validate the collected evidence with the repository preflight contract.

Do not use generic web search to discover or substitute a Research OS repository. Do not accept forks, mirrors, similarly named repositories, placeholder SHAs, or file refs that are not pinned to the frozen HEAD. A preflight failure stops the research run.

## Baseline Fingerprint

The final research report must record at least:

- repository full name and id;
- branch and frozen commit SHA;
- Research OS version;
- Core API version where available;
- `decision_ts`.

`latest main` is used only to discover the starting SHA. Once frozen, later changes to `main` do not enter the run. For a latest-run baseline on v1.4.0 or later, runtime, package and public metadata version surfaces must agree; version drift is a validation failure.

## Company Evidence Isolation

Company facts must be re-established for the current research run. Do not use project memory, previous chats, another company's analysis, cached conclusions, or unrelated repositories as evidence.

A previous versioned Research Snapshot may be used only when the user explicitly requests an incremental update or historical reproduction based on that snapshot.

Prioritize primary sources:

1. Company announcements and regulatory filings
2. Annual / interim / quarterly reports
3. Exchange and regulator disclosures
4. Official investor-relations and company materials
5. Other traceable external sources when primary evidence is unavailable

## Hard Research Invariants

Strictly enforce:

- **No Time Travel** — material evidence must satisfy `publish_ts <= decision_ts`.
- **No Fabricated Data** — missing facts remain missing; `None` is not economic zero.
- **Period Truthfulness** — period-sensitive balance/flow metrics must use the actual or explicitly resolved reporting period. Interim periods must not silently assume 365 days. Distinguish within-period turns from annualized turns where both are presented.
- **Facts ≠ Calculations ≠ Statistical Evidence ≠ Assumptions**.
- **Everything Has Lineage** — preserve raw value, normalized value, unit, period, scope, version, source and formula/assumption lineage where applicable.
- **Models Beat Simple Benchmarks** before production promotion.
- **Research Signal ≠ Auto Trading**.

If reliable evidence cannot be obtained, use `INSUFFICIENT_EVIDENCE` rather than filling the gap for narrative completeness.

## v1.4 Canonical Runtime and Plugin Resolution

Normal stock research should be invoked with the company/security, decision timestamp, and evidence requirements. The caller does **not** need to manually choose an industry strategy plugin in normal use.

The canonical runtime sequence is:

1. construct `ResearchContext` and `ResearchInputs` from the frozen baseline and current run inputs;
2. route the company's business model;
3. build a run-scoped compatible plugin registry;
4. automatically resolve eligible `stable` industry and methodology plugins;
5. execute the capability dependency graph;
6. evaluate the single Research Completion Gate;
7. freeze one canonical `ResearchRunResult` and versioned snapshot.

`experimental` plugins require explicit opt-in. A plugin override is exceptional and must remain explicit and auditable.

If the routed primary or secondary business model lacks a compatible specialized strategy plugin, record an explicit **Coverage Gap**. If an explicitly requested methodology cannot be satisfied, record a methodology Coverage Gap. A Coverage Gap must never be silently converted into specialized KPI support, PASS, or COMPLETE. Plugin failure, compatibility rejection, and unsupported capability coverage must remain visible in the research result.

Industry and methodology plugins are orthogonal. Business-model routing selects the relevant industry strategy; compatible methodology plugins may then extend the available capability graph. `ResearchEngine` itself must remain unaware of company, industry, or plugin identities.

Reporting must consume the canonical `ResearchRunResult`. It must not accept a parallel status dictionary as a second completion-policy surface, and it must take `final_status`, `blocking_modules`, and `module_statuses` from the same runtime `ResearchCompletionResult`.

## Machine-Enforced Safety Gates

Use the pinned Research OS implementation as the source of truth. Where the safety context is available, the run must pass the applicable machine contracts before a completed report may be emitted:

- Repository Preflight
- PIT Validation
- Evidence Lineage
- Financial Sanity
- Business Model Router / specialized KPI or strategy coverage
- Capital Efficiency / Funding Loop
- Driver Graph / Thesis / Anti-Thesis / Falsifiers
- Expectation Evidence
- Forecast Discipline
- Valuation Fitness / Valuation Execution
- Decision State
- Next Verification Event / Temporal Consistency
- Research Completion

Financial sanity is a hard prerequisite: unit, scale, arithmetic or cross-report consistency failures block downstream valuation/decision completion. Expectation claims such as beat/miss/priced-in require auditable expectation evidence. The selected valuation model must equal the executed model and retain scenario, assumption, lineage, and driver-bridge evidence. Only legal `ResearchDecisionState` values may appear as decision states.

For the v1.2.1 correctness semantics preserved by v1.4.0:

- Interim day-based KPIs require a known reporting-period length or derivable dates. If period length is unavailable, keep the metric missing with an explicit reason rather than substituting 365.
- Funding-loop inputs such as working-capital change, debt/equity funding and operating cash flow remain missing when not evidenced. An unclassifiable loop is `unknown` and maps to `INSUFFICIENT_EVIDENCE`.
- Generic core KPI infrastructure is not specialized coverage. Specialized KPI/strategy PASS requires support for the routed primary business model; unsupported primary models remain visible as a coverage limitation.
- `ResearchCompletionGate` is the single completion-policy authority. Reporting must propagate the same `ResearchCompletionResult` (`final_status`, `blocking_modules`, `module_statuses`) and must not independently promote or demote completion.
- Claim-capability normalization must not treat a decision-state claim as an automatic valuation or target-price claim.

## Required Research Order

Do not begin with a preferred valuation template. Preserve the causal order implemented by the pinned Research OS. At minimum:

1. Evidence ingestion and PIT filtering
2. Business Model Router and plugin / KPI applicability resolution
3. Financial sanity, period semantics, capital efficiency, funding loop, growth quality
4. Driver Graph and key-driver ranking
5. Thesis / Anti-Thesis / Falsifiers
6. Expectations / surprise / expectation-gap analysis
7. Forecast hypotheses and benchmark discipline where evidence permits
8. Valuation Model Fitness and execution where evidence permits
9. Research Decision State
10. Monitoring and next-verification events
11. Research Completion Gate

Do not mechanically average incompatible valuation methods.

## Required Final Output

The report should include, where supported by evidence:

- Research OS baseline fingerprint
- resolved strategy/plugin set and any Coverage Gap
- `FINAL_STATUS = COMPLETE | INCOMPLETE`
- module validation/completion status for material gates
- Research Decision State
- Thesis / Anti-Thesis / Falsifiers
- Business Model classification and specialized KPI/strategy applicability
- Key operating drivers
- Financial quality, period-aware operating KPIs, capital efficiency and funding loop
- Market expectations and expectation gap, or explicit `INSUFFICIENT_EVIDENCE`
- Forecast evidence / limitations
- Valuation Model Fitness and executed valuation lineage
- Evidence Quality / Evidence Gaps
- Key risks
- Next verification events
- Evidence that would increase conviction
- Evidence that would weaken or break the thesis

A tool or browsing workflow ending successfully does **not** imply research completion. `FINAL_STATUS=COMPLETE` may be emitted only when the Research Completion Gate returns COMPLETE. Otherwise report `FINAL_STATUS=INCOMPLETE` and identify blocking modules. The report's completion fields must come from the same completion result used by the runtime.

## Research vs. Repository Modification

A stock-research request is read-only with respect to Research OS by default. If research exposes a methodology defect, report it as an OS improvement candidate after completing or stopping the research; do not silently modify the OS mid-run.

## Incremental Update Invocation

When the user says an equivalent of:

`更新 <公司>，按 Research OS，只看上次 snapshot 之后的新证据`

use the latest Research OS `main` for methodology, but preserve the prior versioned Research Snapshot as the historical baseline. Produce an Evidence Delta and do not overwrite the historical snapshot.

At minimum report what changed, why it changed, what did not change, whether conviction or Research Decision State changed, falsifier movement, and the next evidence that must be verified.

## Historical PIT Invocation

Historical research requires explicit `decision_ts`. Prohibit evidence, outcomes, prices, disclosures, and hindsight explanations published after that timestamp.
