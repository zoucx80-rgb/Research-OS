# Research OS v1.1 Decision, Monitoring & API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert evidence/thesis/expectation/valuation states into research-only decision states, then add post-mortem/drift monitoring and stable read APIs.

**Architecture:** Decision evaluation is deterministic and explainable; it consumes persisted subsystem outputs rather than raw data. Monitoring closes the loop after new filings. FastAPI exposes read-only v1.1 research surfaces first.

**Tech Stack:** Python 3.12+, Pydantic v2, FastAPI, SQLAlchemy, pytest.

**Spec:** `/mnt/data/Research_OS_v1.1_完整规范.md`

## Global Constraints

- Decision outputs are research states, never trade orders.
- Every persisted decision state links to supporting evidence/claims.
- Material thesis transitions trigger post-mortem records.
- API responses include version and decision timestamp.

---

### Task 1: Define decision-state domain model

**Files:**
- Create: `src/research_os/decision/models.py`
- Test: `tests/unit/decision/test_models.py`

**Interfaces:**
- Produces: fundamental, valuation, expectation, thesis, and decision-state enums.
- Consumes: none.

- [ ] **Step 1: Write failing allowed-state test**

```python
def test_decision_state_is_research_only():
    state = DecisionStateRecord(
        company_id="001287.SZ",
        state="WAIT_FOR_CONFIRMATION",
        decision_ts="2026-08-29T08:00:00+00:00",
        evidence_ids=["e1"],
    )
    assert "BUY" not in state.state
```

- [ ] **Step 2: Implement exact decision states**

```text
HIGH_CONVICTION_WATCH
ACCUMULATION_CANDIDATE
WAIT_FOR_CONFIRMATION
HOLD_AND_MONITOR
RISK_REVIEW
THESIS_BROKEN
INSUFFICIENT_EVIDENCE
```

- [ ] **Step 3: Run tests and commit**

Run: `pytest tests/unit/decision/test_models.py -v`  
Expected: PASS.

```bash
git add src/research_os/decision tests/unit/decision/test_models.py
git commit -m "feat: define research decision states"
```

### Task 2: Implement deterministic DecisionEngine

**Files:**
- Create: `src/research_os/decision/engine.py`
- Test: `tests/unit/decision/test_engine.py`

**Interfaces:**
- Produces: `DecisionEngine.evaluate(DecisionContext) -> DecisionStateRecord`.
- Consumes: subsystem states, confidence, evidence IDs.

- [ ] **Step 1: Write failing broken-thesis test**

```python
def test_falsified_thesis_forces_thesis_broken(engine):
    result = engine.evaluate(
        ctx(
            thesis_state="FALSIFIED",
            fundamental_state="DETERIORATING",
            valuation_state="CHEAP",
            expectation_state="MIXED",
            evidence_confidence=0.9,
        )
    )
    assert result.state == "THESIS_BROKEN"
```

- [ ] **Step 2: Implement precedence rules**

Required precedence:
1. insufficient evidence;
2. falsified thesis;
3. material risk review;
4. confirmation/monitoring states;
5. high-conviction watch candidates.

Cheap valuation must never override a falsified thesis.

- [ ] **Step 3: Add explainability payload**

Every result includes:

```text
reason_codes
supporting_claim_ids
evidence_ids
research_os_version
decision_ts
```

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/unit/decision/test_engine.py -v`  
Expected: PASS.

```bash
git add src/research_os/decision/engine.py tests/unit/decision/test_engine.py
git commit -m "feat: evaluate explainable decision states"
```

### Task 3: Implement research post-mortem

**Files:**
- Create: `src/research_os/monitoring/postmortem.py`
- Test: `tests/unit/monitoring/test_postmortem.py`

**Interfaces:**
- Produces: `ResearchPostMortem`.
- Consumes: previous snapshot, current evidence, forecast error records, thesis transitions.

- [ ] **Step 1: Write failing post-mortem completeness test**

```python
def test_postmortem_answers_five_required_questions(service):
    p = service.build(previous_snapshot, current_snapshot)
    assert p.forecast_hit_summary is not None
    assert p.driver_errors is not None
    assert p.thesis_changes is not None
    assert p.valuation_error_ranking is not None
    assert p.process_change_candidates is not None
