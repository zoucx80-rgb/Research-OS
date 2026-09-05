# Research OS 1.6.02 M1 Temporal Research and Sufficiency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PIT-safe comparable multi-period financial analysis and domain-level research sufficiency so a non-empty one-point series can no longer masquerade as adequate temporal evidence.

**Architecture:** Add temporal and sufficiency contracts beside the frozen v1.6.01 artifact payloads. A pure temporal service validates explicit reporting/comparison bases and derives only supported changes; Engine-executed modules publish `financial.temporal_analysis` and `research.sufficiency`. Existing Readiness remains execution-oriented but requires substantive temporal analysis for its time-series dimension.

**Tech Stack:** Python 3.12, Pydantic v2, Decimal, existing ReportingPeriod/AccountingScope/PolicyRegistry, pytest, Hypothesis.

**Spec:** `docs/superpowers/specs/2026-09-04-research-os-v1-6-02-professional-research-semantic-closure-design.md`

## Global Constraints

- Implementation starts from the latest fetched `main`; planning parent is `c40bf7d08591376f82dc2abf94997db6034a4da6`.
- Target Research OS `1.6.02`; keep Core API `2.0`, Plugin API `2.0`, Snapshot Schema `2.0`, HTTP API `v1`.
- Add new artifact IDs; do not change required fields in `financial.time_series@2.0` or `research.readiness@2.0`.
- Every valid observation and derived assessment carries revision-bound lineage.
- Reject future availability and incompatible currency, unit, scope, period, or comparison basis.
- Never split cumulative H1/Q1_Q3 into quarters, interpolate missing values, or turn annualized values into reported values.
- Trend is descriptive (`RISING/FALLING/STABLE/MIXED/UNKNOWN`), not automatically an economic conclusion.
- Presentation projects canonical temporal/sufficiency artifacts and performs no change calculation.

---

## File Structure

- Create `src/research_os/temporal/{__init__,models,service}.py` for temporal contracts and derivation.
- Create `src/research_os/sufficiency/{__init__,models,service}.py` for domain sufficiency.
- Create `src/research_os/application/professional_modules/sufficiency.py` for the Engine module.
- Modify `src/research_os/application/command.py`, `professional_modules/financial_capital.py`, `professional_modules/__init__.py`, and `application/plan.py` for inputs and ordering.
- Modify `src/research_os/runtime/core_artifacts.py` and `src/research_os/readiness/service.py` for registrations and readiness semantics.
- Modify reporting projector files `_core.py`, `_monitoring.py`, `_registry.py`, and `_shared.py` for projection only.
- Add unit/property/integration/regression tests under `tests/unit/temporal`, `tests/property/temporal`, `tests/unit/sufficiency`, `tests/integration/runtime`, and `tests/regression/professional`.

---

### Task 1: Freeze additive temporal contracts

**Files:**
- Create: `src/research_os/temporal/__init__.py`
- Create: `src/research_os/temporal/models.py`
- Modify: `src/research_os/application/command.py`
- Test: `tests/unit/temporal/test_models.py`
- Test: `tests/unit/application/test_command.py`

**Interfaces:**
- Consumes: `ReportingPeriod`, `AccountingScope`, `LineageValue`, `DomainArtifact`.
- Produces: `FinancialPeriodObservation`, `MetricTemporalAssessment`, `FinancialTemporalAnalysis`, `FinancialResearchInput.period_observations`.

- [x] **Step 1: Write contract RED tests**

```python
def test_period_observation_requires_utc_availability_and_lineage() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        FinancialPeriodObservation(
            metric_id="revenue",
            reporting_period=ReportingPeriod(period_type="FY"),
            period_kind="FLOW",
            value=Decimal("100"),
            unit="CNY",
            accounting_scope=AccountingScope(consolidation="consolidated"),
            value_kind="reported",
            comparison_basis="YOY_PERIOD",
            available_ts=datetime(2025, 3, 31),
            evidence_refs=(evidence_ref(),),
        )


def test_financial_command_accepts_period_observations() -> None:
    command = command_with(period_observations=(reported_revenue_fy_2024(),))
    assert command.financial.period_observations[0].metric_id == "revenue"
```

