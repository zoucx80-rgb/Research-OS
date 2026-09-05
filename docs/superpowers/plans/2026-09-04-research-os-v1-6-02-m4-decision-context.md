# Research OS 1.6.02 M4 Decision Context and Derivation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Decision Context from all available P0 canonical research states, remove the constant valuation-state path, and publish an auditable rule-level derivation for every decision.

**Architecture:** Add a single `DecisionContextBuilder` that translates canonical artifacts into the existing decision domain states and a new typed input assessment. Refactor `DecisionEngine` so one private rule evaluation powers both the backward-compatible `evaluate()` result and a new derivation-producing method. The Engine-executed Portfolio Decision module writes the existing decision artifacts plus additive input-assessment and derivation artifacts.

**Tech Stack:** Python 3.12, Pydantic v2, existing DecisionEngine/PolicyRegistry/ArtifactSnapshot, pytest, Hypothesis.

**Spec:** `docs/superpowers/specs/2026-09-04-research-os-v1-6-02-professional-research-semantic-closure-design.md`

**Execution note:** Per user instruction, all five tasks are delivered in one verified M4 commit rather than one commit per task.

## Global Constraints

- M1, M2, and M3 must be complete before M4 integration.
- Keep `decision.record@2.0` and `decision.state_provenance@2.0`; add `decision.input_assessment@2.0` and `decision.derivation@2.0`.
- Preserve existing `DecisionEngine.evaluate(context) -> DecisionStateRecord` for current callers.
- The builder, not the application module, owns normalized state derivation.
- A missing domain is explicitly represented as unavailable/unknown; it is never silently omitted.
- Funding risk and falsified thesis remain vetoes. Insufficient forecast cannot strengthen a state. Insufficient research evidence cannot be bypassed by thesis confidence.
- This milestone explains canonical inputs to current decision. Previous-run state transitions remain 1.6.03 scope.
- No buy/sell/order/position output is introduced.

---

## File Structure

- Create `src/research_os/decision/context.py` for `DecisionContextBuilder`.
- Modify `src/research_os/decision/models.py` for dimension assessment/derivation values and additive context fields.
- Modify `src/research_os/decision/engine.py` for shared rule evaluation and derivation output.
- Modify `src/research_os/decision/aggregation.py` and policy definitions for new typed gates.
- Modify `src/research_os/decision/__init__.py` for exports.
- Modify `src/research_os/application/plan.py` for Portfolio Decision wiring.
- Modify `src/research_os/runtime/core_artifacts.py` for two keys.
- Modify decision/reporting projectors in `_core.py`, `_registry.py`, `_shared.py`.
- Add unit/property/integration/regression tests under decision, runtime, reporting, and professional suites.

---

### Task 1: Add decision input and derivation contracts

**Files:**
- Modify: `src/research_os/decision/models.py`
- Modify: `src/research_os/decision/__init__.py`
- Test: `tests/unit/decision/test_context_contracts.py`

**Interfaces:**
- Consumes: artifact IDs, normalized dimension states, EvidenceRef.
- Produces: `DecisionDimensionAssessment`, `DecisionInputAssessment`, `DecisionDerivation`, additive `DecisionContext` fields.

- [x] **Step 1: Write RED contracts**

```python
def test_decision_assessment_rejects_duplicate_dimensions() -> None:
    item = dimension("forecast", "INSUFFICIENT_EVIDENCE")
    with pytest.raises(ValueError, match="unique"):
        DecisionInputAssessment(dimensions=(item, item), evidence_confidence=Decimal("0.5"))


def test_context_defaults_keep_existing_constructor_valid() -> None:
    context = legacy_decision_context()
    assert context.forecast_state == "UNKNOWN"
    assert context.sufficiency_state == "INSUFFICIENT_EVIDENCE"
    assert context.scenario_state == "UNAVAILABLE"
```

- [x] **Step 2: Implement additive contracts**