```

- [ ] **Step 2: Implement deterministic aggregation**

Post-mortem stores data-supported answers; narrative generation can be a later rendering layer.

- [ ] **Step 3: Run tests and commit**

Run: `pytest tests/unit/monitoring/test_postmortem.py -v`  
Expected: PASS.

```bash
git add src/research_os/monitoring/postmortem.py tests/unit/monitoring
git commit -m "feat: close research loop with postmortems"
```

### Task 4: Implement business/model drift detection

**Files:**
- Create: `src/research_os/monitoring/drift.py`
- Test: `tests/unit/monitoring/test_drift.py`

**Interfaces:**
- Produces: `DriftAlert`.
- Consumes: historical/current feature distributions and profile scores.

- [ ] **Step 1: Write failing router-reclassification test**

```python
def test_material_business_mix_change_requests_router_review():
    alert = detect_business_model_drift(
        previous={"distributor_score": 0.92, "manufacturer_score": 0.08},
        current={"distributor_score": 0.55, "manufacturer_score": 0.45},
        threshold=0.25,
    )
    assert alert.requires_router_review is True
```

- [ ] **Step 2: Implement threshold-based v1.1 drift**

Use explicit score deltas; do not introduce opaque unsupervised ML in v1.1.

- [ ] **Step 3: Run tests and commit**

Run: `pytest tests/unit/monitoring/test_drift.py -v`  
Expected: PASS.

```bash
git add src/research_os/monitoring/drift.py tests/unit/monitoring/test_drift.py
git commit -m "feat: detect research model drift"
```

### Task 5: Expose read-only FastAPI v1.1 endpoints

**Files:**
- Create: `src/research_os/api/app.py`
- Create: `src/research_os/api/routes/research.py`
- Test: `tests/integration/api/test_research_routes.py`

**Interfaces:**
- Produces:
  - `GET /companies/{id}/business-model`
  - `GET /companies/{id}/drivers`
  - `GET /companies/{id}/kpi-pack`
  - `GET /companies/{id}/capital-efficiency`
  - `GET /companies/{id}/theses`
  - `GET /companies/{id}/expectations`
  - `GET /companies/{id}/valuation/fitness`
  - `GET /companies/{id}/decision-state`
  - `GET /companies/{id}/evidence-ledger`
  - `GET /companies/{id}/research-snapshot`

- [ ] **Step 1: Write failing decision endpoint test**

```python
def test_decision_endpoint_returns_version_and_timestamp(client):
    r = client.get("/companies/001287.SZ/decision-state")
    assert r.status_code == 200
    body = r.json()
    assert "research_os_version" in body
    assert "decision_ts" in body
    assert "state" in body
```

- [ ] **Step 2: Implement router dependencies**

Routes call services only; they do not calculate financial metrics directly.

- [ ] **Step 3: Run API tests**

Run: `pytest tests/integration/api/test_research_routes.py -v`  
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/research_os/api tests/integration/api
git commit -m "feat: expose research os v1.1 read APIs"
```


### Task 6: Implement Event Engine and materiality mapping

**Files:**
- Create: `src/research_os/events/engine.py`
- Test: `tests/unit/events/test_engine.py`

**Interfaces:**
- Produces: `ResearchEvent`, `EventImpact`, `EventEngine.map_impact()`.
- Consumes: evidence/event payload plus current driver/thesis IDs.

- [ ] **Step 1: Write failing financing-event mapping test**

```python
def test_financing_event_maps_to_funding_and_dilution_drivers(engine):
    impact = engine.map_impact(
        event(
            event_type="share_issue",
            company_id="X",
            amount=3.0,
        )
    )
    assert "financing" in impact.affected_driver_types
    assert impact.materiality in {"medium", "high"}
```

- [ ] **Step 2: Implement exact event types**

Support:
`financial_report`, `guidance`, `major_order`, `capacity`, `pricing`, `raw_material`, `financing`, `share_issue`, `buyback`, `management_change`, `regulation`, `customer`, `supplier`, `industry_price`, `consensus_revision`.

- [ ] **Step 3: Implement impact payload**