- [x] **Step 2: Run RED**

```bash
pytest -q tests/unit/temporal/test_models.py tests/unit/application/test_command.py
```

Expected: FAIL because the temporal types and command field do not exist.

- [x] **Step 3: Implement the contract types**

```python
TemporalComparisonBasis = Literal["YOY_PERIOD", "QOQ_PERIOD", "TTM", "SAME_PERIOD"]
PeriodKind = Literal["FLOW", "STOCK", "FLOW_RATIO", "STOCK_RATIO"]
TrendState = Literal["RISING", "FALLING", "STABLE", "MIXED", "UNKNOWN"]
TurningPointState = Literal["CONFIRMED", "POSSIBLE", "NOT_OBSERVED", "UNKNOWN"]


class FinancialPeriodObservation(LineageValue):
    metric_id: str
    reporting_period: ReportingPeriod
    period_kind: PeriodKind
    value: Decimal
    unit: str
    accounting_scope: AccountingScope
    value_kind: Literal["reported", "derived"]
    annualized: bool = False
    comparison_basis: TemporalComparisonBasis | None = None
    available_ts: datetime


class MetricTemporalAssessment(LineageValue):
    metric_id: str
    unit: str
    point_count: int = Field(ge=0)
    comparable_point_count: int = Field(ge=0)
    temporal_span_days: int | None = Field(default=None, ge=0)
    yoy_change: Decimal | None = None
    qoq_change: Decimal | None = None
    ttm_value: Decimal | None = None
    trend_state: TrendState = "UNKNOWN"
    turning_point_state: TurningPointState = "UNKNOWN"
    anomaly_flags: tuple[str, ...] = ()
    comparison_status: Literal["PASS", "NOT_COMPARABLE", "INSUFFICIENT_EVIDENCE"]
    reason_codes: tuple[str, ...] = ()


class FinancialTemporalAnalysis(DomainArtifact):
    assessments: tuple[MetricTemporalAssessment, ...] = ()
    temporal_coverage: Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"
    unresolved_gaps: tuple[str, ...] = ()
```

Normalize timestamps to UTC, require evidence for reported values, reject duplicate identities, and canonicalize order by metric/scope/unit/period end.

- [x] **Step 4: Add the command field**

```python
class FinancialResearchInput(_FrozenInput):
    unit: str = "CNY"
    observations: tuple[FinancialObservation, ...] = Field(default_factory=tuple)
    operating_observations: tuple[OperatingObservation, ...] = Field(default_factory=tuple)
    time_series: tuple[FinancialTimeSeries, ...] = Field(default_factory=tuple)
    period_observations: tuple[FinancialPeriodObservation, ...] = Field(default_factory=tuple)
    cash_flow_quality: CashFlowQualityInput | None = None
```

- [x] **Step 5: Run GREEN and commit**

```bash
pytest -q tests/unit/temporal/test_models.py tests/unit/application/test_command.py
git add src/research_os/temporal src/research_os/application/command.py tests/unit/temporal tests/unit/application/test_command.py
git commit -m "feat: add temporal research contracts"
```

### Task 2: Implement deterministic temporal analysis

**Files:**
- Create: `src/research_os/temporal/service.py`
- Modify: `src/research_os/policies/builtins.py`
- Test: `tests/unit/temporal/test_service.py`
- Test: `tests/property/temporal/test_temporal_invariants.py`

**Interfaces:**
- Consumes: period observations, UTC `decision_ts`, versioned temporal policies.
- Produces: `ComparisonBasisValidator.validate(...)` and `TemporalAnalysisService.analyze(observations, *, decision_ts) -> FinancialTemporalAnalysis`.

- [x] **Step 1: Write comparison/PIT RED tests**

```python
def test_one_point_is_not_sufficient() -> None:
    result = TemporalAnalysisService().analyze((reported_revenue_fy_2024(),), decision_ts=DECISION_TS)
    assert result.temporal_coverage == "INSUFFICIENT_EVIDENCE"
    assert result.assessments[0].yoy_change is None


def test_cumulative_h1_is_not_converted_to_quarter() -> None:
    result = TemporalAnalysisService().analyze((revenue_h1_2024(), revenue_h1_2025()), decision_ts=DECISION_TS)
    assert result.assessments[0].yoy_change == Decimal("0.10")
    assert result.assessments[0].qoq_change is None


def test_future_available_observation_is_rejected() -> None:
    with pytest.raises(ValueError, match="available_ts exceeds decision_ts"):
        TemporalAnalysisService().analyze((future_observation(),), decision_ts=DECISION_TS)
```

