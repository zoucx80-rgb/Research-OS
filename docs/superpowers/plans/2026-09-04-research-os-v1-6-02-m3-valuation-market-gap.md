# Research OS 1.6.02 M3 Valuation Execution and Market Gap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute routed valuation methods through the controlled domain path, validate the results, bind a PIT market anchor, and publish a basis-compatible market gap that Decision can consume.

**Architecture:** Retain existing model fitness, routing, method implementations, execution validator, and reconciliation. Add typed execution requests and a small method registry so the application invokes those services rather than accepting only prebuilt outputs. Market data enters as a lineage-bound PIT value; a separate service compares it with the reconciled model band without placing market anchors inside reconciliation arithmetic.

**Tech Stack:** Python 3.12, Pydantic v2, Decimal, existing valuation services, pytest, Hypothesis.

**Spec:** `docs/superpowers/specs/2026-09-04-research-os-v1-6-02-professional-research-semantic-closure-design.md`

**Execution note:** Per user instruction, all five tasks are delivered in one verified M3 commit rather than one commit per task.

## Global Constraints

- M1 is required for final sufficiency integration; M2 is not a code dependency but its forecast quality later influences Decision.
- Keep existing valuation artifacts and add `valuation.market_anchor@2.0` and `valuation.market_gap@2.0`.
- Do not silently trust command-provided `ValuationExecution`; mark it externally supplied and validate it, or execute a typed request.
- All prices, model inputs, ranges, and gaps retain evidence/assumption lineage.
- Require `observed_ts <= available_ts <= decision_ts`; use the last valid trading observation, not a fabricated decision-date price.
- Require identical currency, per-share/total-value basis, share class, and corporate-action basis before comparison.
- Market anchor is excluded from `ValuationReconciler`; reconciliation measures model consistency, market gap measures price versus model band.
- Reporting only projects the canonical execution, anchor, and gap.

---

## File Structure

- Create `src/research_os/valuation/registry.py` for immutable built-in method lookup.
- Create `src/research_os/valuation/market.py` for PIT anchor/gap contracts and comparison service.
- Modify `src/research_os/valuation/execution.py` for typed execution request/service.
- Modify `src/research_os/valuation/__init__.py` for exports.
- Modify `src/research_os/application/command.py` for execution requests and market anchor.
- Modify `src/research_os/application/professional_modules/valuation_sensitivity.py` for controlled execution and gap publication.
- Modify `src/research_os/runtime/core_artifacts.py` and `src/research_os/application/plan.py` for new keys/dependencies.
- Modify `src/research_os/sufficiency/service.py` for valuation executability.
- Modify reporting `_market.py`, `_registry.py`, `_shared.py`.
- Add unit/property/integration/regression tests under valuation, runtime, reporting, and professional suites.

---

### Task 1: Add immutable valuation method registry

**Files:**
- Create: `src/research_os/valuation/registry.py`
- Modify: `src/research_os/valuation/__init__.py`
- Test: `tests/unit/valuation/test_registry.py`

**Interfaces:**
- Consumes: `PEMethod`, `PBMethod`, `DCFMethod`, `SOTPMethod`.
- Produces: `ValuationMethodRegistry.require(method_id)` and `builtin_valuation_method_registry()`.

- [x] **Step 1: Write registry RED**

```python
def test_builtin_registry_contains_supported_methods() -> None:
    registry = builtin_valuation_method_registry()
    assert tuple(item.method_id for item in registry.methods) == ("dcf", "pb", "pe", "sotp")
    assert registry.require("pe").method_id == "pe"


def test_conflicting_method_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate valuation method"):
        ValuationMethodRegistry((PEMethod(), PEMethod()))
```

- [x] **Step 2: Implement deterministic registry**

```python
class ValuationMethod(Protocol):
    method_id: str
    def execute(self, inputs: ValuationMethodInput) -> ValuationMethodResult: ...


class ValuationMethodRegistry:
    def __init__(self, methods: Iterable[ValuationMethod]) -> None: ...
    def get(self, method_id: str) -> ValuationMethod | None: ...
    def require(self, method_id: str) -> ValuationMethod: ...
```

Freeze sorted `methods`, reject duplicates, and raise `KeyError("unregistered valuation method: <id>")` for missing methods.

- [x] **Step 3: Run and commit**