Every event impact includes:
`affected_drivers`, `affected_theses`, `materiality`, `direction`, `confidence_grade`, `next_required_check`.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/unit/events/test_engine.py -v`  
Expected: PASS.

```bash
git add src/research_os/events tests/unit/events
git commit -m "feat: map research events to drivers and theses"
```

### Task 7: Implement peer roles and comparison normalization

**Files:**
- Create: `src/research_os/peers/models.py`
- Create: `src/research_os/peers/normalization.py`
- Test: `tests/unit/peers/test_normalization.py`

**Interfaces:**
- Produces: `PeerRole`, `ComparableMetric`, `normalize_peer_metric()`.
- Consumes: company metric, peer metric, accounting/time/scope metadata.

- [ ] **Step 1: Write failing incompatible-period test**

```python
def test_peer_comparison_rejects_h1_vs_fy_without_normalization():
    with pytest.raises(PeerNormalizationError):
        normalize_peer_metric(
            left=metric(period_type="H1", scope="parent"),
            right=metric(period_type="FY", scope="consolidated"),
        )
```

- [ ] **Step 2: Implement peer roles**

Allowed:
`direct_competitor`, `business_model_peer`, `supply_chain_peer`, `valuation_peer`, `capital_efficiency_peer`.

- [ ] **Step 3: Implement comparison compatibility checks**

Require explicit matching or normalization for:
`accounting_definition`, `period`, `frequency`, `scope`, `share_count_convention`, `business_model_interpretation`.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/unit/peers/test_normalization.py -v`  
Expected: PASS.

```bash
git add src/research_os/peers tests/unit/peers
git commit -m "feat: normalize evidence-based peer comparisons"
```

### Task 8: Implement probability calibration records

**Files:**
- Create: `src/research_os/monitoring/calibration.py`
- Test: `tests/unit/monitoring/test_calibration.py`

**Interfaces:**
- Produces: `ProbabilityForecast`, `CalibrationRecord`, `brier_score()`.
- Consumes: explicitly probabilistic research forecasts only.

- [ ] **Step 1: Write failing Brier-score test**

```python
def test_brier_score_for_binary_outcome():
    assert brier_score(probability=0.7, outcome=1) == pytest.approx(0.09)
```

- [ ] **Step 2: Implement bounded probability validation**

Reject probability outside `[0, 1]`.

- [ ] **Step 3: Keep calibration optional**

Non-probabilistic thesis records do not receive synthetic probabilities.

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/unit/monitoring/test_calibration.py -v`  
Expected: PASS.

```bash
git add src/research_os/monitoring/calibration.py tests/unit/monitoring/test_calibration.py
git commit -m "feat: record research probability calibration"
```

### Task 9: Build Decision Summary and standard report read-model

**Files:**
- Create: `src/research_os/reporting/summary.py`
- Test: `tests/unit/reporting/test_summary.py`

**Interfaces:**
- Produces: `DecisionSummary`, `ResearchReportModel`.
- Consumes: profile, ranked drivers, financial/capital results, theses, expectations, valuation, decision state, evidence ledger, version bundle.

- [ ] **Step 1: Write failing summary completeness test**

```python
def test_decision_summary_contains_required_front_page_fields(builder):
    s = builder.build(full_context())
    assert s.business_model
    assert s.primary_thesis
    assert len(s.top_drivers) <= 3
    assert len(s.top_risks) <= 3
    assert s.next_verification_event
    assert s.research_os_version == "1.1.0"
```

- [ ] **Step 2: Implement six page read-model sections**

The read model exposes:
`Decision`, `Drivers`, `FinancialCapital`, `ExpectationsForecast`, `Valuation`, `Evidence`.

- [ ] **Step 3: Implement standard deep-research section ordering**

Return sections in the v1.1 specification order, including Thesis, Anti-Thesis, Falsifiers, Expectation Gap, Monitoring Checklist, Evidence Ledger, and Version/Data Snapshot.

- [ ] **Step 4: Add unsupported-one-line-thesis guard**

The one-line core contradiction may only be emitted when at least one supporting claim exists in the ledger.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/unit/reporting/test_summary.py -v`  
Expected: PASS.

```bash
git add src/research_os/reporting tests/unit/reporting
git commit -m "feat: build v1.1 decision and report read models"
```