- [x] **Step 2: Write order-invariance RED property**

```python
@given(st.permutations(comparable_observations()))
def test_order_does_not_change_analysis(items) -> None:
    service = TemporalAnalysisService()
    assert service.analyze(tuple(items), decision_ts=DECISION_TS) == service.analyze(comparable_observations(), decision_ts=DECISION_TS)
```

- [x] **Step 3: Run RED**

```bash
pytest -q tests/unit/temporal/test_service.py tests/property/temporal/test_temporal_invariants.py
```

- [x] **Step 4: Implement supported derivations**

Implement `ComparisonBasisValidator` as the single check for period type/kind, cumulative status, dates, scope, unit, annualization, and declared comparison basis. Group by `(metric_id, unit, accounting_scope)`, reject future/duplicate conflicts, and sort chronologically. Calculate YOY only for equal period types/kinds with explicit `YOY_PERIOD`; QOQ only for contiguous non-cumulative `CUSTOM` quarters with `QOQ_PERIOD`; TTM only from four contiguous non-cumulative flow quarters explicitly marked `TTM`. Collect evidence and assumption lineage from every used observation. `turning_point_state` may be `CONFIRMED` only when the configured number of comparable changes reverses direction; one change is at most `POSSIBLE`.

Register typed policy parameters under `temporal_analysis`: `minimum_comparable_points=2`, `stable_relative_change=0.01`, `anomaly_relative_change=0.30`. These thresholds are versioned research policy, not probabilities.

- [x] **Step 5: Run GREEN and commit**

```bash
pytest -q tests/unit/temporal/test_service.py tests/property/temporal/test_temporal_invariants.py tests/unit/policies
git add src/research_os/temporal/service.py src/research_os/policies/builtins.py tests/unit/temporal tests/property/temporal
git commit -m "feat: derive comparable financial trends"
```

### Task 3: Publish temporal analysis through the Engine

**Files:**
- Modify: `src/research_os/runtime/core_artifacts.py`
- Modify: `src/research_os/application/professional_modules/financial_capital.py`
- Test: `tests/unit/contracts/test_core_artifacts.py`
- Test: `tests/integration/runtime/test_temporal_sufficiency.py`

**Interfaces:**
- Consumes: `FinancialResearchInput.period_observations`, `ResearchContext.decision_ts`.
- Produces: `FINANCIAL_TEMPORAL_ANALYSIS: ArtifactKey[FinancialTemporalAnalysis]`.

- [x] **Step 1: Write module RED**

```python
def test_financial_module_publishes_temporal_analysis() -> None:
    result = run_command(command_with_two_comparable_fy_periods())
    temporal = result.artifacts.require(FINANCIAL_TEMPORAL_ANALYSIS)
    assert temporal.temporal_coverage == "SUFFICIENT"
    assert temporal.assessments[0].yoy_change == Decimal("0.10")
    assert temporal.evidence_refs
```

- [x] **Step 2: Register the key and implement the write**

```python
FINANCIAL_TEMPORAL_ANALYSIS = ArtifactKey(
    artifact_id="financial.temporal_analysis",
    schema_version="2.0",
    value_type=FinancialTemporalAnalysis,
)
```

Add it to `CORE_ARTIFACT_KEYS` and `FinancialResearchModule.spec.provides`; call `TemporalAnalysisService.analyze` and write with producer `core:professional-financial`. Do not derive from the legacy presentation-oriented string period.

- [x] **Step 3: Run GREEN and commit**

```bash
pytest -q tests/unit/contracts/test_core_artifacts.py tests/integration/runtime/test_temporal_sufficiency.py tests/unit/snapshots tests/property/snapshots
git add src/research_os/runtime/core_artifacts.py src/research_os/application/professional_modules/financial_capital.py tests/unit/contracts/test_core_artifacts.py tests/integration/runtime/test_temporal_sufficiency.py
git commit -m "feat: publish financial temporal analysis"
```