```bash
pytest -q tests/unit/valuation/test_registry.py tests/unit/valuation/test_method_fitness_v2.py
git add src/research_os/valuation/registry.py src/research_os/valuation/__init__.py tests/unit/valuation/test_registry.py
git commit -m "feat: register valuation methods"
```

### Task 2: Add controlled valuation execution requests

**Files:**
- Modify: `src/research_os/valuation/execution.py`
- Modify: `src/research_os/application/command.py`
- Test: `tests/unit/valuation/test_controlled_execution.py`
- Test: `tests/unit/application/test_command.py`

**Interfaces:**
- Consumes: `ValuationMethodInput`, `ModelFitnessInputs`, funding state/reasons, method registry.
- Produces: `ValuationExecutionRequest` and `ControlledValuationExecutionService.execute(...)`.

- [x] **Step 1: Write RED**

```python
def test_controlled_execution_calls_selected_method_and_validator() -> None:
    result = service().execute(
        request=pe_request(),
        fitness=fully_supported_fitness(),
        business_model="manufacturing",
        funding_state="self_funded",
        funding_reason_codes=(),
    )
    assert result.validation.status == "PASS"
    assert result.execution.executed_model == "pe"
    assert result.execution.result.base_case == Decimal("20")
```

- [x] **Step 2: Implement request/result/service**

```python
class ValuationExecutionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    model_key: str
    method_input: ValuationMethodInput
    scenario_logic: str
    driver_bridge: tuple[str, ...] = ()


class ControlledValuationExecution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    execution: ValuationExecution
    validation: ValuationExecutionResult
```

`ControlledValuationExecutionService` must call `ValuationFitnessPolicy.assess`, execute only the request's registered model, build the existing domain `ValuationExecution`, and validate it with `ValuationExecutionValidator`. Do not execute a contraindicated method; return an insufficient domain execution with the fitness reason.

- [x] **Step 3: Add the command field**

```python
class ValuationResearchInput(_FrozenInput):
    models: tuple[ValuationModelInput, ...] = Field(default_factory=tuple)
    execution: ArtifactValuationExecution | None = None
    execution_requests: tuple[ValuationExecutionRequest, ...] = Field(default_factory=tuple)
    ranges: tuple[ValuationRange, ...] = Field(default_factory=tuple)
    rationales: tuple[ValuationRationale, ...] = Field(default_factory=tuple)
    market_anchor: PitMarketAnchor | None = None
```

Alias the existing artifact-value `ValuationExecution` import explicitly to avoid collision with `valuation.execution.ValuationExecution`.

- [x] **Step 4: Run and commit**

```bash
pytest -q tests/unit/valuation/test_controlled_execution.py tests/unit/valuation/test_execution.py tests/unit/application/test_command.py
git add src/research_os/valuation/execution.py src/research_os/application/command.py tests/unit/valuation/test_controlled_execution.py tests/unit/application/test_command.py
git commit -m "feat: execute routed valuation methods"
```

### Task 3: Add PIT market anchor and market-gap service

**Files:**
- Create: `src/research_os/valuation/market.py`
- Modify: `src/research_os/valuation/__init__.py`
- Test: `tests/unit/valuation/test_market_gap.py`
- Test: `tests/property/valuation/test_market_gap_invariants.py`

**Interfaces:**
- Consumes: `ValuationReconciliation`, included `ValuationRange` values, optional `PitMarketAnchor`.
- Produces: `ValuationMarketGapService.compare(reconciliation, ranges, anchor) -> ValuationMarketGap`.

- [x] **Step 1: Write PIT/basis RED**

```python
def test_market_anchor_requires_pit_order() -> None:
    with pytest.raises(ValueError, match="observed_ts <= available_ts"):
        anchor(observed_ts=DECISION_TS, available_ts=DECISION_TS - timedelta(days=1))


def test_incompatible_basis_is_not_compared() -> None:
    gap = ValuationMarketGapService().compare(reconciliation(), total_value_ranges(), per_share_anchor())
    assert gap.domain_status == "INSUFFICIENT_EVIDENCE"
    assert gap.comparison_status == "NOT_COMPARABLE"
    assert gap.reason_codes == ("VALUATION_BASIS_MISMATCH",)
```

- [x] **Step 2: Write state RED**

