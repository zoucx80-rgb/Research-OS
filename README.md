# Research OS v1.2

Research OS v1.2 is a Point-in-Time, evidence-linked investment research operating system with machine-enforced research completion safety gates. It preserves the v1.1 business-model routing, KPI packs, driver graphs, Thesis/Anti-Thesis/Falsifiers, expectation vintages, valuation fitness, decision states, and monitoring loops while adding hard validation boundaries for repository identity, financial arithmetic, expectation evidence, valuation execution, temporal consistency, and final research completion.

## Core invariants

- No time travel: only evidence with `publish_ts <= decision_ts` may enter a run.
- No fabricated data: missing facts remain missing and may surface as `INSUFFICIENT_EVIDENCE`.
- Facts, calculations, statistical evidence, and assumptions remain distinct.
- Material metrics and claims carry evidence lineage and version metadata; raw and normalized Evidence values survive storage round trips.
- Financial unit/scale corruption is a hard failure before valuation or decision generation.
- Market-expectation conclusions require a traceable expectation baseline.
- Selected valuation models must match executed models and retain assumptions, lineage, and driver bridges.
- Decision states are research outputs, never automatic trade orders.
- Tool completion is not research completion: only the Completion Gate may emit `FINAL_STATUS=COMPLETE`.

## Repository map

- `src/research_os/orchestration.py` — one-shot `ResearchOS.complete_run()` orchestration and safety-gate composition.
- `src/research_os/preflight/` — exact repository identity and frozen-HEAD validation.
- `src/research_os/domain/` — Evidence, calculation lineage, assumption lineage, and version contracts.
- `src/research_os/validation/` — financial unit, scale, arithmetic, and consistency validation.
- `src/research_os/completion/` — module status and final research completion gate.
- `src/research_os/router/` — explainable business-model classification.
- `src/research_os/kpi/` — Core, Manufacturing, and Distributor KPI packs.
- `src/research_os/capital/` — ROIC, incremental ROIC, IWCR, funding loop, growth-quality components.
- `src/research_os/drivers/` — driver graph and ranking.
- `src/research_os/thesis/` — Thesis / Anti-Thesis / Falsifier state machine.
- `src/research_os/ledger/` — Evidence Ledger and conclusion validity horizons.
- `src/research_os/expectations/` — PIT expectation vintages, evidence validation, and surprise decomposition.
- `src/research_os/forecasting/` — hypothesis registration, model promotion, forecast-error attribution.
- `src/research_os/valuation/` — model fitness, routing, and execution validation.
- `src/research_os/decision/` — deterministic research-state engine and legal state validation.
- `src/research_os/events/`, `monitoring/`, `peers/`, `reporting/` — update, learning, comparison, validation-aware read models.
- `alembic/` — schema/governance migrations including v1.2 Evidence-lineage persistence.
- `docs/specs/` — v1.1 full specification plus v1.2 safety-gate increment.
- `docs/superpowers/plans/` — implementation plans.

## Local verification

```bash
python -m pip install -e . --no-deps --no-build-isolation
pytest -q tests/integration/storage/test_v1_2_lineage_migration.py
pytest -q
python scripts/release_gate_v1_1.py
```

The release script retains its historical filename for compatibility but reads the current package version and validates the v1.2 release gate.

Database migration smoke test:

```bash
DATABASE_URL=sqlite:///research_os.db alembic -c alembic.ini upgrade head
DATABASE_URL=sqlite:///research_os.db alembic -c alembic.ini downgrade 0002_v1_1_semantics
DATABASE_URL=sqlite:///research_os.db alembic -c alembic.ini upgrade head
```

## Completion semantics

`FINAL_STATUS` is machine-readable and has only two values: `COMPLETE` or `INCOMPLETE`. A completed report cannot contain an illegal Research Decision State or present unsupported expectation/valuation conclusions as validated. Missing required evidence must remain visible instead of being inferred from narrative context.

## Version governance

The OS follows semantic versions (`MAJOR.MINOR.PATCH`). Every research snapshot freezes dataset, parser, formula, router, KPI pack, driver, forecast, valuation, report, and OS versions plus a SHA-256 payload hash. Historical snapshots and release tags are immutable.

See `CHANGELOG.md`, `research_os_version.json`, `docs/specs/Research_OS_v1.2_安全门禁增量规范.md`, and `docs/migrations/v1.1-to-v1.2.md`.