### Task 4: Add domain research sufficiency

**Files:**
- Create: `src/research_os/sufficiency/__init__.py`
- Create: `src/research_os/sufficiency/models.py`
- Create: `src/research_os/sufficiency/service.py`
- Create: `src/research_os/application/professional_modules/sufficiency.py`
- Modify: `src/research_os/application/professional_modules/__init__.py`
- Modify: `src/research_os/runtime/core_artifacts.py`
- Modify: `src/research_os/application/plan.py`
- Test: `tests/unit/sufficiency/test_service.py`
- Test: `tests/integration/runtime/test_temporal_sufficiency.py`

**Interfaces:**
- Consumes: `ResearchStateView` and known professional artifact keys.
- Produces: `ResearchSufficiencyEvaluator.evaluate(state) -> ResearchSufficiencyAssessment`, artifact `RESEARCH_SUFFICIENCY`.

- [x] **Step 1: Write RED**

```python
def test_sufficiency_explains_upgrade_evidence() -> None:
    result = evaluator().evaluate(state_with_single_period_only())
    temporal = result.require_domain("financial_temporal")
    assert temporal.temporal_coverage == "MISSING"
    assert temporal.known_items and temporal.unknown_items
    assert temporal.why_unknown and temporal.upgrade_evidence_requirements
```

- [x] **Step 2: Implement values and evaluator**

```python
CoverageLevel = Literal["COMPLETE", "PARTIAL", "MISSING", "NOT_APPLICABLE"]


class MaterialResearchGap(LineageValue):
    gap_key: str
    domain_id: str
    reason_code: str
    description: str
    required_evidence: tuple[str, ...]


class DomainSufficiencyAssessment(LineageValue):
    domain_id: str
    coverage: CoverageLevel
    evidence_quality: CoverageLevel
    temporal_coverage: CoverageLevel
    benchmark_coverage: CoverageLevel
    peer_coverage: CoverageLevel
    model_executability: Literal["EXECUTABLE", "BLOCKED", "NOT_APPLICABLE"]
    known_items: tuple[str, ...]
    unknown_items: tuple[str, ...]
    why_unknown: tuple[str, ...]
    upgrade_evidence_requirements: tuple[str, ...]
    material_gaps: tuple[MaterialResearchGap, ...]


class ResearchSufficiencyAssessment(DomainArtifact):
    overall_status: Literal["SUFFICIENT", "LIMITED", "INSUFFICIENT_EVIDENCE"]
    domains: tuple[DomainSufficiencyAssessment, ...]
    blocking_gap_keys: tuple[str, ...]
```

Implement deterministic ordering, unique domain/gap identities, and `require_domain`. The evaluator uses artifact status plus domain-specific substance; it does not emit a pseudo-probability score.

- [x] **Step 3: Register/module-wire and commit**

```python
RESEARCH_SUFFICIENCY = ArtifactKey(
    artifact_id="research.sufficiency",
    schema_version="2.0",
    value_type=ResearchSufficiencyAssessment,
)
```

Place `ResearchSufficiencyModule` after methodology and before Decision in `ResearchPlanCompiler`.

```bash
pytest -q tests/unit/sufficiency tests/integration/runtime/test_temporal_sufficiency.py tests/unit/contracts/test_core_artifacts.py
git add src/research_os/sufficiency src/research_os/application/professional_modules src/research_os/application/plan.py src/research_os/runtime/core_artifacts.py tests/unit/sufficiency tests/integration/runtime/test_temporal_sufficiency.py
git commit -m "feat: add domain research sufficiency"
```

### Task 5: Correct Readiness and project M1 artifacts

**Files:**
- Modify: `src/research_os/readiness/service.py`
- Modify: `src/research_os/reporting/projectors/_core.py`
- Modify: `src/research_os/reporting/projectors/_monitoring.py`
- Modify: `src/research_os/reporting/projectors/_registry.py`
- Modify: `src/research_os/reporting/projectors/_shared.py`
- Test: `tests/unit/readiness/test_readiness.py`
- Test: `tests/unit/reporting/test_v1_6_02_temporal_sufficiency.py`

