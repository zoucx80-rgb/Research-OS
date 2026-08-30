# Research OS v1.5.05

Research OS v1.5.05 (code SemVer `1.5.5`) is a Point-in-Time, evidence-linked investment research operating system built around one canonical, extensible runtime. This PATCH release preserves the v1.4.0 runtime/plugin architecture and v1.5.01–v1.5.04 correctness boundaries while adding a deterministic professional reporting-composition layer downstream of canonical research semantics.

## Core invariants

- No time travel: only evidence with `publish_ts <= decision_ts` may enter a run.
- No fabricated data: missing facts remain missing; `None` is never silently treated as economic zero.
- Facts, calculations, statistical evidence, analyst assumptions, and derived states remain distinct.
- Material metrics and conclusions retain evidence lineage and version metadata.
- Period-sensitive balance/flow metrics require truthful reporting-period semantics.
- Generic infrastructure is not specialized industry coverage.
- Missing professional coverage cannot be filled by narrative confidence.
- Funding-loop classification requires evidenced operands.
- Market-expectation claims require traceable and event-aware expectation evidence.
- Decision states are research outputs, never automatic trade orders.
- `ResearchCompletionGate` is the single authority for `COMPLETE` / `INCOMPLETE`.
- Reporting consumes canonical research state and cannot redefine completion or decision semantics.
- Human-facing presentation translates and composes canonical machine semantics without changing them.

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

`BusinessModelRouter` is `router@1.2.0`. Period-sensitive `inventory_to_revenue` evidence contributes only when its Evidence period is explicitly annual. Lease-heavy operating models suppress the low-PPE distributor heuristic when right-of-use assets or lease liabilities are economically material. The standard taxonomy includes `hospitality` without pretending that a Hospitality strategy plugin exists.

`BusinessModelProfile.classification_status` distinguishes `classified`, `unsupported_taxonomy`, and `insufficient_evidence`. Canonical industry execution follows the **primary business model only**. Secondary models remain classification and coverage metadata and do not contaminate the primary KPI / Driver / Thesis chain.

## Coverage-aware professional research

When the primary model has no compatible industry strategy plugin, the Coverage Gap remains explicit; a generic Driver Graph may be produced only as an informational fallback; no active specialized Thesis or Claim is generated; and the final completion state continues to come only from `ResearchCompletionGate`.

v1.5.03 added structured professional-question coverage. Industry contributions can declare required capabilities and evidence keys, and the runtime records whether each question is supported or blocked by missing capability/evidence. Asking a professional-looking question is not treated as professional coverage by itself.

v1.5.05 report composition keeps **evidence missing**, **capability missing**, **not applicable**, and **presentation/deferred** limitations distinct instead of collapsing them into one generic gap list.

## State Provenance

High-level fundamental, valuation, and expectation states carry explicit provenance. Legacy string inputs remain compatible but are identified as **analyst assumptions** rather than being narrated as Research OS-derived conclusions. Structured state inputs can identify derived, analyst-assumption, external-model, or manual-override sources together with supporting evidence and method metadata.

## Evidence-driven Thesis and Driver lineage

The built-in thesis engine does not default to `Fundamentals improve`. Directional operating signals determine whether evidence is improving, mixed, weakening, or insufficient before a thesis is formed. Driver nodes carry fact-specific evidence IDs rather than inheriting the complete run evidence set.

Manufacturing Driver Graphs can include supported revenue, margin, receivables, inventory, capex, and cash-generation nodes. Missing order, capacity, utilization, yield, qualification, or product-mix evidence remains an explicit question-level coverage gap rather than being fabricated.

## Funding-loop and economic exposure integrity

Severe Funding Loop evidence continues to feed the existing `DecisionContext.material_risk` boundary. Distributor analytics additionally expose factoring, derecognized receivables, receivable transfers, other working-capital financing, and total financing burden relative to gross profit. These exposures remain economically visible without being automatically relabeled as debt.

v1.5.04 requires explicit matching `<fact>_comparison_basis` values before delta facts form incremental ratios. Reported book-equity change (`delta_equity`) is informational; only explicit `external_equity_financing` drives equity-funding math, and only `equity_dilution=True` emits dilution risk. Missing or mismatched semantics remain missing rather than becoming professional-looking ratios.

## Field-correctness hardening

- filing YoY values rounded to two decimal percentage points pass ordinary financial-sanity validation while material discrepancies still fail;
- `cfo`, `ocf`, and `operating_cash_flow` are canonical aliases for falsifier evaluation, and new theses emit `ocf`;
- financing theses cite the evidence attached to their actual working-capital/financing drivers rather than the complete evidence set;
- a distributor PE route is penalized when the canonical Funding Loop is debt-funded with negative operating cash flow;
- no separate risk, decision or completion engine is introduced.

## Expectation gap and valuation result contracts

v1.5.05 adds structured expectation-gap and valuation-output contracts without weakening missing-value discipline.

- Missing consensus produces no fabricated expectation gap.
- Thin, stale, or pre-event consensus retains an explicit qualification.
- Directional expectation gaps do not invent numeric magnitude.
- `ValuationResult` can carry explicit Bear/Base/Bull cases, primary ranges, per-share values, sensitivities, evidence and assumption lineage.
- Presentation does not derive upside/downside merely because current price and a valuation estimate are present.

