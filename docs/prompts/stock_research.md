# Research OS — Stock Research Invocation Protocol v1.6

This document defines the canonical prompt expansion for company / stock research on the **current Research OS v1.6 runtime**. It is a research-use protocol, not a repository-development protocol. Unless the user explicitly requests Research OS development, a company research run must not modify the repository.

## Short invocation

Equivalent requests include:

- `按 Research OS 完整研究 <公司> <代码>，decision_ts=<日期>`
- `用最新 Research OS 分析 <公司> <代码>`
- `Research OS 完整分析 <公司> <代码>`

If `decision_ts` is omitted for a clearly current-state request, resolve the date explicitly before evidence collection. Historical company research requires an explicit `decision_ts`.

## 1. Repository preflight and frozen baseline

The only valid repository identity is:

- `repository_full_name = zoucx80-rgb/Research-OS`
- `repository_id = 1350382205`
- `branch = main`

Required sequence:

1. Resolve exactly the official repository; do not substitute forks or similarly named repos.
2. Read current `main` HEAD and freeze its exact 40-hex SHA.
3. Verify repository full name, stable repository id, branch/check-out mode, HEAD, Research OS version and Core API version against the baseline contract.
4. Read repository rules and this prompt from that same frozen SHA.
5. Keep the frozen baseline unchanged for the whole run.

`latest main` is only a discovery step. Once the run starts, later commits do not enter the run.

## 2. Evidence isolation and PIT discipline

Company facts must be established for this run. Do not treat project memory, previous chats, another company's report, cached conclusions, or unrelated repository data as current company-fact evidence.

Prioritize traceable primary sources: exchange/regulator filings, company announcements, annual/interim/quarterly reports, and official investor-relations material. Other sources may supplement evidence when their provenance and publication timestamp are explicit.

Every material evidence item must satisfy:

```text
publish_ts <= decision_ts
```

No Time Travel is fail-closed. Evidence published after the cutoff may be discussed only as an explicitly out-of-cutoff observation, never as an input to the frozen run.

## 3. Hard research invariants

Strictly enforce:

- **No Time Travel**.
- **No Fabricated Data** — missing facts remain missing; `None` is not economic zero.
- **Facts ≠ Calculations ≠ Statistical Evidence ≠ Assumptions**.
- **Everything Has Lineage** — material artifacts retain evidence or explicit assumption lineage.
- **Period Truthfulness** — period-sensitive metrics use truthful reporting-period semantics.
- **Comparison-Basis Safety** — incompatible metrics are `NOT_COMPARABLE`, not forcibly compared.
- **Models Beat Simple Benchmarks** before production promotion.
- **Research Signal ≠ Auto Trading**.
- **Completion ≠ Bullish** and **Readiness ≠ Completion**.
- Missing specialized plugin coverage remains a coverage gap; generic logic must not masquerade as industry expertise.

When evidence is insufficient, retain typed `INSUFFICIENT_EVIDENCE`, `NOT_APPLICABLE`, `UNKNOWN`, `UNRESOLVED`, or another contract-defined state. Human-readable output may translate the state, but may not replace it with narrative confidence.

## 4. Current Core API 2.0 run

Construct one typed `ResearchRunCommand` around a frozen `ResearchContext` and run-scoped research inputs. The current v1.6 sequence is:

```text
ResearchRunCommand
    ↓
Repository Preflight
    ↓
BootstrapPlanCompiler
    ↓
ResearchEngine
    ├─ Repository Preflight Artifact
    ├─ PIT Evidence Artifact
    ├─ Financial Fact Snapshot
    └─ Business Model Profile
    ↓
StrategyResolver / Plugin API 2.0
    ↓
ResearchPlanCompiler
    ↓
ResearchEngine
    ↓
Completion Evaluation
    ↓
Readiness Evaluation
    ↓
ResearchRunResult
```

`ResearchEngine` is the sole module invoker. Modules exchange typed Artifact Schema 2.0 values; orchestration code must not bypass the Engine to create an alternate research state.

Repository preflight, business-model routing, plugin resolution, module execution, Completion and Readiness all belong upstream of reporting.

## 5. Plugin API 2.0

Normal research automatically resolves compatible stable industry and methodology plugins from the PIT business-model profile and run context.

Plugin requirements:

- `PluginManifest.plugin_api_version == "2.0"`;
- explicit Core API and Research OS version specifiers;
- declared business-model support and service capabilities;
- `service_capabilities` exactly match returned services;
- applicability/support assessment retains evidence lineage where applicable;
- experimental plugins require explicit opt-in;
- plugin overrides require explicit rationale and remain auditable.

Industry and methodology plugins are orthogonal. Canonical industry execution follows the primary business model; secondary business models remain classification/coverage metadata unless the contract explicitly says otherwise.

## 6. Professional research foundations

Use the typed v1.6 domain services/modules appropriate to the available evidence. The research should cover, when applicable and evidenced:

- financial time series and critical KPIs;
- Business Model Router / KPI Pack;
- capital efficiency, Funding Loop and cash-flow quality;
- operating evidence and Driver Graph;
- Thesis / Anti-Thesis / Falsifiers;
- semantic claims and thesis state;
- market expectations, expectation quality and Expectation Gap;
- forecast hypotheses, PIT folds, benchmark comparison and promotion discipline;
- peers and comparison-basis normalization;
- valuation model fitness, routing, execution and reconciliation;
- sensitivity analysis with material assumptions/model boundary;
- Decision State and state provenance;
- monitoring plan, next verification event and prior-run review;
- evidence quality/gaps, Completion and Research Readiness.

