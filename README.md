# Research OS v1.2.1

Research OS v1.2.1 is a Point-in-Time, evidence-linked investment research operating system with machine-enforced research completion safety gates. This PATCH release preserves the v1.2 architecture while hardening period arithmetic, missing-value semantics, KPI applicability, completion consistency and version governance.

## Core invariants

- No time travel: only evidence with `publish_ts <= decision_ts` may enter a run.
- No fabricated data: missing facts remain missing and may surface as `INSUFFICIENT_EVIDENCE`; `None` is never silently treated as economic zero.
- Facts, calculations, statistical evidence, and assumptions remain distinct.
- Material metrics and claims carry evidence lineage and version metadata; raw and normalized Evidence values survive storage round trips.
- Financial unit/scale corruption is a hard failure before valuation or decision generation.
- Period-sensitive balance/flow metrics use explicit reporting-period semantics. Interim periods do not silently assume 365 days; period turns and annualized turns are distinguished where applicable.
- Generic CorePack availability is infrastructure, not proof of specialized KPI coverage. A routed primary business model requires a specialized pack for `KPI Pack = PASS`.
- Funding-loop classification requires evidenced operands. Missing funding facts produce `unknown` / `INSUFFICIENT_EVIDENCE` rather than an invented financing state.
- Market-expectation conclusions require a traceable expectation baseline.
- Selected valuation models must match executed models and retain assumptions, lineage, and driver bridges.
- Decision states are research outputs, never automatic trade orders.
- Tool completion is not research completion: `ResearchCompletionGate` is the single completion-policy authority, and reporting propagates the same `ResearchCompletionResult`.

## Repository map

- `src/research_os/orchestration.py` — one-shot `ResearchOS.complete_run()` orchestration and safety-gate composition.
- `src/research_os/preflight/` — exact repository identity and frozen-HEAD validation.
- `src/research_os/domain/` — Evidence, calculation lineage, assumption lineage, and version contracts.
- `src/research_os/validation/` — financial unit, scale, arithmetic, and consistency validation.
- `src/research_os/period/` — reporting-period semantics and period-aware turnover helpers.
- `src/research_os/completion/` — module status and final research completion gate.
- `src/research_os/router/` — explainable business-model classification.
- `src/research_os/kpi/` — Core, Manufacturing, and Distributor KPI packs with applicability metadata.
- `src/research_os/capital/` — ROIC, incremental ROIC, IWCR, evidence-aware funding loop, growth-quality components.
- `src/research_os/drivers/` — driver graph and ranking.
- `src/research_os/thesis/` — Thesis / Anti-Thesis / Falsifier state machine.
- `src/research_os/ledger/` — Evidence Ledger and conclusion validity horizons.
- `src/research_os/expectations/` — PIT expectation vintages, evidence validation, and surprise decomposition.
- `src/research_os/forecasting/` — hypothesis registration, model promotion, forecast-error attribution.
- `src/research_os/valuation/` — model fitness, routing, and execution validation.
- `src/research_os/decision/` — deterministic research-state engine and legal state validation.
- `src/research_os/version.py` — centralized Python runtime version source.
- `src/research_os/events/`, `monitoring/`, `peers/`, `reporting/` — update, learning, comparison, validation-aware read models.
- `alembic/` — schema/governance migrations including v1.2 Evidence-lineage persistence; v1.2.1 adds no database migration.
- `docs/specs/` and `docs/superpowers/specs/` — release specifications and approved designs.
- `docs/superpowers/plans/` — implementation plans.

## Local verification

```bash
python -m pip install -e . --no-deps --no-build-isolation
pytest -q tests/regression/research_patterns/test_v1_2_1_correctness_patterns.py \
  tests/unit/kpi/test_period_sensitive_packs.py \
  tests/unit/capital/test_engine.py \
  tests/unit/kpi/test_applicability.py \
  tests/unit/completion/test_consistency.py \
  tests/unit/test_version_consistency_v1_2_1.py
pytest -q tests/integration/storage/test_v1_2_lineage_migration.py
pytest -q
python scripts/release_gate_v1_1.py
```

The release script retains its historical filename for compatibility, reads the current package version, and validates all existing v1.2 gates plus the v1.2.1 correctness checks.

Database migration smoke test remains the v1.2 lineage migration:

```bash
DATABASE_URL=sqlite:///research_os.db alembic -c alembic.ini upgrade head
DATABASE_URL=sqlite:///research_os.db alembic -c alembic.ini downgrade 0002_v1_1_semantics
DATABASE_URL=sqlite:///research_os.db alembic -c alembic.ini upgrade head
```

## Completion semantics

`FINAL_STATUS` is machine-readable and has only two values: `COMPLETE` or `INCOMPLETE`. `ResearchCompletionGate` owns this policy. Reporting may display the result but does not independently redefine COMPLETE. Missing required evidence, unsupported KPI coverage, unknown funding classification, or unsupported claimed capabilities remain visible in module status and blockers rather than being inferred from narrative context.

## Period semantics

For interim disclosures, the economic period must be explicit through period metadata or derivable dates before day-based ratios are computed. If an interim period length is unavailable, day-based metrics remain missing with an explicit reason. FY retains annual compatibility. Where turnover can be interpreted both within-period and annualized, the two forms are exposed separately.

## Version governance

`src/research_os/version.py` defines the Python runtime source `RESEARCH_OS_VERSION`. `research_os.__version__`, runtime defaults, `pyproject.toml`, and `research_os_version.json` must agree with it. Every research snapshot separately freezes dataset, parser, formula, router, KPI pack, driver, forecast, valuation, report, and OS versions plus a SHA-256 payload hash. Historical snapshots and release tags are immutable.

See `CHANGELOG.md`, `research_os_version.json`, `docs/specs/Research_OS_v1.2_安全门禁增量规范.md`, `docs/migrations/v1.1-to-v1.2.md`, and the v1.2.1 correctness-hardening design/plan under `docs/superpowers/`.
