# Research OS v1.1

Research OS v1.1 is a Point-in-Time, evidence-linked investment research operating system. It preserves the v1.0 financial-analysis discipline while adding business-model routing, KPI packs, driver graphs, Thesis/Anti-Thesis/Falsifiers, expectation vintages, valuation model fitness, research decision states, and monitoring/learning loops.

## Core invariants

- No time travel: only evidence with `publish_ts <= decision_ts` may enter a run.
- No fabricated data: missing facts remain missing.
- Facts, calculations, statistical evidence, and assumptions retain A–E confidence semantics.
- Material metrics and claims carry evidence lineage and version metadata.
- Forecast models must beat simple out-of-sample benchmarks before production promotion.
- Decision states are research outputs, never automatic trade orders.

## Repository map

- `src/research_os/orchestration.py` — one-shot `ResearchOS.complete_run()` orchestration.
- `src/research_os/domain/` — Evidence and version contracts.
- `src/research_os/router/` — explainable business-model classification.
- `src/research_os/kpi/` — Core, Manufacturing, and Distributor KPI packs.
- `src/research_os/capital/` — ROIC, incremental ROIC, IWCR, funding loop, growth-quality components.
- `src/research_os/drivers/` — driver graph and ranking.
- `src/research_os/thesis/` — Thesis / Anti-Thesis / Falsifier state machine.
- `src/research_os/ledger/` — Evidence Ledger and conclusion validity horizons.
- `src/research_os/expectations/` — PIT expectation vintages and surprise decomposition.
- `src/research_os/forecasting/` — hypothesis registration, model promotion, forecast-error attribution.
- `src/research_os/valuation/` — model fitness and valuation routing.
- `src/research_os/decision/` — deterministic research-state engine.
- `src/research_os/events/`, `monitoring/`, `peers/`, `reporting/` — update, learning, comparison, and read models.
- `alembic/` — v1.1 database schema and governance tables.
- `docs/specs/` — approved v1.1 specification.
- `docs/superpowers/plans/` — implementation plans.

## Local verification

The execution environment used for this build is offline. If build isolation attempts to download packages, use the locally installed build backend:

```bash
python -m pip install -e . --no-deps --no-build-isolation
pytest -q
python scripts/release_gate_v1_1.py
```

Database migration smoke test:

```bash
DATABASE_URL=sqlite:///research_os.db alembic -c alembic.ini upgrade head
DATABASE_URL=sqlite:///research_os.db alembic -c alembic.ini downgrade base
```

## Version governance

The OS follows semantic versions (`MAJOR.MINOR.PATCH`). Every research snapshot freezes dataset, parser, formula, router, KPI pack, driver, forecast, valuation, report, and OS versions plus a SHA-256 payload hash.

See `CHANGELOG.md`, `research_os_version.json`, and `docs/migrations/v1.0-to-v1.1.md`.
