# Research OS v1.5.02

Research OS v1.5.02 (code SemVer `1.5.2`) is a Point-in-Time, evidence-linked investment research operating system built around one canonical, extensible runtime. This release preserves the v1.4.0 runtime/plugin architecture and the v1.5.01 semantic-correctness boundaries while extending them into end-to-end **Semantic Research Integrity**.

## Core invariants

- No time travel: only evidence with `publish_ts <= decision_ts` may enter a run.
- No fabricated data: missing facts remain missing; `None` is never silently treated as economic zero.
- Facts, calculations, statistical evidence, and assumptions remain distinct.
- Material metrics and conclusions retain evidence lineage and version metadata.
- Period-sensitive balance/flow metrics require truthful reporting-period semantics.
- Generic infrastructure is not specialized industry coverage.
- Missing professional coverage cannot be filled by narrative confidence.
- Funding-loop classification requires evidenced operands.
- Market-expectation claims require traceable expectation evidence.
- Decision states are research outputs, never automatic trade orders.
- `ResearchCompletionGate` is the single authority for `COMPLETE` / `INCOMPLETE`.
- Reporting consumes the same canonical `ResearchRunResult` and cannot redefine completion.
- Human-facing presentation translates canonical machine semantics without changing them.

## Canonical runtime

```text
ResearchContext + ResearchInputs
        ↓
ResearchRuntimeFactory
        ↓
ResearchRuntime
        ↓
ResearchEngine + run-scoped PluginRegistry
        ↓
ResearchRunResult + Snapshot
```

`ResearchRuntime` owns composition policy, completion evaluation, component fingerprinting, report contributions, and snapshot freezing. `ResearchEngine` executes capability dependencies only and remains unaware of company or industry identities.

## Business-model routing and strategy isolation

`BusinessModelRouter` remains `router@1.1.0` from v1.5.01. Period-sensitive `inventory_to_revenue` evidence contributes only when its Evidence period is explicitly annual. The standard taxonomy includes `hospitality` without pretending that a Hospitality strategy plugin exists.

`BusinessModelProfile.classification_status` distinguishes:

- `classified`
- `unsupported_taxonomy`
- `insufficient_evidence`

v1.5.02 additionally makes module status truthful: unresolved classification remains a structured profile but does not report Router `PASS`.

Canonical industry execution follows the **primary business model only**. Secondary models remain classification and coverage metadata. Unsupported secondary models still produce Coverage Gaps, while compatible secondary plugins are not automatically co-executed in the primary KPI / Driver / Thesis chain. This prevents cross-pack contamination.

## Coverage-aware research narrative

When the primary model has no compatible industry strategy plugin:

- the Coverage Gap remains explicit;
- a generic Driver Graph may be produced only as an informational fallback;
- the graph is marked `coverage_scope="generic"` and `coverage_limited=true`;
- no active Thesis or Claim is generated as if specialized industry research were complete;
- Driver/Thesis completion remains evidence-insufficient;
- the final completion state continues to come only from `ResearchCompletionGate`.

This is the expected behavior for a recognized `hospitality` company until a compatible Hospitality plugin is available.

## Funding-loop risk integrity

v1.5.02 connects severe canonical Funding Loop evidence to the existing `DecisionContext.material_risk` input. A `stressed` loop is material; a `debt_funded` loop with both `DEBT_FUNDS_NWC` and `NEGATIVE_OCF` is also material. This allows the existing Decision Engine to return `RISK_REVIEW` when financing risk is severe without adding a new decision state or parallel risk engine.

## Expectation quality

`ConsensusVintage.source_count` and `source_quality` are reused rather than duplicated. The expectation layer now records a non-directional quality assessment using source count, source quality, and vintage age:

- fewer than 3 sources → thin consensus;
- source quality below 0.5 → low source quality;
- vintage age above 90 days → stale consensus.

This quality context does not invent expectation direction and does not replace PIT validation.

## Industry report contributions

Built-in Manufacturing and Distributor plugins now return structured `ReportContribution` records with titles, descriptions, research questions, and artifact references. The contribution contract is additive and remains backward compatible.

Manufacturing contributions emphasize production/capacity, working-capital conversion and capital efficiency. Distributor contributions emphasize receivables/inventory/payables, funding loop, financing cost and impairment sensitivity.

## End-to-end human-readable research view

