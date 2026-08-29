# Research OS v1.1 Driver, Thesis & Evidence Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Represent company value drivers as an evidence-linked graph, maintain thesis/anti-thesis with observable falsifiers, and record material claims in an auditable Evidence Ledger.

**Architecture:** Driver graphs are deterministic domain objects, not causal claims by default. Thesis state transitions are governed by an explicit state machine; every active thesis must have at least one falsifier and next verification event.

**Tech Stack:** Python 3.12+, Pydantic v2, networkx optional for traversal only, pytest.

**Spec:** `/mnt/data/Research_OS_v1.1_完整规范.md`

## Global Constraints

- A Driver Tree expresses an economic mechanism; it does not itself prove causality.
- Every critical driver must link to evidence.
- Every active thesis requires an anti-thesis/falsifier path.
- Material claim language must carry A-E confidence grade.
- Thesis transitions are append-only events.

---

### Task 1: Implement driver nodes, edges, and graph validation

**Files:**
- Create: `src/research_os/drivers/models.py`
- Create: `src/research_os/drivers/graph.py`
- Test: `tests/unit/drivers/test_graph.py`

**Interfaces:**
- Produces: `DriverNode`, `DriverEdge`, `DriverGraphResult`, `DriverGraph.validate()`.
- Consumes: pack IDs and evidence IDs.

- [ ] **Step 1: Write failing orphan-driver test**

```python
def test_critical_driver_without_evidence_is_invalid():
    graph = DriverGraph(
        nodes=[DriverNode(
            driver_id="demand",
            name="AI demand",
            driver_type="demand",
            critical=True,
            evidence_ids=[],
        )],
        edges=[],
    )
    with pytest.raises(DriverValidationError):
        graph.validate()
```

- [ ] **Step 2: Run test and verify failure**

Run: `pytest tests/unit/drivers/test_graph.py -v`  
Expected: FAIL.

- [ ] **Step 3: Implement typed graph objects**

Required edge relations: `positive`, `negative`, `nonlinear`, `conditional`.

- [ ] **Step 4: Implement validation**

Validation fails when:
- a critical node has no evidence;
- an edge references a missing node;
- `lag_quarters < 0`;
- relation is outside the allowed enum.

- [ ] **Step 5: Run tests and commit**

Run: `pytest tests/unit/drivers/test_graph.py -v`  
Expected: PASS.

```bash
git add src/research_os/drivers tests/unit/drivers
git commit -m "feat: add evidence-linked driver graph"
```

### Task 2: Implement driver priority ranking

**Files:**
- Create: `src/research_os/drivers/ranking.py`
- Test: `tests/unit/drivers/test_ranking.py`

**Interfaces:**
- Produces: `rank_drivers(nodes) -> list[RankedDriver]`.
- Consumes: materiality, uncertainty, observability, decision relevance.

- [ ] **Step 1: Write failing ranking test**

```python
def test_priority_is_product_of_four_components():
    ranked = rank_drivers([
        scored_driver("a", 0.9, 0.8, 0.7, 0.6),
        scored_driver("b", 0.5, 0.5, 1.0, 1.0),
    ])
    assert ranked[0].driver_id == "a"
    assert ranked[0].score == pytest.approx(0.9 * 0.8 * 0.7 * 0.6)
```

- [ ] **Step 2: Implement bounded score validation**

Each component must be between 0 and 1.

- [ ] **Step 3: Run tests and commit**

Run: `pytest tests/unit/drivers/test_ranking.py -v`  
Expected: PASS.

```bash
git add src/research_os/drivers/ranking.py tests/unit/drivers/test_ranking.py
git commit -m "feat: rank decision-relevant drivers"
```

### Task 3: Implement thesis model and state machine

**Files:**
- Create: `src/research_os/thesis/models.py`
- Create: `src/research_os/thesis/state_machine.py`
- Test: `tests/unit/thesis/test_state_machine.py`

**Interfaces:**
- Produces: `Thesis`, `Falsifier`, `ThesisStatus`, `transition_thesis()`.
- Consumes: evidence/driver references.