```python
@pytest.mark.parametrize(
    ("price", "expected"),
    ((Decimal("9"), "UNDERVALUED"), (Decimal("15"), "FAIR"), (Decimal("21"), "OVERVALUED")),
)
def test_market_state_compares_price_with_model_band(price: Decimal, expected: str) -> None:
    assert ValuationMarketGapService().compare(reconciliation_10_20(), ranges_10_20(), anchor(price=price)).state == expected
```

- [x] **Step 3: Implement contracts/service**

```python
class PitMarketAnchor(LineageValue):
    company_id: str
    security_id: str
    share_class: str
    source_id: str
    observed_ts: datetime
    available_ts: datetime
    price: Decimal = Field(gt=0)
    currency: str
    unit: str
    valuation_basis: Literal["per_share", "total_value"]
    corporate_action_basis: str


class ValuationMarketGap(DomainArtifact):
    reconciliation_key: str | None = None
    market_anchor_security_id: str | None = None
    market_anchor_observed_ts: datetime | None = None
    market_value: Decimal | None = None
    model_low: Decimal | None = None
    model_high: Decimal | None = None
    gap_low: Decimal | None = None
    gap_high: Decimal | None = None
    currency: str | None = None
    valuation_basis: str | None = None
    state: Literal["UNDERVALUED", "FAIR", "OVERVALUED", "UNKNOWN"] = "UNKNOWN"
    comparison_status: Literal["PASS", "NOT_COMPARABLE", "INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"
    reason_codes: tuple[str, ...] = ()
```

Implement `MarketAnchorValidator.validate(anchor, *, company_id, decision_ts)` for identity, UTC/PIT order, positive value, share class, unit, valuation basis, and corporate-action basis. Derive the comparable currency/basis from all ranges named by `included_range_keys`; reject missing, mixed, or scenario/market-anchor-only ranges. Calculate `gap_low=model_low-price`, `gap_high=model_high-price`. Preserve reconciliation/anchor identities and anchor/included-range lineage.

- [x] **Step 4: Run and commit**

```bash
pytest -q tests/unit/valuation/test_market_gap.py tests/property/valuation/test_market_gap_invariants.py
git add src/research_os/valuation/market.py src/research_os/valuation/__init__.py tests/unit/valuation/test_market_gap.py tests/property/valuation/test_market_gap_invariants.py
git commit -m "feat: compare PIT market anchors with valuation"
```

### Task 4: Wire execution, anchor, and gap into the professional module

**Files:**
- Modify: `src/research_os/runtime/core_artifacts.py`
- Modify: `src/research_os/application/professional_modules/valuation_sensitivity.py`
- Modify: `src/research_os/application/plan.py`
- Modify: `src/research_os/sufficiency/service.py`
- Test: `tests/integration/runtime/test_valuation_market_gap.py`
- Test: `tests/regression/professional/test_v1_6_02_valuation_market_gap.py`

**Interfaces:**
- Consumes: routing, execution requests/external execution, ranges, anchor, funding state.
- Produces: existing valuation artifacts plus `VALUATION_MARKET_ANCHOR`, `VALUATION_MARKET_GAP`.

- [x] **Step 1: Write runtime RED**

```python
def test_valuation_module_executes_and_publishes_market_gap() -> None:
    result = run_command(command_with_pe_execution_and_anchor())
    assert result.artifacts.require(VALUATION_EXECUTION).results[0].status == "SUPPORTED"
    assert result.artifacts.require(VALUATION_MARKET_ANCHOR).price == Decimal("12")
    assert result.artifacts.require(VALUATION_MARKET_GAP).comparison_status == "PASS"
```

- [x] **Step 2: Register keys**

```python
VALUATION_MARKET_ANCHOR = ArtifactKey(
    artifact_id="valuation.market_anchor",
    schema_version="2.0",
    value_type=PitMarketAnchor,
)
VALUATION_MARKET_GAP = ArtifactKey(
    artifact_id="valuation.market_gap",
    schema_version="2.0",
    value_type=ValuationMarketGap,
)
```

- [x] **Step 3: Implement module ordering**

Execute the preferred routed request, validate it, map supported method results to the existing artifact `ValuationExecution/ValuationResult`, reconcile command/model ranges, validate the anchor against `context.company.company_id` and `context.decision_ts`, then compute the gap. External execution remains accepted only after an explicit validation path and must retain lineage.