Do not invent a professional artifact because it is expected in a polished report. Structured unsupported output is correct when the domain cannot be supported.

## 7. Snapshot Schema 2.0 and lineage

When persistence is requested, freeze the finalized research into Snapshot Schema 2.0.

The snapshot must preserve:

- frozen company / `decision_ts` / repository baseline;
- actual module/plugin/metric/policy/external version identities;
- component implementation fingerprints;
- typed artifacts and Artifact value fingerprints;
- semantic input assumptions;
- Completion and Readiness;
- canonical research digest;
- separate persistence/integrity digest.

Operational controls such as `persist_snapshot` are not research semantics and must not alter the research digest.

`run_id`, `snapshot_id` and creation timestamps are identity/integrity metadata, not research-semantic inputs.

Persisted snapshots must be verified before query/replay. Tampered payload, artifact fingerprint, research digest or integrity digest fails closed.

## 8. HTTP API v1

The HTTP API is read-only. It may expose verified runs, artifacts, snapshots, snapshot listings, research views and health state. API/projector layers must not rebuild research logic or bless unverified database payloads.

PIT query bounds remain explicit. A request for a company snapshot at or before a date must not return a later `decision_ts`.

## 9. Completion and Readiness

Completion answers whether required execution contracts ran successfully enough to constitute a complete machine research run.

Readiness answers whether the resulting research artifacts are sufficiently evidenced and qualified for their intended research use.

They are separate typed states. An `INCOMPLETE` execution cannot be reported as `READY`; a `COMPLETE` run may still be `NOT_READY` if research evidence/qualifiers are insufficient.

Presentation never changes either state.

## 10. Canonical reporting and presentation

Current v1.6 human-facing output uses exactly one downstream direction:

```text
ResearchRunResult
    ↓
ResearchViewPresenter
    ↓
HumanReadableResearchView
    ↓
ResearchReportComposer
    ↓
ResearchReportDocument
    ↓
ResearchReportMarkdownRenderer
    ↓
MarkdownPresentationArtifact
    ↓
HtmlPresentationArtifact
    ↓
PdfPresentationArtifact
```

The presenter, composer and renderers are read-only with respect to research meaning. They may translate, organize, format, style, paginate and export; they may not recalculate or change:

- KPI or financial state;
- Funding Loop or capital efficiency;
- Driver/Thesis/semantic claim state;
- expectation or forecast state;
- valuation result/reconciliation;
- sensitivity or monitoring conditions;
- Decision State;
- Completion or Readiness.

`SemanticPreservationValidator` must preserve Artifact identity, provider, lineage, payload fingerprint and the reporting-chain semantic fingerprint. Material sensitivity results retain assumptions/model boundary; monitoring items retain explicit condition and lineage.

When PDF output is requested, actually render a real Playwright Chromium PDF. Successful Markdown/HTML serialization is not a PDF acceptance substitute.

## 11. Current v1.6 field acceptance

The current release validates three separate dimensions:

- `machine_semantics`
- `research_depth`
- `presentation`

The three canonical synthetic cases are:

- Manufacturing typed architecture — `PASS / PASS / PASS`.
- Distributor funding and valuation — `PASS / LIMITED / PASS`.
- Coverage-limited no-plugin — `PASS / LIMITED / PASS`.

`LIMITED` research depth is not a failed presentation and must not be disguised as full coverage.

## 12. Historical replay is a separate mode

Do not import a v1 compatibility runtime into v1.6 to reproduce old releases.

The supported historical field releases v1.5.08–v1.5.12 are replayed from exact frozen commits in detached worktrees with dedicated virtualenvs, sanitized `PYTHONPATH`, historical runner scripts/fixtures and commit-specific dependencies.

Historical replay rules:

1. resolve only the exact registry-pinned commit;
2. verify the detached worktree HEAD and historical product/Core API version;
3. verify imports originate inside that historical worktree;
4. execute the historical release's own runner and fixtures;
5. stage output and publish it only after success;
6. never read current v1.6 runtime/reporting state as historical research input;
7. keep any compatibility action narrow, exact-commit/exact-source-fingerprint bounded and replay-only.

A historical replay answers “what that historical release produced under its frozen contracts.” It is not a current v1.6 research run.

## 13. Required research output

A full report should make the following explicit where supported:

- frozen repository/version/`decision_ts` baseline;
- evidence cutoff and key source lineage;
- business model and plugin coverage;
- financial/KPI picture and critical data gaps;
- capital efficiency / Funding Loop / cash-flow quality;
- Driver Graph and causal evidence limitations;
- Thesis / Anti-Thesis / Falsifiers;
- market expectations / Expectation Gap;
- forecast evidence and benchmark discipline;
- valuation model fitness and reconciled scenarios/ranges;
- Evidence Quality / Evidence Gaps;
- Research Decision State and provenance;
- next verification event;
- conditions that raise conviction;
- explicit Thesis Broken conditions;
- Completion and Research Readiness;
- audit appendix with implementation/version/lineage detail.

Do not turn a research state into a trading instruction unless the user separately requests a portfolio/trading decision layer. Even then, **Research Signal ≠ Auto Trading** remains mandatory.

## 14. Development boundary

If the user asks to change Research OS itself, leave this research invocation protocol and follow the repository development/design/release workflow. Company-research evidence and development validation evidence must remain separate.
