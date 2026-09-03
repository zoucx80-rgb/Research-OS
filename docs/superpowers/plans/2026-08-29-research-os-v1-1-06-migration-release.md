# Research OS v1.1 Migration & Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate v1.0 semantics safely into v1.1, prove backward compatibility on manufacturing research, prove cross-model applicability on a distributor fixture, and enforce the v1.1 Stable release gate.

**Architecture:** Treat v1.0 as a golden-output contract. Migration is additive: existing facts/formulas stay valid, while manufacturing-specific orchestration moves into a pack. Stable release requires both legacy reproducibility and a complete Distributor Research Run.

**Tech Stack:** Python 3.12+, pytest, PostgreSQL/Alembic, existing finance-core functions.

**Spec:** `/mnt/data/Research_OS_v1.1_完整规范.md`

## Global Constraints

- Do not overwrite v1.0 snapshots.
- Formula changes require a new formula version.
- Migration scripts are idempotent.
- Legacy manufacturing golden values must remain reproducible.
- Distributor validation must exercise Router → KPI → Driver → Thesis → Expectations → Valuation → Decision → Snapshot.

---

### Task 1: Create explicit v1.0-to-v1.1 migration map

**Files:**
- Create: `docs/migrations/v1.0-to-v1.1.md`
- Create: `src/research_os/migrations/v1_0_to_v1_1.py`
- Test: `tests/unit/migrations/test_v1_0_to_v1_1.py`

**Interfaces:**
- Produces: `migrate_snapshot_metadata()`.
- Consumes: legacy snapshot metadata.

- [ ] **Step 1: Write failing metadata migration test**

```python
def test_legacy_snapshot_gets_explicit_v1_0_defaults():
    migrated = migrate_snapshot_metadata(
        {
            "dataset_version": "2026-08-25.2",
            "formula_version": "finance-core@1.8.0",
            "valuation_version": "valuation@1.3.2",
            "report_version": "gaona-template@2.1",
        }
    )
    assert migrated["research_os_version"] == "1.0.0"
    assert migrated["router_version"] == "legacy-manufacturing-default"
```

- [ ] **Step 2: Implement pure metadata migration**

Never mutate historical calculated values.

- [ ] **Step 3: Document field mapping**

The migration document must list each v1.0 field, v1.1 destination, default, and whether the transformation is reversible.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/unit/migrations/test_v1_0_to_v1_1.py -v`  
Expected: PASS.

```bash
git add docs/migrations src/research_os/migrations tests/unit/migrations
git commit -m "feat: map v1.0 snapshots into v1.1 governance"
```

### Task 2: Build manufacturing golden regression suite

**Files:**
- Create: `tests/fixtures/manufacturing_legacy_snapshot.json`
- Create: `tests/golden/test_v1_0_manufacturing_reproducibility.py`

**Interfaces:**
- Produces: release-blocking golden contract.
- Consumes: Manufacturing Pack and legacy fixture.

- [ ] **Step 1: Freeze expected legacy outputs**

Include at minimum:
- DuPont factors;
- Shapley sum equals ΔROE;
- OCF/NP;
- AR days;
- inventory days;
- simple FCF;
- fixed-asset turnover;
- PE target algebra;
- EV-to-equity reconciliation.

- [ ] **Step 2: Run golden suite before any allowed tolerance change**

Run: `pytest tests/golden/test_v1_0_manufacturing_reproducibility.py -v`  
Expected: PASS. Any mismatch is a release blocker unless accompanied by a new formula version and approved migration note.

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/manufacturing_legacy_snapshot.json tests/golden/test_v1_0_manufacturing_reproducibility.py
git commit -m "test: freeze v1.0 manufacturing outputs"
```

### Task 3: Build complete Distributor Research Run fixture

**Files:**
- Create: `tests/fixtures/distributor_full_run.json`
- Create: `tests/integration/test_distributor_complete_run.py`

**Interfaces:**
- Produces: end-to-end proof of v1.1 semantics.
- Consumes: all public service interfaces from plans 1-5.