v1.5.01 introduced `DecisionSummaryPresenter` for the final decision summary. v1.5.02 keeps that compatibility surface and adds the standard complete human-facing view:

```python
from research_os.reporting import ResearchViewPresenter

view = ResearchViewPresenter().build(result, locale="zh-CN")
```

The canonical direction is one-way:

```text
ResearchRunResult
    ↓
ResearchViewPresenter
    ↓
HumanReadableResearchView
```

The view covers:

- baseline and version identity;
- business model and classification status;
- industry/methodology plugin selections;
- Coverage Gaps;
- structured industry report contributions;
- KPI values, statuses and missing reasons;
- Funding Loop state and reasons;
- Driver Graph and coverage scope;
- Thesis / Anti-Thesis / Falsifiers;
- expectation-quality context;
- valuation routing;
- the existing human-readable decision/completion summary.

Machine codes remain audit metadata. Chinese labels and explanations are the primary human-facing surface. The presenter does **not** calculate or alter completion, decision, thesis, fundamental, expectation, valuation, or funding states.

The default report fingerprint is `semantic-research-view@1.0.0`. The v1.5.01 `semantic-report@1.0.0` / `DecisionSummaryPresenter` remains available for compatibility and historical snapshots keep their original report version.

## Repository map

- `src/research_os/runtime/` — canonical context, inputs, module graph, runtime, result, fingerprints and snapshots.
- `src/research_os/plugins/` — plugin manifests, registry, resolver, built-ins and extension protocols.
- `src/research_os/knowledge/` — PIT-aware knowledge-provider interface.
- `src/research_os/preflight/` — exact repository identity and frozen-HEAD validation.
- `src/research_os/domain/` — Evidence and lineage contracts.
- `src/research_os/validation/` — financial sanity validation.
- `src/research_os/period/` — reporting-period semantics.
- `src/research_os/completion/` — the single research completion policy.
- `src/research_os/router/` — business-model classification.
- `src/research_os/kpi/` — built-in KPI packs.
- `src/research_os/capital/` — capital efficiency and Funding Loop.
- `src/research_os/drivers/` — Driver Graph and coverage scope.
- `src/research_os/thesis/` — Thesis / Anti-Thesis / Falsifiers.
- `src/research_os/expectations/` — expectation vintages, validation and quality.
- `src/research_os/valuation/` — model fitness, routing and execution validation.
- `src/research_os/decision/` — deterministic research decision-state engine.
- `src/research_os/reporting/` — canonical decision summary plus one-way semantic research view.
- `src/research_os/version.py` — `RESEARCH_OS_VERSION` and `CORE_API_VERSION`.

## Local verification

```bash
python -m pip install -e . --no-deps --no-build-isolation

pytest -q \
  tests/unit/runtime \
  tests/unit/plugins \
  tests/unit/knowledge \
  tests/integration/runtime \
  tests/regression/architecture

pytest -q \
  tests/regression/research_patterns/test_v1_2_1_correctness_patterns.py \
  tests/unit/kpi/test_period_sensitive_packs.py \
  tests/unit/capital/test_engine.py \
  tests/unit/kpi/test_applicability.py \
  tests/unit/completion/test_consistency.py \
  tests/unit/test_version_consistency_v1_2_1.py

pytest -q tests/integration/storage/test_v1_2_lineage_migration.py
pytest -q
python scripts/release_gate_v1_1.py
```

CI enforces the same order: architecture contracts → correctness regressions → migration smoke → full suite → release gate.

## Version governance

`RESEARCH_OS_VERSION = "1.5.2"` and `CORE_API_VERSION = "1.0"`. Package metadata, public version metadata and runtime version surfaces must agree.

Snapshots separately freeze dataset, parser, formula, router, KPI pack, driver, forecast, valuation, report and OS versions plus payload hash and component fingerprints. Historical release tags and snapshots remain immutable.

## Migration

No database migration is required for v1.5.02. Existing machine integrations may continue consuming canonical `ResearchRunResult` and `DecisionSummary`. Decision-summary-only human clients may continue using `DecisionSummaryPresenter`; complete human-facing research should use `ResearchViewPresenter`.

See `docs/migrations/v1.5.02.md`, `docs/migrations/v1.5.01.md`, `docs/architecture/plugin-authoring-v1.md`, `CHANGELOG.md`, and the v1.5.02 design/plan under `docs/superpowers/`.