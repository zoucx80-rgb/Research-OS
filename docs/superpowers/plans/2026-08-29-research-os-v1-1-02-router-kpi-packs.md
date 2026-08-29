# Research OS v1.1 Router & KPI Packs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route each company to evidence-backed business-model profiles and load versioned KPI packs, with Manufacturing and Distributor as the first production packs.

**Architecture:** Start with deterministic, explainable classification rules plus versioned manual override. KPI packs implement a common protocol and return typed metric results; pack-specific logic never leaks into the router.

**Tech Stack:** Python 3.12+, Pydantic v2, pandas, pytest.

**Spec:** `/mnt/data/Research_OS_v1.1_完整规范.md`

## Global Constraints

- Classification must include supporting evidence.
- Manual overrides are versioned and auditable.
- Multi-model profiles are supported.
- Missing KPI inputs produce missing results, not synthetic values.
- v1.0 manufacturing calculations retain existing formula versions.

---

### Task 1: Define BusinessModelProfile and explainable router

**Files:**
- Create: `src/research_os/router/models.py`
- Create: `src/research_os/router/classifier.py`
- Test: `tests/unit/router/test_classifier.py`

**Interfaces:**
- Produces: `BusinessModelProfile`, `BusinessModelRouter.classify()`.
- Consumes: `list[Evidence]`.

- [ ] **Step 1: Write a failing distributor classification test**

```python
def test_router_classifies_high_inventory_low_fixed_asset_company_as_distributor(router):
    profile = router.classify(
        "001287.SZ",
        evidence=[
            metric("inventory_to_revenue", 0.28),
            metric("fixed_asset_to_assets", 0.01),
            metric("gross_margin", 0.03),
            statement("business_description", "electronic component distribution"),
        ],
    )
    assert profile.primary_model == "distributor"
    assert profile.confidence >= 0.80
    assert profile.evidence_ids
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/unit/router/test_classifier.py -v`  
Expected: FAIL because router does not exist.

- [ ] **Step 3: Implement the typed profile**

```python
class BusinessModelProfile(BaseModel):
    company_id: str
    primary_model: str
    secondary_models: list[str] = []
    confidence: float
    evidence_ids: list[str]
    router_version: str
    manual_override: bool = False
```

- [ ] **Step 4: Implement deterministic scoring**

The first production router must score explicit evidence features and return the top model; do not introduce ML classification in v1.1.

- [ ] **Step 5: Run tests**

Run: `pytest tests/unit/router/test_classifier.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/research_os/router tests/unit/router
git commit -m "feat: add explainable business model router"
```

### Task 2: Add versioned manual override

**Files:**
- Modify: `src/research_os/router/models.py`
- Create: `src/research_os/router/registry.py`
- Test: `tests/unit/router/test_override.py`

**Interfaces:**
- Produces: `RouterOverrideRegistry.set_override()` and `resolve()`.
- Consumes: `BusinessModelProfile`.

- [ ] **Step 1: Write the failing audit test**

```python
def test_manual_override_preserves_previous_classification(registry):
    registry.set_override("X", "manufacturer", reason="segment changed", effective_at="2026-08-29")
    history = registry.history("X")
    assert history[-1].reason == "segment changed"
    assert history[-1].manual_override is True
```

- [ ] **Step 2: Run the test**

Run: `pytest tests/unit/router/test_override.py -v`  
Expected: FAIL.

- [ ] **Step 3: Implement append-only override records**

Each override stores:

```text
company_id, old_model, new_model, reason, effective_at, created_at, actor, router_version
```

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/unit/router/test_override.py -v`  
Expected: PASS.

```bash
git add src/research_os/router tests/unit/router/test_override.py
git commit -m "feat: version business model overrides"
```

### Task 3: Define KpiPack protocol and registry

**Files:**
- Create: `src/research_os/kpi/base.py`
- Modify: `src/research_os/router/registry.py`
- Test: `tests/unit/kpi/test_registry.py`

**Interfaces:**
- Produces: `KpiPack`, `MetricResult`, `KpiPackRegistry.resolve()`.
- Consumes: `BusinessModelProfile`.

- [ ] **Step 1: Write the failing registry test**

```python
def test_distributor_profile_loads_distributor_pack(registry):
    packs = registry.resolve(
        BusinessModelProfile(
            company_id="001287.SZ",
            primary_model="distributor",
            confidence=0.9,
            evidence_ids=["e1"],
            router_version="router@1.0.0",
        )
    )
    assert [p.pack_id for p in packs] == ["core", "distributor"]
```

- [ ] **Step 2: Implement the protocol**

```python
class MetricResult(BaseModel):
    metric_id: str
    value: float | None
    unit: str | None
    status: str
    formula_version: str
    evidence_ids: list[str]

class KpiPack(Protocol):
    pack_id: str
    pack_version: str
    required_facts: frozenset[str]
    optional_facts: frozenset[str]
    def calculate(self, facts: Mapping[str, float | None]) -> list[MetricResult]: ...
```

- [ ] **Step 3: Implement registry resolution**

`core` loads for every non-financial company; primary and secondary model packs load after it with duplicate pack IDs removed.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/unit/kpi/test_registry.py -v`  
Expected: PASS.

```bash
git add src/research_os/kpi src/research_os/router/registry.py tests/unit/kpi
git commit -m "feat: add versioned KPI pack registry"
```

### Task 4: Migrate Manufacturing Pack without formula drift

**Files:**
- Create: `src/research_os/kpi/manufacturing.py`
- Test: `tests/golden/kpi/test_manufacturing_pack.py`

**Interfaces:**
- Produces: `ManufacturingPack.calculate()`.
- Consumes: v1.0 formula functions or exact copied formula-versioned implementations.

- [ ] **Step 1: Add golden fixtures for DuPont, cash conversion, AR days, inventory days, FCF, Capex intensity, fixed-asset turnover**

- [ ] **Step 2: Run golden test and verify failure before pack exists**

Run: `pytest tests/golden/kpi/test_manufacturing_pack.py -v`  
Expected: FAIL.

- [ ] **Step 3: Implement pack as a thin orchestrator over v1.0 calculation functions**

Do not rewrite formulas inside the pack.

- [ ] **Step 4: Run golden tests**

Run: `pytest tests/golden/kpi/test_manufacturing_pack.py -v`  
Expected: all legacy expected values match exactly within existing tolerances.

- [ ] **Step 5: Commit**

```bash
git add src/research_os/kpi/manufacturing.py tests/golden/kpi
git commit -m "refactor: move manufacturing metrics into KPI pack"
```

### Task 5: Implement Distributor Pack

**Files:**
- Create: `src/research_os/kpi/distributor.py`
- Test: `tests/unit/kpi/test_distributor_pack.py`

**Interfaces:**
- Produces: DSO, DIO, DPO, CCC, NWC intensity, incremental NWC intensity, short-debt ratios, interest/gross-profit, cash conversion, ROIC.
- Consumes: financial facts.

- [ ] **Step 1: Write failing CCC test**

```python
def test_ccc_equals_dso_plus_dio_minus_dpo():
    result = DistributorPack().calculate({
        "avg_ar": 100,
        "revenue": 1000,
        "avg_inventory": 200,
        "cogs": 900,
        "avg_ap": 150,
    })
    values = {m.metric_id: m.value for m in result}
    assert values["ccc_days"] == pytest.approx(
        values["dso_days"] + values["dio_days"] - values["dpo_days"]
    )
```

- [ ] **Step 2: Run test**

Run: `pytest tests/unit/kpi/test_distributor_pack.py::test_ccc_equals_dso_plus_dio_minus_dpo -v`  
Expected: FAIL.

- [ ] **Step 3: Implement exact formulas**

```python
def days(avg_balance: float | None, flow: float | None) -> float | None:
    if avg_balance is None or flow is None or flow <= 0:
        return None
    return avg_balance / flow * 365.0
```