```python
class DecisionDimensionAssessment(LineageValue):
    dimension: str
    state: str
    availability: Literal["AVAILABLE", "INSUFFICIENT_EVIDENCE", "NOT_APPLICABLE"]
    artifact_ids: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()


class DecisionInputAssessment(DomainArtifact):
    dimensions: tuple[DecisionDimensionAssessment, ...] = ()
    evidence_confidence: Decimal = Field(ge=0, le=1)
    blocking_reason_codes: tuple[str, ...] = ()

    def require_dimension(self, dimension: str) -> DecisionDimensionAssessment: ...


class DecisionDerivation(DomainArtifact):
    rule_id: str
    rule_version: str
    input_states: tuple[DecisionDimensionAssessment, ...]
    output_state: ResearchDecisionState
    supporting_reason_codes: tuple[str, ...] = ()
    blocking_reason_codes: tuple[str, ...] = ()
    used_thesis_ids: tuple[str, ...] = ()
    used_claim_ids: tuple[str, ...] = ()
```

Extend `DecisionContext` with defaults:

```python
forecast_state: Literal["PASS", "FAIL", "INSUFFICIENT_EVIDENCE", "UNKNOWN"] = "UNKNOWN"
sufficiency_state: Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"
scenario_state: Literal["AVAILABLE", "UNAVAILABLE", "ADVERSE"] = "UNAVAILABLE"
```

Canonicalize dimensions/reasons/IDs and collect lineage deterministically.

- [x] **Step 3: Run and commit**

```bash
pytest -q tests/unit/decision/test_context_contracts.py tests/unit/decision/test_models.py
git add src/research_os/decision/models.py src/research_os/decision/__init__.py tests/unit/decision/test_context_contracts.py
git commit -m "feat: add decision derivation contracts"
```

### Task 2: Build Decision Context from canonical artifacts

**Files:**
- Create: `src/research_os/decision/context.py`
- Test: `tests/unit/decision/test_context_builder.py`
- Test: `tests/property/decision/test_context_determinism.py`

**Interfaces:**
- Consumes: `ResearchContext`, `ResearchStateView`, M1-M3 and existing thesis/funding/expectation/semantic artifacts.
- Produces: `DecisionContextBuilder.build(context, state) -> tuple[DecisionContext, DecisionInputAssessment]`.

- [x] **Step 1: Write valuation/funding RED**

```python
def test_market_gap_drives_valuation_state() -> None:
    context, assessment = DecisionContextBuilder().build(run_context(), state_with_market_gap("UNDERVALUED"))
    assert context.valuation_state == "CHEAP"
    assert assessment.require_dimension("valuation_market_gap").state == "UNDERVALUED"


def test_material_funding_risk_is_preserved() -> None:
    context, _ = DecisionContextBuilder().build(run_context(), state_with_debt_funded_negative_ocf())
    assert context.material_funding_risk is True
```

- [x] **Step 2: Write missingness/determinism RED**

```python
def test_missing_scenario_is_explicit() -> None:
    context, assessment = DecisionContextBuilder().build(run_context(), state_without_sensitivity())
    assert context.scenario_state == "UNAVAILABLE"
    assert assessment.require_dimension("scenario").availability == "INSUFFICIENT_EVIDENCE"


@given(st.permutations(canonical_envelopes()))
def test_context_is_order_independent(envelopes) -> None:
    assert build_from(envelopes) == build_from(canonical_envelopes())
```

- [x] **Step 3: Implement explicit dimension mapping**

Build these dimensions in stable order:

```text
financial_temporal
capital_efficiency
funding_loop
thesis_portfolio
semantic_signals
expectation_gap
forecast_quality
valuation_reconciliation
valuation_market_gap
scenario
research_sufficiency
```

Map `UNDERVALUED -> CHEAP`, `FAIR -> FAIR`, `OVERVALUED -> EXPENSIVE`, all unsupported states to `UNRELIABLE`. Derive fundamental state from temporal evidence, funding, capital efficiency, and semantic signals with explicit reason codes; never interpret a generic rising cost metric as improvement. Evidence confidence is the minimum supported thesis confidence bounded by sufficiency; no primary thesis yields zero.