- [ ] **Step 1: Write the full pipeline test**

```python
def test_distributor_research_run_is_complete(os_services, distributor_fixture):
    evidence = os_services.evidence.load_fixture(distributor_fixture)
    profile = os_services.router.classify("001287.SZ", evidence)
    packs = os_services.kpi_registry.resolve(profile)
    metrics = os_services.metrics.calculate(packs, evidence)
    drivers = os_services.drivers.build("001287.SZ", [p.pack_id for p in packs], evidence)
    theses = os_services.theses.evaluate("001287.SZ", evidence, drivers)
    expectations = os_services.expectations.snapshot("001287.SZ", distributor_fixture.decision_ts)
    valuation = os_services.valuation.route_from(metrics, theses, expectations)
    decision = os_services.decision.evaluate_from(metrics, theses, expectations, valuation)
    snapshot = os_services.snapshots.freeze_from_run(decision)

    assert profile.primary_model == "distributor"
    assert any(m.metric_id == "ccc_days" for m in metrics)
    assert all(t.falsifiers for t in theses if t.status == "active")
    assert valuation.primary_models
    assert decision.evidence_ids
    assert snapshot.versions.research_os_version == "1.1.0"
```

- [ ] **Step 2: Run and verify the pipeline**

Run: `pytest tests/integration/test_distributor_complete_run.py -v`  
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/distributor_full_run.json tests/integration/test_distributor_complete_run.py
git commit -m "test: prove distributor complete research run"
```

### Task 4: Encode v1.1 release gate

**Files:**
- Create: `scripts/release_gate_v1_1.py`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/unit/release/test_release_gate.py`

**Interfaces:**
- Produces: exit code 0 only when every v1.1 Stable condition passes.
- Consumes: test reports and configuration.

- [ ] **Step 1: Write failing release-gate test**

```python
def test_release_gate_rejects_missing_distributor_run():
    result = evaluate_release_gate(
        {
            "v1_golden": True,
            "pit": True,
            "manufacturing": True,
            "distributor": False,
            "router_explainable": True,
            "thesis_falsifiers": True,
            "ledger": True,
            "valuation_fitness": True,
            "decision_no_trade": True,
            "snapshot_reproducible": True,
        }
    )
    assert result.ready is False
```

- [ ] **Step 2: Implement exact Stable conditions**

All ten conditions from the v1.1 specification are required; there is no partial Stable release.

- [ ] **Step 3: Wire CI**

CI final job runs:

```bash
python scripts/release_gate_v1_1.py
```

after unit, integration, and golden suites.

- [ ] **Step 4: Run full gate**

Run: `ruff check . && mypy src && pytest -q && python scripts/release_gate_v1_1.py`  
Expected: exit code 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/release_gate_v1_1.py .github/workflows/ci.yml tests/unit/release
git commit -m "build: enforce research os v1.1 stable gate"
```

### Task 5: Publish v1.1.0 version manifest and changelog

**Files:**
- Create: `CHANGELOG.md`
- Create: `research_os_version.json`
- Create: `docs/architecture/research-os-v1.1.md`

**Interfaces:**
- Produces: human/machine-readable release metadata.
- Consumes: finalized module versions.

- [ ] **Step 1: Create version manifest**

```json
{
  "research_os_version": "1.1.0",
  "status": "stable",
  "module_versions": {
    "finance_core": "2.0.0",
    "router": "1.0.0",
    "driver_engine": "1.0.0",
    "thesis_engine": "1.0.0",
    "expectation_engine": "1.0.0",
    "valuation": "2.0.0",
    "report_template": "3.0.0"
  }
}
```

- [ ] **Step 2: Add changelog headings**

Use exactly:
`Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, `Validation`, `Migration`, `Known Limitations`.

- [ ] **Step 3: Run documentation/version consistency test**

Run: `pytest tests/unit/release/test_release_gate.py -v`  
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md research_os_version.json docs/architecture/research-os-v1.1.md
git commit -m "docs: publish research os v1.1.0 manifest"
```