- [ ] **Step 1: Write failing active-thesis validation test**

```python
def test_active_thesis_requires_falsifier_and_next_check():
    with pytest.raises(ValueError):
        Thesis(
            thesis_id="t1",
            company_id="001287.SZ",
            title="AI demand drives profitable growth",
            statement="...",
            mechanism="...",
            status="active",
            falsifiers=[],
            next_check_date=None,
        )
```

- [ ] **Step 2: Implement statuses**

Allowed states:

```text
new, active, strengthening, weakening, falsified, expired
```

- [ ] **Step 3: Implement legal transitions**

```python
LEGAL = {
    "new": {"active", "expired"},
    "active": {"strengthening", "weakening", "falsified", "expired"},
    "strengthening": {"active", "weakening", "falsified", "expired"},
    "weakening": {"active", "strengthening", "falsified", "expired"},
    "falsified": set(),
    "expired": set(),
}
```

- [ ] **Step 4: Add irreversible falsified-state test**

Run: `pytest tests/unit/thesis/test_state_machine.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/research_os/thesis tests/unit/thesis
git commit -m "feat: add falsifiable thesis state machine"
```

### Task 4: Implement ThesisService evaluation contract

**Files:**
- Create: `src/research_os/thesis/service.py`
- Test: `tests/unit/thesis/test_service.py`

**Interfaces:**
- Produces: `ThesisService.evaluate(company_id, evidence, drivers) -> list[Thesis]`.
- Consumes: `DriverGraphResult`, evidence.

- [ ] **Step 1: Write failing falsifier-trigger test**

```python
def test_falsifier_moves_active_thesis_to_weakening(service, active_thesis):
    evidence = [
        metric("revenue_yoy", 0.40),
        metric("inventory_to_revenue_change", 0.12),
        metric("dso_change_days", 25),
        metric("cfo", -100),
    ]
    result = service.evaluate_existing(active_thesis, evidence)
    assert result.status in {"weakening", "falsified"}
```

- [ ] **Step 2: Implement falsifier predicates as explicit callables/config rules**

No LLM-only transition may alter persisted thesis status.

- [ ] **Step 3: Run tests and commit**

Run: `pytest tests/unit/thesis/test_service.py -v`  
Expected: PASS.

```bash
git add src/research_os/thesis/service.py tests/unit/thesis/test_service.py
git commit -m "feat: evaluate thesis falsifiers from evidence"
```

### Task 5: Implement Evidence Ledger claims

**Files:**
- Create: `src/research_os/ledger/service.py`
- Test: `tests/unit/ledger/test_ledger.py`

**Interfaces:**
- Produces: `Claim`, `EvidenceLedger.add_claim()`, `EvidenceLedger.validate_claim()`.
- Consumes: evidence IDs, confidence grade, formula/model references, falsifiers.

- [ ] **Step 1: Write failing unsupported-claim test**

```python
def test_material_claim_requires_evidence(ledger):
    with pytest.raises(ClaimValidationError):
        ledger.add_claim(
            claim_id="c1",
            company_id="001287.SZ",
            claim_text="Growth is debt funded",
            claim_type="risk",
            confidence_grade="B",
            evidence_ids=[],
        )
```

- [ ] **Step 2: Implement the claim schema**

A material claim stores:
`claim_text`, `claim_type`, `confidence_grade`, `evidence_ids`, `formula_or_model`, `assumptions`, `falsifiers`, `valid_from`, `valid_until`, `status`.

- [ ] **Step 3: Add expiry test**

```python
def test_expired_claim_is_not_current(ledger, expired_claim):
    assert ledger.current_claims("001287.SZ", as_of="2026-09-30") == []
```

- [ ] **Step 4: Run tests and commit**

Run: `pytest tests/unit/ledger/test_ledger.py -v`  
Expected: PASS.

```bash
git add src/research_os/ledger tests/unit/ledger
git commit -m "feat: add auditable evidence ledger"
```