- [x] **Step 4: Run and commit**

```bash
pytest -q tests/unit/decision/test_context_builder.py tests/property/decision/test_context_determinism.py
git add src/research_os/decision/context.py tests/unit/decision/test_context_builder.py tests/property/decision/test_context_determinism.py
git commit -m "feat: build decision context from artifacts"
```

### Task 3: Refactor DecisionEngine to emit derivation without duplicate rules

**Files:**
- Modify: `src/research_os/decision/engine.py`
- Modify: `src/research_os/decision/aggregation.py`
- Modify: `src/research_os/policies/builtins.py`
- Test: `tests/unit/decision/test_engine_v1_6_02.py`
- Test: `tests/unit/decision/test_aggregation.py`

**Interfaces:**
- Consumes: `DecisionContext`, `DecisionInputAssessment`.
- Produces: existing `evaluate(context)` and new `evaluate_with_derivation(context, assessment)`.

- [x] **Step 1: Write RED veto/promotion tests**

```python
def test_insufficient_sufficiency_blocks_conviction() -> None:
    record, derivation = engine().evaluate_with_derivation(high_confidence_context(sufficiency_state="INSUFFICIENT_EVIDENCE"), assessment())
    assert record.state == "INSUFFICIENT_EVIDENCE"
    assert "RESEARCH_SUFFICIENCY_BLOCKED" in derivation.blocking_reason_codes


def test_failed_forecast_cannot_produce_high_conviction() -> None:
    record, _ = engine().evaluate_with_derivation(confirming_context(forecast_state="FAIL"), assessment())
    assert record.state != "HIGH_CONVICTION_WATCH"
```

- [x] **Step 2: Extract one private rule evaluator**

```python
class _RuleOutcome(NamedTuple):
    state: ResearchDecisionState
    rule_id: str
    supporting_reasons: tuple[str, ...]
    blocking_reasons: tuple[str, ...]
```

Both public methods call `_evaluate_rule(context)`. `evaluate()` converts the outcome to the existing record. `evaluate_with_derivation()` returns that same record plus a `DecisionDerivation`; it must not evaluate the rule table twice.

- [x] **Step 3: Apply rule precedence**

Required precedence:

```text
insufficient material evidence
  -> falsified thesis
  -> material funding risk
  -> unresolved portfolio conflict
  -> deteriorating fundamentals
  -> multi-dimension confirmation with forecast PASS
  -> cheap and improving
  -> confirmation required
  -> hold and monitor
```

Version the rule policy as `decision_aggregation@2.0.2`; thresholds remain in PolicyRegistry.

- [x] **Step 4: Run compatibility and GREEN tests**

```bash
pytest -q tests/unit/decision tests/integration/runtime/test_portfolio_decision.py
git add src/research_os/decision/engine.py src/research_os/decision/aggregation.py src/research_os/policies/builtins.py tests/unit/decision
git commit -m "feat: derive decisions through versioned rules"
```

### Task 4: Wire additive decision artifacts into Portfolio Decision

**Files:**
- Modify: `src/research_os/runtime/core_artifacts.py`
- Modify: `src/research_os/application/plan.py`
- Test: `tests/integration/runtime/test_decision_context_v1_6_02.py`
- Test: `tests/regression/professional/test_v1_6_02_decision_context.py`

**Interfaces:**
- Consumes: all builder inputs and sufficiency.
- Produces: existing decision record/provenance plus `DECISION_INPUT_ASSESSMENT`, `DECISION_DERIVATION`.

- [x] **Step 1: Write runtime RED**

```python
def test_portfolio_decision_publishes_every_consumed_dimension() -> None:
    result = run_command(full_professional_command())
    assessment = result.artifacts.require(DECISION_INPUT_ASSESSMENT)
    derivation = result.artifacts.require(DECISION_DERIVATION)
    assert set(item.dimension for item in assessment.dimensions) >= REQUIRED_DECISION_DIMENSIONS
    assert derivation.output_state == result.artifacts.require(DECISION_RECORD).state
```

