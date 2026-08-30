# Research OS v1.5.01

Research OS v1.5.01 (code SemVer `1.5.1`) is a Point-in-Time, evidence-linked investment research operating system built around one canonical, extensible runtime. This patch preserves the v1.4.0 runtime/plugin architecture and hardens semantic correctness at three boundaries: period-safe business-model routing, accurate coverage-gap classification, and a canonical human-readable zh-CN presentation adapter.

## Core invariants

- No time travel: only evidence with `publish_ts <= decision_ts` may enter a run.
- No fabricated data: missing facts remain missing and may surface as `INSUFFICIENT_EVIDENCE`; `None` is never silently treated as economic zero.
- Facts, calculations, statistical evidence, and assumptions remain distinct.
- Material metrics and claims carry evidence lineage and version metadata.
- Financial unit/scale corruption is a hard failure before valuation or decision completion.
- Period-sensitive balance/flow metrics use explicit reporting-period semantics; interim periods do not silently assume 365 days.
- Generic infrastructure is not specialized KPI coverage. Unsupported routed business models produce explicit coverage gaps.
- Funding-loop classification requires evidenced operands; missing funding facts remain unknown rather than invented.
- Market-expectation conclusions require a traceable expectation baseline.
- Selected valuation models must match executed models and retain assumptions, lineage, and driver bridges.
- Decision states are research outputs, never automatic trade orders.
- `ResearchCompletionGate` is the single authority for `COMPLETE` / `INCOMPLETE`.
- Reporting consumes the same canonical `ResearchRunResult` and cannot redefine completion status.
- Human-facing presentation translates canonical machine semantics without changing those semantics.

## Canonical runtime

The public execution path is:

```text
ResearchContext + ResearchInputs
        ↓
ResearchRuntimeFactory
        ↓
ResearchRuntime
        ↓
ResearchEngine + run-scoped PluginRegistry
        ↓
ResearchRunResult
```

`ResearchRuntime` owns composition policy, completion evaluation, component fingerprinting, and snapshot freezing. `ResearchEngine` executes capability dependencies only; it does not contain company, industry, or plugin identifiers.

`ResearchRuntimeFactory.default()` composes the built-in strategy provider. `ResearchRuntimeFactory.with_providers(...)` is the explicit extension point for additional trusted plugin providers. Registries and module instances are rebuilt for every run so mutable plugin state cannot leak across research runs.

## Router and coverage semantics

`BusinessModelRouter` is `router@1.1.0`. The period-sensitive `inventory_to_revenue` classification signal contributes only when its Evidence period is explicitly annual. Interim or unknown period semantics cannot silently influence distributor classification as if they were full-year values.

`BusinessModelProfile` separately records whether the company was `classified`, the current taxonomy is `unsupported_taxonomy`, or usable business-model evidence is `insufficient_evidence`.

The standard taxonomy includes `hospitality`. This makes hotel/住宿 business models representable without pretending that a specialized hotel strategy plugin exists. `StrategyResolver` distinguishes business-model taxonomy/evidence gaps from the normal case where a represented business model has no compatible industry strategy plugin.

## Plugin resolution

Research OS v1.5.01 preserves the two orthogonal plugin types introduced in v1.4.0:

- `industry` plugins for routed business-model strategy/KPIs;
- `methodology` plugins for cross-industry research methods.

Stable compatible plugins are eligible for automatic resolution. Experimental plugins require explicit opt-in. Compatibility is enforced through `PluginManifest` using `CORE_API_VERSION = "1.0"`, plugin semantic version, Research OS compatibility range, declared `provides` / `requires`, business-model coverage, maturity, and priority.

A normal stock-research caller supplies the company/security and evidence, not a hand-selected industry plugin. The runtime routes the business model and resolves compatible plugins. If no compatible strategy exists, `StrategyResolution.coverage_gaps` records that limitation; the gap is never silently treated as PASS or COMPLETE.

See `docs/architecture/plugin-authoring-v1.md`.

## Human-readable reporting

`DecisionSummary` remains the canonical reporting read model derived from `ResearchRunResult`. For human-facing zh-CN output, use `DecisionSummaryPresenter`:

```python
from research_os.reporting import DecisionSummaryPresenter

view = DecisionSummaryPresenter().build(result, locale="zh-CN")
```

Presentation values keep three explicit layers:

```text
canonical machine code → Chinese label → Chinese explanation
```

The raw machine code remains technical metadata. It is not used as the primary research conclusion. Unknown internal codes receive a readable fallback explanation instead of being dumped directly to the user. The presenter does not recompute completion, decision, thesis, fundamental, expectation, or valuation states.

## Repository map

- `src/research_os/runtime/` — canonical context, inputs, module graph, engine, factory, result, fingerprints and snapshot composition.
- `src/research_os/plugins/` — plugin manifests, registry, resolver, built-in providers and extension contracts.
- `src/research_os/knowledge/` — PIT-safe knowledge-provider interface.
- `src/research_os/preflight/` — exact repository identity and frozen-HEAD validation.
- `src/research_os/domain/` — Evidence, calculation lineage, assumption lineage and version contracts.
- `src/research_os/validation/` — financial unit, scale, arithmetic and consistency validation.
- `src/research_os/period/` — reporting-period semantics and period-aware turnover helpers.
- `src/research_os/completion/` — module status and final research completion gate.
- `src/research_os/router/` — explainable business-model classification and classification semantics.
- `src/research_os/kpi/` — reusable KPI contracts and built-in calculation packs.
- `src/research_os/capital/` — capital efficiency, evidence-aware funding loop and growth quality.
- `src/research_os/drivers/` — driver graph and ranking.
- `src/research_os/thesis/` — Thesis / Anti-Thesis / Falsifier state machine.
- `src/research_os/ledger/` — Evidence Ledger and conclusion validity horizons.
- `src/research_os/expectations/` — PIT expectation vintages, evidence validation and surprise decomposition.
- `src/research_os/forecasting/` — hypothesis registration, model promotion and forecast-error attribution.
- `src/research_os/valuation/` — model fitness, routing and execution validation.
- `src/research_os/decision/` — deterministic research-state engine and legal state validation.
- `src/research_os/reporting/` — canonical reporting read models plus one-way human-readable semantic presentation.
- `src/research_os/version.py` — centralized `RESEARCH_OS_VERSION` and `CORE_API_VERSION`.
- `alembic/` — schema/governance migrations; v1.5.01 adds no new database migration.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — approved architecture designs and implementation plans.

The legacy `src/research_os/orchestration.py` and duplicate KPI registry policy surface removed in v1.4.0 remain absent.

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

The release script retains its historical filename for compatibility, reads the current package version, and evaluates all earlier correctness/architecture gates plus the v1.5.01 semantic-correctness gates.

## Completion semantics

`FINAL_STATUS` has only two machine-readable values: `COMPLETE` or `INCOMPLETE`. `ResearchCompletionGate` owns this policy. Reporting may display the result but cannot independently promote or demote it. Missing required evidence, unsupported strategy/KPI coverage, unknown funding classification, or unsupported claimed capabilities remain visible as module statuses, coverage gaps, or blockers.

`DecisionSummaryPresenter` only translates the canonical values into human-readable language. It is not a second completion source.

## Snapshot and version governance

`src/research_os/version.py` defines `RESEARCH_OS_VERSION = "1.5.1"` and `CORE_API_VERSION = "1.0"`. `research_os.__version__`, `pyproject.toml`, and `research_os_version.json` must agree with the runtime version.

Each research snapshot separately freezes dataset, parser, formula, router, KPI pack, driver, forecast, valuation, report and OS versions plus payload hash and component fingerprints. The default report version for v1.5.01 is `semantic-report@1.0.0`. Historical snapshots and released tags remain immutable.

## Migration

No database migration is required for v1.5.01. Existing v1.4.0 callers remain compatible because the new Router and CoverageGap fields have defaults and the Core API remains `1.0`.

Human-facing callers should use `DecisionSummaryPresenter`; machine integrations may continue consuming canonical `DecisionSummary` and `ResearchRunResult`.

See `docs/migrations/v1.5.01.md`, `docs/migrations/v1.4.0.md`, `docs/architecture/plugin-authoring-v1.md`, `CHANGELOG.md`, and the v1.5.01 design/plan under `docs/superpowers/`.