Use it for DSO/DIO/DPO; calculate CCC only when all three exist.

- [ ] **Step 4: Add no-fabrication test**

```python
def test_missing_ap_keeps_dpo_and_ccc_missing():
    values = metric_map(DistributorPack().calculate({
        "avg_ar": 100, "revenue": 1000,
        "avg_inventory": 200, "cogs": 900,
        "avg_ap": None,
    }))
    assert values["dpo_days"] is None
    assert values["ccc_days"] is None
```

- [ ] **Step 5: Run all distributor tests**

Run: `pytest tests/unit/kpi/test_distributor_pack.py -v`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/research_os/kpi/distributor.py tests/unit/kpi/test_distributor_pack.py
git commit -m "feat: add distributor capital-efficiency metrics"
```


### Task 6: Implement general CapitalEfficiencyEngine and Funding Loop

**Files:**
- Create: `src/research_os/capital/engine.py`
- Test: `tests/unit/capital/test_engine.py`

**Interfaces:**
- Produces: `CapitalEfficiencyResult`, `FundingLoopResult`, `CapitalEfficiencyEngine.calculate()`.
- Consumes: normalized NOPAT, invested capital, NWC, revenue, debt, interest, cash-flow inputs.

- [ ] **Step 1: Write failing ROIC and incremental-ROIC tests**

```python
def test_roic_and_incremental_roic_use_average_and_incremental_capital():
    r = CapitalEfficiencyEngine().calculate({
        "nopat": 12.0,
        "invested_capital_begin": 90.0,
        "invested_capital_end": 110.0,
        "nopat_prev": 9.0,
        "invested_capital_prev": 90.0,
    })
    assert r.roic == pytest.approx(12.0 / 100.0)
    assert r.incremental_roic == pytest.approx((12.0 - 9.0) / (110.0 - 90.0))
```

- [ ] **Step 2: Run and verify failure**

Run: `pytest tests/unit/capital/test_engine.py -v`  
Expected: FAIL because the capital engine is missing.

- [ ] **Step 3: Implement capital-efficiency formulas**

```python
def safe_ratio(num: float | None, den: float | None) -> float | None:
    if num is None or den is None or den == 0:
        return None
    return num / den
```

Use:
- `ROIC = NOPAT / AverageInvestedCapital`
- `IncrementalROIC = ΔNOPAT / ΔInvestedCapital`
- `IWCR = ΔNWC / ΔRevenue`

If a denominator is zero or missing, return `None` plus a status code; do not invent a value.

- [ ] **Step 4: Write failing funding-state test**

```python
def test_growth_with_large_nwc_and_debt_increase_is_debt_funded():
    r = CapitalEfficiencyEngine().funding_loop({
        "delta_revenue": 100.0,
        "delta_nwc": 60.0,
        "delta_debt": 55.0,
        "delta_equity": 0.0,
        "operating_cash_flow": -20.0,
    })
    assert r.funding_state == "debt_funded"
```

- [ ] **Step 5: Implement explicit funding states**

Allowed:
`self_funded`, `mixed`, `debt_funded`, `equity_funded`, `stressed`.

Classification rules must be configuration-backed and include reason codes such as:
`HIGH_IWCR`, `DEBT_FUNDS_NWC`, `NEGATIVE_OCF`, `EQUITY_DILUTION`.

- [ ] **Step 6: Add GrowthQuality components**

Return the component values separately:
`growth`, `margin`, `roic`, `cash_conversion`, `incremental_nwc_efficiency`, `leverage_deterioration`, `dilution`.

Do not collapse to a single score unless weights are explicitly configured and versioned.

- [ ] **Step 7: Run tests and commit**

Run: `pytest tests/unit/capital/test_engine.py -v`  
Expected: PASS.

```bash
git add src/research_os/capital tests/unit/capital
git commit -m "feat: add capital efficiency and funding loop engine"
```