The three-company regression asserts: 300034 distinguishes temporal improvement, model disagreement, market gap, and insufficiency; 001287 retains `RISK_REVIEW` when the quantitative funding bridge proves material funding risk; 301073 is re-evaluated after hospitality resolution but remains fail-closed for missing industry evidence. It never requires a buy/sell or optimistic state.

- [x] **Step 2: Register keys and update module spec**

```python
DECISION_INPUT_ASSESSMENT = ArtifactKey(
    artifact_id="decision.input_assessment", schema_version="2.0", value_type=DecisionInputAssessment
)
DECISION_DERIVATION = ArtifactKey(
    artifact_id="decision.derivation", schema_version="2.0", value_type=DecisionDerivation
)
```

Add M1-M3 artifact keys to `PortfolioDecisionModule.spec.requires`; replace its private state helpers with `DecisionContextBuilder`; write all four decision artifacts from the same record/assessment/derivation.

- [x] **Step 3: Run and commit**

```bash
pytest -q tests/integration/runtime/test_decision_context_v1_6_02.py tests/regression/professional/test_v1_6_02_decision_context.py tests/unit/contracts/test_core_artifacts.py tests/unit/snapshots tests/property/snapshots
git add src/research_os/runtime/core_artifacts.py src/research_os/application/plan.py tests/integration/runtime/test_decision_context_v1_6_02.py tests/regression/professional/test_v1_6_02_decision_context.py
git commit -m "feat: publish decision context and derivation"
```

### Task 5: Project Decision derivation and add M4 gate

**Files:**
- Modify: `src/research_os/reporting/projectors/_core.py`
- Modify: `src/research_os/reporting/projectors/_registry.py`
- Modify: `src/research_os/reporting/projectors/_shared.py`
- Create: `tests/unit/reporting/test_v1_6_02_decision.py`
- Modify: `src/research_os/release/verification.py`
- Modify: `tests/regression/architecture/test_release_governance.py`

**Interfaces:**
- Consumes: decision assessment/derivation.
- Produces: decision-first human projection and pack `v1-6-02-decision-context`.

- [x] **Step 1: Write projector and no-trading RED**

```python
def test_decision_projection_explains_support_blockers_and_upgrade_evidence() -> None:
    payload = project_artifact("decision.derivation", derivation()).payload
    assert payload["形成规则"]
    assert payload["支持因素"]
    assert payload["阻塞因素"]
    assert not any(term in str(payload) for term in ("下单", "买入数量", "目标仓位"))
```

- [x] **Step 2: Implement the projection**

Render normalized dimension labels, rule ID/version, support/block reason labels, and output state. Do not derive a new decision summary in the projector.

- [x] **Step 3: Register the verification pack**

```python
_V1_6_02_DECISION_CHECKS = {
    "v1_6_02_decision_unit": "tests/unit/decision",
    "v1_6_02_decision_property": "tests/property/decision",
    "v1_6_02_decision_runtime": "tests/integration/runtime/test_decision_context_v1_6_02.py",
    "v1_6_02_decision_field": "tests/regression/professional/test_v1_6_02_decision_context.py",
    "v1_6_02_decision_reporting": "tests/unit/reporting/test_v1_6_02_decision.py",
}
```

Register but do not select the pack before M6.

- [x] **Step 4: Run M4 exit gate and commit**

```bash
pytest -q tests/unit/decision tests/property/decision tests/integration/runtime/test_portfolio_decision.py tests/integration/runtime/test_decision_context_v1_6_02.py tests/regression/professional/test_v1_6_02_decision_context.py tests/unit/reporting/test_v1_6_02_decision.py tests/regression/architecture/test_release_governance.py
python -m ruff check src/research_os/decision src/research_os/application/plan.py tests/unit/decision
git diff --check
git add src/research_os/reporting/projectors tests/unit/reporting/test_v1_6_02_decision.py src/research_os/release/verification.py tests/regression/architecture/test_release_governance.py
git commit -m "test: gate v1.6.02 decision context"
```
