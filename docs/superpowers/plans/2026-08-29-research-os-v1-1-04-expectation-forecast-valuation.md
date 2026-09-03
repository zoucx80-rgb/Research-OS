# Research OS v1.1 Expectation, Forecast & Valuation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PIT consensus vintages, earnings-surprise decomposition, hypothesis/model promotion rules, and valuation model-fitness routing.

**Architecture:** Expectations are immutable vintages keyed by `as_of`; forecasts are promoted through explicit lifecycle states only after OOS benchmark tests; valuation routes models by fitness rather than mechanical averaging.

**Tech Stack:** Python 3.12+, pandas, numpy, statsmodels, scikit-learn, Pydantic v2, pytest.

**Spec:** `/mnt/data/Research_OS_v1.1_完整规范.md`

## Global Constraints

- Consensus used in historical analysis must have `as_of <= decision_ts`.
- Actual and expected periods must match.
- Forecast models cannot reach PRODUCTION unless they beat a simple OOS benchmark.
- Low-fitness valuation models cannot dominate the primary valuation range.

---

### Task 1: Implement consensus vintages and PIT expectation snapshots

**Files:**
- Create: `src/research_os/expectations/models.py`
- Test: `tests/unit/expectations/test_vintage.py`

**Interfaces:**
- Produces: `ConsensusVintage`, `ExpectationSnapshot`.
- Consumes: source forecasts and `decision_ts`.

- [ ] **Step 1: Write failing PIT vintage test**

```python
def test_expectation_snapshot_uses_latest_vintage_known_at_decision_time(service):
    service.add(vintage(as_of="2026-05-01", net_profit=2.5))
    service.add(vintage(as_of="2026-08-26", net_profit=2.1))
    snap = service.snapshot("300034.SZ", decision_ts="2026-05-15")
    assert snap.net_profit == 2.5
```

- [ ] **Step 2: Implement immutable vintages and `snapshot()` selection**

Use latest `as_of` not later than `decision_ts`.

- [ ] **Step 3: Run test and commit**

Run: `pytest tests/unit/expectations/test_vintage.py -v`  
Expected: PASS.

```bash
git add src/research_os/expectations tests/unit/expectations/test_vintage.py
git commit -m "feat: add point-in-time consensus vintages"
```

### Task 2: Implement surprise decomposition

**Files:**
- Create: `src/research_os/expectations/surprise.py`
- Test: `tests/unit/expectations/test_surprise.py`

**Interfaces:**
- Produces: `SurpriseResult`.
- Consumes: period-matched actuals and expectations.

- [ ] **Step 1: Write failing headline-beat/quality-miss test**

```python
def test_profit_beat_with_cfo_miss_is_mixed_quality():
    r = decompose_surprise(
        actual={"net_profit": 5.1, "cfo": -175, "inventory": 183},
        expected={"net_profit": 4.5, "cfo": -40, "inventory": 130},
        period="2026H1",
    )
    assert r.net_profit_surprise > 0
    assert r.cfo_surprise < 0
    assert r.label == "HEADLINE_BEAT_QUALITY_MISS"
```

- [ ] **Step 2: Implement period validation and surprise math**

Reject mismatched reporting periods.

- [ ] **Step 3: Run tests and commit**

Run: `pytest tests/unit/expectations/test_surprise.py -v`  
Expected: PASS.

```bash
git add src/research_os/expectations/surprise.py tests/unit/expectations/test_surprise.py
git commit -m "feat: decompose earnings expectation gaps"
```

### Task 3: Add hypothesis registry and model promotion

**Files:**
- Create: `src/research_os/forecasting/hypotheses.py`
- Create: `src/research_os/forecasting/promotion.py`
- Test: `tests/unit/forecasting/test_promotion.py`

**Interfaces:**
- Produces: `Hypothesis`, `ModelStage`, `PromotionDecision`.
- Consumes: benchmark/OOS metrics and PIT compliance flag.

- [ ] **Step 1: Write failing non-beating-model test**

```python
def test_model_cannot_promote_if_it_does_not_beat_naive():
    d = decide_promotion(
        current_stage="candidate",
        model_mae=12.0,
        benchmark_mae=10.0,
        pit_compliant=True,
        stable=True,
    )
    assert d.next_stage == "candidate"
    assert "benchmark" in d.reason
```

- [ ] **Step 2: Implement model stages**

```text
experimental, candidate, validated, production, degraded, retired
```

- [ ] **Step 3: Implement promotion gates**

To reach `production` require:
- PIT compliance;
- OOS metric better than benchmark;
- stability flag true;
- hypothesis registered before model run.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/unit/forecasting/test_promotion.py -v`  
Expected: PASS.

```bash
git add src/research_os/forecasting tests/unit/forecasting
git commit -m "feat: govern forecast model promotion"
```

### Task 4: Implement forecast error attribution record

**Files:**
- Create: `src/research_os/forecasting/errors.py`
- Test: `tests/unit/forecasting/test_errors.py`

**Interfaces:**
- Produces: `ForecastErrorRecord`.
- Consumes: prediction, actual, driver deltas.

- [ ] **Step 1: Write failing closed-period error test**

```python
def test_closed_forecast_records_absolute_error():
    record = close_forecast(
        metric="revenue",
        predicted=100,
        actual=92,
        period="2026Q3",
        attribution="demand_error",
    )
    assert record.error == -8
    assert record.absolute_error == 8
```

- [ ] **Step 2: Implement allowed attribution categories**

`demand_error`, `price_error`, `margin_error`, `working_capital_error`, `financing_cost_error`, `model_structural_error`, `data_revision_error`.

- [ ] **Step 3: Run tests and commit**

Run: `pytest tests/unit/forecasting/test_errors.py -v`  
Expected: PASS.

```bash
git add src/research_os/forecasting/errors.py tests/unit/forecasting/test_errors.py
git commit -m "feat: attribute closed forecast errors"
```

### Task 5: Implement valuation fitness and routing

**Files:**
- Create: `src/research_os/valuation/fitness.py`
- Create: `src/research_os/valuation/router.py`
- Test: `tests/unit/valuation/test_router.py`

**Interfaces:**
- Produces: `ModelFitness`, `ValuationRoutingResult`, `ValuationRouter.route()`.
- Consumes: business model, data quality, earnings stability, cash-flow visibility, capital structure fit, forecast stability.

- [ ] **Step 1: Write failing DCF-downweight test**

```python
def test_distributor_with_volatile_fcf_does_not_use_dcf_as_primary():
    result = ValuationRouter().route(
        context(
            business_model="distributor",
            dcf=fitness(cash_flow_visibility=0.2),
            pe=fitness(earnings_stability=0.8),
            pb=fitness(capital_structure_fit=0.8),
        )
    )
    assert result.models["dcf"].status != "PRIMARY"
```

- [ ] **Step 2: Implement score**

```python
def fitness_score(x: ModelFitnessInputs) -> float:
    return (
        x.data_quality
        * x.earnings_stability
        * x.cash_flow_visibility
        * x.capital_structure_fit
        * x.business_model_fit
        * x.forecast_stability
    )
```

- [ ] **Step 3: Implement statuses**

`PRIMARY`, `SECONDARY`, `SANITY_CHECK`, `LOW_CONFIDENCE`, `NOT_APPLICABLE`.

- [ ] **Step 4: Add no-mechanical-average test**

The routing result must expose primary range and disagreement diagnosis; it must not expose a default arithmetic-average target.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/unit/valuation/test_router.py -v`  
Expected: PASS.

```bash
git add src/research_os/valuation tests/unit/valuation
git commit -m "feat: route valuation models by fitness"
```