**Interfaces:**
- Consumes: M1 artifacts.
- Produces: correct time-series Readiness and presentation-safe payloads.

- [x] **Step 1: Write RED**

```python
def test_one_point_series_does_not_pass_time_series_readiness() -> None:
    assessment = evaluate(snapshot_with_one_point_series())
    assert dimension(assessment, "time_series").status == "INCOMPLETE"


def test_projector_displays_canonical_yoy() -> None:
    projected = project_artifact("financial.temporal_analysis", temporal_artifact())
    assert projected.payload["指标趋势"][0]["同比变化"] == "10.00%"
```

- [x] **Step 2: Implement the Readiness rule and projectors**

Use `(FINANCIAL_TIME_SERIES, FINANCIAL_TEMPORAL_ANALYSIS)` for the `time_series` requirement and require `temporal_coverage == "SUFFICIENT"`. Project canonical values only; include known/unknown/upgrade evidence in the sufficiency projection.

- [x] **Step 3: Run GREEN and commit**

```bash
pytest -q tests/unit/readiness/test_readiness.py tests/unit/reporting/test_v1_6_02_temporal_sufficiency.py tests/integration/runtime/test_completion_readiness_separation.py
git add src/research_os/readiness/service.py src/research_os/reporting/projectors tests/unit/readiness/test_readiness.py tests/unit/reporting/test_v1_6_02_temporal_sufficiency.py
git commit -m "fix: require substantive temporal readiness"
```

### Task 6: Add M1 field regression and verification pack

**Files:**
- Create: `tests/regression/professional/test_v1_6_02_temporal_sufficiency.py`
- Modify: `src/research_os/release/verification.py`
- Modify: `tests/regression/architecture/test_release_governance.py`

**Interfaces:**
- Consumes: the three v1.6.01 field commands and M1 artifacts.
- Produces: verification pack `v1-6-02-temporal-sufficiency`.

- [x] **Step 1: Write three-company regression**

```python
@pytest.mark.parametrize("company_id", ("300034.SZ", "001287.SZ", "301073.SZ"))
def test_single_period_case_is_not_temporally_sufficient(company_id: str) -> None:
    result = run_v1_6_01_case(company_id)
    assert result.artifacts.require(FINANCIAL_TEMPORAL_ANALYSIS).temporal_coverage != "SUFFICIENT"
    assert result.artifacts.require(RESEARCH_SUFFICIENCY).blocking_gap_keys
```

Add case-specific assertions: 300034 evaluates revenue/gross margin/OCF; 001287 evaluates revenue/AR/inventory/NWC/OCF/debt with auditable bases; 301073 evaluates revenue/cash flow/lease evidence independently. Every absent series names its exact required periods/evidence instead of being dropped.

- [x] **Step 2: Register the pack without selecting it in the current release**

```python
_V1_6_02_TEMPORAL_CHECKS = {
    "v1_6_02_temporal_unit": "tests/unit/temporal",
    "v1_6_02_temporal_property": "tests/property/temporal",
    "v1_6_02_sufficiency_unit": "tests/unit/sufficiency",
    "v1_6_02_temporal_runtime": "tests/integration/runtime/test_temporal_sufficiency.py",
    "v1_6_02_temporal_field": "tests/regression/professional/test_v1_6_02_temporal_sufficiency.py",
}
```

- [x] **Step 3: Run M1 exit gate**

```bash
pytest -q tests/unit/temporal tests/property/temporal tests/unit/sufficiency tests/unit/readiness/test_readiness.py tests/integration/runtime/test_temporal_sufficiency.py tests/regression/professional/test_v1_6_02_temporal_sufficiency.py tests/unit/snapshots tests/property/snapshots tests/regression/architecture/test_release_governance.py
python -m ruff check src/research_os/temporal src/research_os/sufficiency tests/unit/temporal tests/unit/sufficiency
git diff --check
```

- [x] **Step 4: Commit**

```bash
git add src/research_os/release/verification.py tests/regression
git commit -m "test: gate v1.6.02 temporal sufficiency"
```