- [x] **Step 4: Update sufficiency**

Valuation model executability is `EXECUTABLE` only when controlled execution passes; market comparison coverage is complete only when gap comparison passes. A supported range without execution or anchor is partial, not complete.

- [x] **Step 5: Run and commit**

```bash
pytest -q tests/unit/valuation tests/property/valuation tests/integration/runtime/test_valuation_market_gap.py tests/regression/professional/test_v1_6_02_valuation_market_gap.py tests/unit/sufficiency
git add src/research_os/runtime/core_artifacts.py src/research_os/application/professional_modules/valuation_sensitivity.py src/research_os/application/plan.py src/research_os/sufficiency/service.py tests/integration/runtime/test_valuation_market_gap.py tests/regression/professional/test_v1_6_02_valuation_market_gap.py
git commit -m "feat: publish valuation execution and market gap"
```

### Task 5: Project valuation semantics and add the M3 gate

**Files:**
- Modify: `src/research_os/reporting/projectors/_market.py`
- Modify: `src/research_os/reporting/projectors/_registry.py`
- Modify: `src/research_os/reporting/projectors/_shared.py`
- Create: `tests/unit/reporting/test_v1_6_02_valuation.py`
- Modify: `tests/fixtures/field_acceptance/v1_6_02/300034.SZ.json`
- Create: `tests/fixtures/field_acceptance/v1_6_02/001287.SZ.json`
- Create: `tests/fixtures/field_acceptance/v1_6_02/301073.SZ.json`
- Modify: `src/research_os/release/verification.py`
- Modify: `tests/regression/architecture/test_release_governance.py`

**Interfaces:**
- Consumes: canonical valuation execution/anchor/gap.
- Produces: presentation-safe valuation output and pack `v1-6-02-valuation-market-gap`.

- [x] **Step 1: Add verified PIT anchor evidence**

For each company, record the last market observation available at or before `2026-08-30T00:00:00Z`, including actual observation timestamp, availability timestamp, source identity, share class, currency, basis, corporate-action basis, and evidence fingerprint. Do not use 2026-08-30 as a fabricated trading timestamp.

- [x] **Step 2: Write projector/field RED**

```python
def test_market_gap_projector_displays_observation_time_and_basis() -> None:
    payload = project_artifact("valuation.market_gap", supported_gap()).payload
    assert payload["市场比较状态"] == "通过"
    assert payload["市场估值状态"] == "低估"


def test_at_least_one_real_company_has_supported_market_gap() -> None:
    gaps = [run_v1_6_02_case(item).artifacts.require(VALUATION_MARKET_GAP) for item in REAL_COMPANY_IDS]
    assert any(item.comparison_status == "PASS" for item in gaps)
```

- [x] **Step 3: Implement projectors and gate registry**

```python
_V1_6_02_VALUATION_CHECKS = {
    "v1_6_02_valuation_unit": "tests/unit/valuation",
    "v1_6_02_valuation_property": "tests/property/valuation",
    "v1_6_02_valuation_runtime": "tests/integration/runtime/test_valuation_market_gap.py",
    "v1_6_02_valuation_field": "tests/regression/professional/test_v1_6_02_valuation_market_gap.py",
    "v1_6_02_valuation_reporting": "tests/unit/reporting/test_v1_6_02_valuation.py",
}
```

Register but do not select the pack before M6.

- [x] **Step 4: Run M3 exit gate and commit**

```bash
pytest -q tests/unit/valuation tests/property/valuation tests/integration/runtime/test_valuation_market_gap.py tests/regression/professional/test_v1_6_02_valuation_market_gap.py tests/unit/reporting/test_v1_6_02_valuation.py tests/unit/snapshots tests/property/snapshots tests/regression/architecture/test_release_governance.py
python -m ruff check src/research_os/valuation src/research_os/application/professional_modules/valuation_sensitivity.py tests/unit/valuation
git diff --check
git add src/research_os/reporting/projectors tests/unit/reporting/test_v1_6_02_valuation.py tests/fixtures/field_acceptance/v1_6_02 src/research_os/release/verification.py tests/regression/architecture/test_release_governance.py
git commit -m "test: gate v1.6.02 valuation market gap"
```
