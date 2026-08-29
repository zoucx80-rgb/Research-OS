# Research OS — Stock Research Invocation Protocol

This document defines the canonical prompt expansion for company / stock research using Research OS.

It is a **research-use protocol**, not a repository-development protocol. Unless the user explicitly asks to change Research OS, company research must not modify the `Research-OS` repository.

## Short Invocation

When the user says any equivalent of:

- `按 Research OS 完整研究 <公司> <代码>，decision_ts=<日期>`
- `用最新 Research OS 分析 <公司> <代码>`
- `Research OS 完整分析 <公司> <代码>`

expand the request into the full protocol below.

If `decision_ts` is omitted and the user clearly requests a current-state research report, resolve it to the current date and state the resolved date explicitly before using it.

For historical research, the user should provide an explicit `decision_ts`.

## Step 0 — Repository Identity Preflight

The only valid Research OS repository is:

- `repository_full_name = zoucx80-rgb/Research-OS`
- `repository_id = 1350382205`
- `default_branch = main`

Repository access must use an exact GitHub repository lookup when that connected GitHub resource is available.

Do **not** use generic web search to discover, select, or substitute a Research OS repository.

Do **not** fall back to:

- similarly named repositories;
- forks;
- mirrors;
- third-party `research-os` projects;
- cached repository copies whose identity and HEAD cannot be verified;
- chat memory as a substitute for repository contents.

Required preflight sequence:

1. Resolve exactly `zoucx80-rgb/Research-OS`.
2. Verify repository id `1350382205`.
3. Verify default branch `main`.
4. Read the current `main` HEAD commit SHA.
5. Freeze that SHA as the Research OS baseline for the entire research run.
6. Read root `AGENTS.md` from that exact SHA.
7. Read all Research OS specifications, configuration, and code required by the task from that exact SHA.

If any of steps 1–6 fail or do not match, stop the company research and report the failed preflight. Do not search for an alternative repository.

## Baseline Fingerprint

The final research report must record at least:

- repository full name;
- repository id;
- branch;
- frozen commit SHA;
- Research OS version;
- `decision_ts`.

The phrase `latest main` is only used to discover the starting SHA. Once discovered, the entire run is pinned to that SHA even if `main` changes during the research session.

## Company Evidence Isolation

Company facts must be re-established for the current research run.

Do not use project memory, previous chats, another company's analysis, cached conclusions, or unrelated repositories as evidence.

A previous versioned Research Snapshot may be used only when the user explicitly requests an incremental update or historical reproduction based on that snapshot.

Methodology may be reused. Company facts may not.

Prioritize primary sources:

1. Company announcements and regulatory filings
2. Annual / interim / quarterly reports
3. Exchange and regulator disclosures
4. Official investor-relations and company materials
5. Other traceable external sources when primary evidence is unavailable

## Hard Research Invariants

Strictly enforce:

- **No Time Travel** — material evidence must satisfy `publish_ts <= decision_ts`.
- **No Fabricated Data** — missing data remains missing.
- **Facts ≠ Calculations ≠ Statistical Evidence ≠ Assumptions** — preserve the distinction explicitly.
- **Everything Has Lineage** — material facts, metrics, models, and conclusions must be traceable.
- **Models Beat Simple Benchmarks** — forecasting models require appropriate out-of-sample evidence before promotion.
- **Research Signal ≠ Auto Trading** — output research states, not autonomous trading instructions.

If reliable evidence cannot be obtained, mark the item `INSUFFICIENT_EVIDENCE` rather than filling the gap for narrative completeness.

## Required Research Order

Do not begin with a preferred valuation template.

Use the current pinned Research OS implementation to determine the actual research flow. At minimum, preserve this causal order where applicable:

1. Evidence ingestion and PIT filtering
2. Business Model Router
3. Appropriate KPI Pack
4. Capital efficiency / funding loop / growth quality
5. Driver Graph and key-driver ranking
6. Thesis / Anti-Thesis / Falsifiers
7. Expectations / surprise / expectation gap analysis
8. Forecast hypotheses and benchmark discipline where evidence permits
9. Valuation Model Fitness
10. Valuation range / scenario outputs where evidence permits
11. Research Decision State
12. Monitoring and next-verification events

Do not mechanically average incompatible valuation methods.

## Required Final Output

The report should include, where supported by evidence:

- Research OS baseline fingerprint
- Research Decision State
- Thesis
- Anti-Thesis
- Falsifiers
- Business Model classification and KPI Pack
- Key operating drivers
- Capital efficiency and growth quality
- Market expectations and expectation gap
- Forecast evidence / limitations
- Valuation Model Fitness
- Valuation range or scenario outputs
- Evidence Quality
- Evidence Gaps
- Key risks
- Next verification events
- Evidence that would increase conviction
- Evidence that would weaken or break the thesis

All material numerical facts and material conclusions must retain evidence lineage.

## Research vs. Repository Modification

A stock-research request is read-only with respect to Research OS by default.

Do not modify `Research-OS` during a company research run unless the user separately and explicitly asks to improve or change Research OS.

If the research exposes a methodology defect, report it as an OS improvement candidate after completing or stopping the research; do not silently modify the OS mid-run.

## Incremental Update Invocation

When the user says an equivalent of:

`更新 <公司>，按 Research OS，只看上次 snapshot 之后的新证据`

use the latest Research OS `main` for methodology, but preserve the prior versioned Research Snapshot as the historical baseline. Produce an Evidence Delta and do not overwrite the historical snapshot.

At minimum report:

- what changed;
- why it changed;
- what did not change;
- whether conviction increased or decreased;
- whether Research Decision State changed;
- which falsifiers moved closer to or farther from activation;
- the next evidence that must be verified.

## Historical PIT Invocation

When the user requests historical research, require an explicit `decision_ts` and prohibit all evidence published after it.

Do not use later outcomes, later disclosures, later prices, or hindsight explanations to improve the historical conclusion.
