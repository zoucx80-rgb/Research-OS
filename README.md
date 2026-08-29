# Research OS v1.4.0

Research OS v1.4.0 is a Point-in-Time, evidence-linked investment research operating system built around one canonical, extensible runtime. The release preserves the correctness hardening from v1.2.1 while replacing duplicate orchestration/registry policy surfaces with run-scoped composition, versioned strategy plugins, canonical research results, component fingerprints, and architecture-first release gates.

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

## Plugin resolution

Research OS v1.4.0 supports two orthogonal plugin types:

- `industry` plugins for routed business-model strategy/KPIs;
- `methodology` plugins for cross-industry research methods.

Stable compatible plugins are eligible for automatic resolution. Experimental plugins require explicit opt-in. Compatibility is enforced through `PluginManifest` using `CORE_API_VERSION = "1.0"`, plugin semantic version, Research OS compatibility range, declared `provides` / `requires`, business-model coverage, maturity, and priority.

A normal stock-research caller supplies the company/security and evidence, not a hand-selected industry plugin. The runtime routes the business model and resolves compatible plugins. If no compatible strategy exists, `StrategyResolution.coverage_gaps` records that limitation; the gap is never silently treated as PASS or COMPLETE.

See `docs/architecture/plugin-authoring-v1.md`.

## Repository map

- `src/research_os/runtime/` — canonical context, inputs, module graph, engine, factory, result, fingerprints and snapshot composition.
- `src/research_os/plugins/` — plugin manifests, registry, resolver, built-in providers and extension contracts.
- `src/research_os/knowledge/` — PIT-safe knowledge-provider interface.
- `src/research_os/preflight/` — exact repository identity and frozen-HEAD validation.
- `src/research_os/domain/` — Evidence, calculation lineage, assumption lineage and version contracts.
- `src/research_os/validation/` — financial unit, scale, arithmetic and consistency validation.
- `src/research_os/period/` — reporting-period semantics and period-aware turnover helpers.
- `src/research_os/completion/` — module status and final research completion gate.
- `src/research_os/router/` — explainable business-model classification.
- `src/research_os/kpi/` — reusable KPI contracts and built-in calculation packs.
- `src/research_os/capital/` — capital efficiency, evidence-aware funding loop and growth quality.
- `src/research_os/drivers/` — driver graph and ranking.
- `src/research_os/thesis/` — Thesis / Anti-Thesis / Falsifier state machine.
- `src/research_os/ledger/` — Evidence Ledger and conclusion validity horizons.
- `src/research_os/expectations/` — PIT expectation vintages, evidence validation and surprise decomposition.
- `src/research_os/forecasting/` — hypothesis registration, model promotion and forecast-error attribution.
- `src/research_os/valuation/` — model fitness, routing and execution validation.
- `src/research_os/decision/` — deterministic research-state engine and legal state validation.
- `src/research_os/reporting/` — reporting read models derived from canonical runtime results.
- `src/research_os/version.py` — centralized `RESEARCH_OS_VERSION` and `CORE_API_VERSION`.
- `alembic/` — schema/governance migrations; v1.4.0 adds no new database migration.
- `docs/superpowers/specs/` and `docs/superpowers/plans/` — approved architecture designs and implementation plans.

The legacy `src/research_os/orchestration.py` and duplicate KPI registry policy surface are intentionally removed in v1.4.0.

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

The release script retains its historical filename for compatibility, reads the current package version, and evaluates both the earlier correctness gates and the v1.4 architecture gates.

## Completion semantics

`FINAL_STATUS` has only two machine-readable values: `COMPLETE` or `INCOMPLETE`. `ResearchCompletionGate` owns this policy. Reporting may display the result but cannot independently promote or demote it. Missing required evidence, unsupported strategy/KPI coverage, unknown funding classification, or unsupported claimed capabilities remain visible as module statuses, coverage gaps, or blockers.

## Snapshot and version governance

`src/research_os/version.py` defines `RESEARCH_OS_VERSION = "1.4.0"` and `CORE_API_VERSION = "1.0"`. `research_os.__version__`, `pyproject.toml`, and `research_os_version.json` must agree with the runtime version.

Each research snapshot separately freezes dataset, parser, formula, router, KPI pack, driver, forecast, valuation, report and OS versions plus payload hash and component fingerprints. Historical snapshots and released tags remain immutable.

## Migration

No database migration is required for v1.4.0. Code that imports the deleted legacy orchestrator or duplicate KPI registry must migrate to `ResearchRuntimeFactory` and the canonical plugin/runtime contracts. Reporting code must pass `ResearchRunResult` to `DecisionSummaryBuilder` rather than an arbitrary status dictionary.

See `docs/migrations/v1.4.0.md`, `docs/architecture/plugin-authoring-v1.md`, `CHANGELOG.md`, and the v1.4 canonical-runtime design/plan under `docs/superpowers/`.