Expectation quality continues to use `ConsensusVintage.source_count`, `source_quality`, calendar age, and event-relative freshness.

## Professional human-readable research and report composition

Complete human-facing research uses:

```python
from research_os.reporting import ResearchReportComposer, ResearchViewPresenter

view = ResearchViewPresenter().build(result, locale="zh-CN")
document = ResearchReportComposer().compose(view)
```

The canonical direction is strictly one-way:

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
renderer / PDF
```

For v1.5.05 the full presenter fingerprint is `professional-research-view@1.3.0` and the report-composition fingerprint is `research-report-composer@1.0.0`. Historical v1.5.04 research remains associated with `professional-research-view@1.2.0`.

`HumanReadableResearchView` remains a read-only projection of canonical research artifacts. `ResearchReportComposer` accepts that view only; it does not accept a raw dictionary as an alternate semantic path and does not calculate or alter completion, decision, thesis, fundamental, expectation, valuation, funding, forecast, or business-model state.

The v1.5.05 composer:

- copies canonical Decision/Completion semantics into a concise first-page decision snapshot;
- deduplicates material risks by canonical semantic code;
- builds causal bridges only from an existing valuation `driver_bridge` or existing Driver Graph edges;
- never invents a causal edge or monitoring threshold for narrative smoothness;
- omits empty sections;
- keeps repository SHA, plugin/module identities, raw evidence IDs, and raw assumption IDs in the audit appendix by default;
- uses a concise evidence-traceability note in the main body;
- treats CNY `万元` / `亿元` scaling as display-only formatting and leaves machine values unchanged;
- surfaces lease-heavy limitations without claiming that lease-adjusted ROIC/valuation exists or describing the company as light-asset solely from owned-PPE ratios.

KPI display semantics continue to include formatted values, display units, period labels, period days, and annualization flags. Machine values remain unchanged for auditability.

`DecisionSummaryPresenter` / `semantic-report@1.0.0` remains available for compatibility.

## Repository map

- `src/research_os/runtime/` — canonical context, inputs, provenance, module graph, runtime, result, fingerprints and snapshots.
- `src/research_os/plugins/` — plugin manifests, registry, resolver, built-ins and extension protocols.
- `src/research_os/knowledge/` — PIT-aware knowledge-provider interface.
- `src/research_os/preflight/` — exact repository identity and frozen-HEAD validation.
- `src/research_os/domain/` — Evidence and lineage contracts.
- `src/research_os/validation/` — financial sanity validation.
- `src/research_os/period/` — reporting-period semantics.
- `src/research_os/completion/` — the single research completion policy.
- `src/research_os/router/` — business-model classification.
- `src/research_os/kpi/` — built-in KPI packs.
- `src/research_os/capital/` — capital efficiency, Funding Loop, and economic financing exposure.
- `src/research_os/drivers/` — Driver Graph, coverage scope, and driver-specific lineage.
- `src/research_os/thesis/` — evidence-driven Thesis / Anti-Thesis / Falsifiers.
- `src/research_os/expectations/` — expectation vintages, validation, quality, and structured expectation gaps.
- `src/research_os/valuation/` — model fitness, routing, execution validation, and additive valuation results.
- `src/research_os/decision/` — deterministic research decision-state engine.
- `src/research_os/reporting/` — semantic projection, `ResearchReportComposer`, `ResearchReportDocument`, display formatting, and audit separation.
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
pytest -q tests/unit/reporting tests/unit/expectations tests/unit/valuation
pytest -q tests/regression/architecture tests/regression/research_patterns/test_v1_5_05_reporting_patterns.py
pytest -q
python scripts/release_gate_v1_1.py
```

CI enforces architecture contracts, correctness regressions, storage migration smoke, full-suite verification, and the release gate. v1.5.05 additionally keeps dedicated reporting/expectation/valuation and cross-model reporting regressions as permanent release evidence.

## Version governance

`RESEARCH_OS_VERSION = "1.5.5"` and `CORE_API_VERSION = "1.0"`. Package metadata, public version metadata, plugin versions, presenter/composer fingerprints, and runtime component fingerprints must agree.

Snapshots separately freeze dataset, parser, formula, router, KPI pack, driver, forecast, valuation, report and OS versions plus payload hash and component fingerprints. Historical release tags and snapshots remain immutable.

## Migration and deferred scope

No database or Alembic migration is required for v1.5.05. Existing machine integrations may continue consuming canonical `ResearchRunResult` and `DecisionSummary`; complete v1.5.05 professional output should use `ResearchViewPresenter` followed by `ResearchReportComposer`.

v1.5.05 deliberately does not add a full Hospitality Plugin, a lease-adjusted valuation engine, a second generic-financial Decision state machine, a second Completion Gate, a Forecast subsystem rewrite, automatic trading logic, or company-specific Core logic.

See `docs/migrations/v1.5.05.md`, `docs/migrations/v1.5.04.md`, `docs/migrations/v1.5.03.md`, `docs/migrations/v1.5.02.md`, `docs/migrations/v1.5.01.md`, `docs/architecture/plugin-authoring-v1.md`, `CHANGELOG.md`, and the v1.5.05 design/implementation plan under `docs/superpowers/`.
