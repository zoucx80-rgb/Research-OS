# Research OS v1.1 Master Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver Research OS v1.1 as a backward-compatible, testable investment-research platform that preserves v1.0 PIT/lineage/financial-model rigor while adding business-model routing, driver/thesis reasoning, expectation gaps, model fitness, decision states, and learning loops.

**Architecture:** Build v1.1 as six independently releasable workstreams over one shared Python/PostgreSQL domain model. Each workstream owns explicit interfaces and tests; later workstreams consume only published interfaces from earlier ones. v1.0 manufacturing logic is migrated into a versioned Manufacturing KPI Pack rather than rewritten.

**Tech Stack:** Python 3.12+, Pydantic v2, SQLAlchemy 2.x, PostgreSQL, Alembic, pandas/numpy, statsmodels, scikit-learn, FastAPI, pytest, Hypothesis, ruff, mypy.

**Spec:** `/mnt/data/Research_OS_v1.1_完整规范.md`

## Global Constraints

- No Time Travel: every historical feature must satisfy `source_publish_ts <= decision_ts`.
- No Fabricated Data: missing disclosed detail remains missing; no interpolation to manufacture quarterly detail.
- Confidence grades are exactly `A|B|C|D|E`.
- Research signals and decision states must never become automatic trade orders.
- Raw evidence is immutable; corrections create new revisions.
- Every material claim must be traceable to evidence and version metadata.
- Complex forecasting models must beat a simple benchmark out of sample before promotion.
- Research snapshots freeze OS/data/parser/formula/router/KPI/forecast/valuation/report versions.
- v1.0 calculation semantics remain backward-compatible unless an explicit migration changes a versioned formula.

---

## Delivery Order

1. **Evidence + PIT + Versioning Foundation**
2. **Business Model Router + KPI Pack Registry**
3. **Driver Tree + Thesis/Anti-Thesis + Evidence Ledger**
4. **Expectation + Forecast Validation + Valuation Router**
5. **Decision Engine + Monitoring/Learning + API**
6. **v1.0 Migration + Golden Validation + v1.1 Release Gate**

Each child plan is independently executable and has its own test cycle:

- `2026-08-29-research-os-v1-1-01-evidence-versioning.md`
- `2026-08-29-research-os-v1-1-02-router-kpi-packs.md`
- `2026-08-29-research-os-v1-1-03-driver-thesis-ledger.md`
- `2026-08-29-research-os-v1-1-04-expectation-forecast-valuation.md`
- `2026-08-29-research-os-v1-1-05-decision-monitoring-api.md`
- `2026-08-29-research-os-v1-1-06-migration-release.md`

## Repository Shape Locked by This Plan

```text
research-os/
├── pyproject.toml
├── alembic.ini
├── alembic/
│   └── versions/
├── src/research_os/
│   ├── domain/
│   │   ├── enums.py
│   │   ├── evidence.py
│   │   └── versions.py
│   ├── storage/
│   │   ├── db.py
│   │   └── models.py
│   ├── snapshots/
│   │   └── service.py
│   ├── router/
│   │   ├── models.py
│   │   ├── classifier.py
│   │   └── registry.py
│   ├── kpi/
│   │   ├── base.py
│   │   ├── manufacturing.py
│   │   └── distributor.py
│   ├── capital/
│   │   └── engine.py
│   ├── events/
│   │   └── engine.py
│   ├── peers/
│   │   ├── models.py
│   │   └── normalization.py
│   ├── drivers/
│   │   ├── models.py
│   │   ├── graph.py
│   │   └── ranking.py
│   ├── thesis/
│   │   ├── models.py
│   │   ├── state_machine.py
│   │   └── service.py
│   ├── ledger/
│   │   └── service.py
│   ├── expectations/
│   │   ├── models.py
│   │   └── surprise.py
│   ├── forecasting/
│   │   ├── hypotheses.py
│   │   ├── promotion.py
│   │   └── errors.py
│   ├── valuation/
│   │   ├── fitness.py
│   │   └── router.py
│   ├── decision/
│   │   ├── models.py
│   │   └── engine.py
│   ├── monitoring/
│   │   ├── postmortem.py
│   │   ├── drift.py
│   │   └── calibration.py
│   ├── reporting/
│   │   └── summary.py
│   └── api/
│       ├── app.py
│       └── routes/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── golden/
│   └── fixtures/
└── docs/
    ├── architecture/
    └── migrations/
```

## Cross-Plan Interfaces

```python
# evidence
EvidenceStore.as_of(company_id: str, decision_ts: datetime) -> list[Evidence]

# routing
BusinessModelRouter.classify(company_id: str, evidence: list[Evidence]) -> BusinessModelProfile
KpiPackRegistry.resolve(profile: BusinessModelProfile) -> list[KpiPack]

# drivers/thesis
DriverGraph.build(company_id: str, pack_ids: list[str], evidence: list[Evidence]) -> DriverGraphResult
ThesisService.evaluate(company_id: str, evidence: list[Evidence], drivers: DriverGraphResult) -> list[Thesis]

# expectations/valuation
ExpectationService.snapshot(company_id: str, decision_ts: datetime) -> ExpectationSnapshot
ValuationRouter.route(context: ValuationContext) -> ValuationRoutingResult

# decision
DecisionEngine.evaluate(context: DecisionContext) -> DecisionStateRecord

# reproducibility
SnapshotService.freeze(company_id: str, decision_ts: datetime, versions: VersionBundle) -> ResearchSnapshot
```

## Master Release Milestones

### M1 — Foundation Alpha
Evidence store, PIT queries, immutable revisions, version bundle, research snapshot.

### M2 — Research Semantics Alpha
Router, Manufacturing/Distributor packs, Driver Tree, Thesis/Falsifier, Evidence Ledger.

### M3 — Decision Semantics Beta
Expectation gaps, forecast promotion, valuation fitness, decision states.

### M4 — Learning Beta
Post-mortem, drift detection, API read surfaces.

### M5 — v1.1 Stable
v1.0 golden tests pass; Manufacturing Pack reproduces legacy outputs; Distributor Pack completes a full run; all v1.1 release gates pass.

## Execution Rule

Do not start a later child plan until the earlier plan's public interfaces and tests are green. Each task must end in a small commit and a reviewer gate.
