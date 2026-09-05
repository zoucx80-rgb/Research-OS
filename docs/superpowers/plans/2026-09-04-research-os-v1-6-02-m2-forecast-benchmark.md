# Research OS 1.6.02 M2 Executable Forecast Benchmark Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the professional forecast placeholder with a real PIT-safe out-of-sample evaluation that compares a registered model with a simple benchmark and publishes complete, canonical evaluation evidence.

**Architecture:** Keep `TimeSeriesBacktester`, `BenchmarkRegistry`, and `decide_promotion` as the single forecasting implementations. Add one typed experiment input and one additive benchmark-evidence artifact; the professional module validates the experiment, invokes the existing engine, maps results without recomputation, and remains fail-closed when sample or benchmark evidence is insufficient.

**Tech Stack:** Python 3.12, Pydantic v2, statsmodels, scikit-learn, Decimal, pytest, existing forecasting policies.

**Spec:** `docs/superpowers/specs/2026-09-04-research-os-v1-6-02-professional-research-semantic-closure-design.md`

## Global Constraints

- Complete M1 before final M2 integration so forecast sample/temporal insufficiency can enter `research.sufficiency`.
- Keep existing `forecast.evaluation@2.0`; add `forecast.benchmark_evidence@2.0` for richer output.
- Do not implement another splitter, regression engine, metric calculator, benchmark registry, or promotion rule.
- Training features must be available by train cutoff; test features by forecast origin; labels by evaluation time.
- Random shuffle is forbidden. Realized outcome cannot be a feature.
- No benchmark/OOS/preregistered hypothesis/PIT/stability evidence means no model promotion and no strong forecast conclusion.
- Insufficient sample is a typed research outcome; leakage, malformed timestamps, or contradictory identities are execution errors.

---

## File Structure

- Create `src/research_os/forecasting/contracts.py` for experiment input and canonical benchmark evidence.
- Modify `src/research_os/forecasting/__init__.py` for public exports.
- Modify `src/research_os/application/command.py` for `ForecastResearchInput.experiment`.
- Modify `src/research_os/application/professional_modules/expectation_forecast_peer.py` for orchestration/mapping.
- Modify `src/research_os/runtime/core_artifacts.py` and `src/research_os/application/plan.py` for registration/dependencies.
- Modify `src/research_os/sufficiency/service.py` so forecast benchmark coverage affects sufficiency.
- Modify reporting `_market.py`, `_registry.py`, and `_shared.py` for display.
- Add tests under `tests/unit/forecasting`, `tests/integration/forecasting`, `tests/integration/runtime`, and `tests/regression/professional`.

---

### Task 1: Add forecast experiment and benchmark-evidence contracts

**Files:**
- Create: `src/research_os/forecasting/contracts.py`
- Modify: `src/research_os/forecasting/__init__.py`
- Modify: `src/research_os/application/command.py`
- Test: `tests/unit/forecasting/test_contracts.py`
- Test: `tests/unit/application/test_command.py`

**Interfaces:**
- Consumes: `ForecastObservation`, `ForecastHypothesis`, `ModelStage`, `EvidenceRef`.
- Produces: `ForecastExperimentInput`, `ForecastMetricEvidence`, `ForecastStabilityEvidence`, `ForecastBenchmarkEvidence`, `ForecastResearchInput.experiment`.

- [x] **Step 1: Write RED contract tests**

```python
def test_experiment_requires_unique_features_and_utc_evaluation() -> None:
    with pytest.raises(ValueError):
        ForecastExperimentInput(
            hypothesis_key="hyp:revenue",
            model_key="ols:revenue",
            target_metric="revenue_growth",
            horizon="FY+1",
            feature_names=("margin", "margin"),
            observations=forecast_observations(),
            benchmark_id="naive:last_value",
            evaluation_ts=DECISION_TS,
            n_splits=3,
            current_model_stage="experimental",
            applicability="annual comparable periods",
            model_boundary="linear explanatory forecast",
        )


def test_command_accepts_one_forecast_experiment() -> None:
    command = command_with_forecast_experiment(valid_experiment())
    assert command.forecasting.experiment.model_key == "ols:revenue"
```

- [x] **Step 2: Run RED**

```bash
pytest -q tests/unit/forecasting/test_contracts.py tests/unit/application/test_command.py
```

- [x] **Step 3: Implement contracts**

```python
class ForecastExperimentInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    hypothesis_key: str
    model_key: str
    target_metric: str
    horizon: str
    feature_names: tuple[str, ...] = Field(min_length=1)
    observations: tuple[ForecastObservation, ...] = Field(min_length=1)
    benchmark_id: str
    evaluation_ts: datetime
    n_splits: int = Field(default=3, ge=2)
    current_model_stage: ModelStage = "experimental"
    applicability: str
    model_boundary: str
    caveats: tuple[str, ...] = ()


class ForecastMetricEvidence(LineageValue):
    metric_name: Literal["MAE", "RMSE", "DIRECTION_ACCURACY", "INTERVAL_COVERAGE"]
    value: Decimal


class ForecastStabilityEvidence(LineageValue):
    window_key: str
    model_mae: Decimal
    benchmark_mae: Decimal


class ForecastBenchmarkEvidence(DomainArtifact):
    model_key: str | None = None
    target_metric: str | None = None
    horizon: str | None = None
    benchmark_key: str | None = None
    benchmark_version: str | None = None
    sample_count: int = 0
    fold_count: int = 0
    out_of_sample: bool = False
    pit_compliant: bool = False
    metrics: tuple[ForecastMetricEvidence, ...] = ()
    benchmark_mae: Decimal | None = None
    improvement: Decimal | None = None
    stability_windows: tuple[ForecastStabilityEvidence, ...] = ()
    stable: bool | None = None
    current_stage: ModelStage | None = None
    next_stage: ModelStage | None = None
    promotion_reason: str | None = None
    applicability: str | None = None
    model_boundary: str | None = None
    caveats: tuple[str, ...] = ()
    reason_codes: tuple[str, ...] = ()
```

Require UTC evaluation time, non-empty identities/boundaries, unique features, `target_metric` absent from features, and deterministic observation ordering.

- [x] **Step 4: Add the command field and run GREEN**

```python
class ForecastResearchInput(_FrozenInput):
    hypotheses: tuple[ForecastHypothesis, ...] = Field(default_factory=tuple)
    experiment: ForecastExperimentInput | None = None
```

```bash
pytest -q tests/unit/forecasting/test_contracts.py tests/unit/application/test_command.py
git add src/research_os/forecasting src/research_os/application/command.py tests/unit/forecasting/test_contracts.py tests/unit/application/test_command.py
git commit -m "feat: add forecast benchmark contracts"
```

### Task 2: Validate experiment readiness without hiding invalid data

**Files:**
- Create: `src/research_os/forecasting/experiment.py`
- Test: `tests/unit/forecasting/test_experiment.py`

**Interfaces:**
- Consumes: `ForecastExperimentInput`, `BenchmarkRegistry`, registered hypothesis keys.
- Produces: `ForecastExperimentAssessment(status, reason_codes)`.

- [x] **Step 1: Write RED**

```python
def test_insufficient_sample_is_typed_not_exception() -> None:
    assessment = ForecastExperimentValidator(registry()).assess(
        experiment_with_observations(4), registered_hypotheses={"hyp:revenue"}
    )
    assert assessment.status == "INSUFFICIENT_EVIDENCE"
    assert assessment.reason_codes == ("INSUFFICIENT_OBSERVATIONS",)


def test_unregistered_benchmark_is_typed_insufficient() -> None:
    assessment = ForecastExperimentValidator(registry()).assess(
        experiment_with_benchmark("unknown"), registered_hypotheses={"hyp:revenue"}
    )
    assert "UNREGISTERED_BENCHMARK" in assessment.reason_codes
```

- [x] **Step 2: Implement validator**

```python
class ForecastExperimentAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: Literal["READY", "INSUFFICIENT_EVIDENCE"]
    reason_codes: tuple[str, ...] = ()
```

Require at least `n_splits + 2` observations, registered benchmark, matching preregistered hypothesis, chronological order, and all evaluation timestamps at or before run decision time. Do not catch backtester leakage/identity exceptions as insufficiency.

- [x] **Step 3: Run and commit**

```bash
pytest -q tests/unit/forecasting/test_experiment.py tests/unit/forecasting/test_benchmarks.py tests/unit/forecasting/test_promotion.py
git add src/research_os/forecasting/experiment.py tests/unit/forecasting/test_experiment.py
git commit -m "feat: validate forecast experiment readiness"
```

### Task 3: Execute and publish forecast benchmark evidence

**Files:**
- Modify: `src/research_os/runtime/core_artifacts.py`
- Modify: `src/research_os/application/professional_modules/expectation_forecast_peer.py`
- Modify: `src/research_os/application/plan.py`
- Test: `tests/integration/runtime/test_professional_forecast_benchmark.py`
- Test: `tests/regression/professional/test_v1_6_02_forecast_benchmark.py`

**Interfaces:**
- Consumes: `ForecastResearchInput`, built-in benchmark registry, `TimeSeriesBacktester`, `decide_promotion`.
- Produces: existing `FORECAST_EVALUATION` plus `FORECAST_BENCHMARK_EVIDENCE`.

- [x] **Step 1: Write RED execution test**

```python
def test_professional_module_executes_registered_oos_benchmark() -> None:
    result = run_command(command_with_valid_forecast_experiment())
    evidence = result.artifacts.require(FORECAST_BENCHMARK_EVIDENCE)
    assert evidence.domain_status == "SUPPORTED"
    assert evidence.out_of_sample and evidence.pit_compliant
    assert {item.metric_name for item in evidence.metrics} == {
        "MAE", "RMSE", "DIRECTION_ACCURACY", "INTERVAL_COVERAGE"
    }
    assert evidence.benchmark_key == "naive:last_value"
```

- [x] **Step 2: Register the artifact**

```python
FORECAST_BENCHMARK_EVIDENCE = ArtifactKey(
    artifact_id="forecast.benchmark_evidence",
    schema_version="2.0",
    value_type=ForecastBenchmarkEvidence,
)
```

- [x] **Step 3: Replace the placeholder module path**

When no experiment is present, write both forecast artifacts as `INSUFFICIENT_EVIDENCE` with `EXPERIMENT_NOT_PROVIDED`. When validation is insufficient, write exact reason codes without calling the backtester. When ready:

1. call `TimeSeriesBacktester.run`;
2. call `decide_promotion` using hypothesis registration and the same registry;
3. map metrics/windows/lineage into `ForecastBenchmarkEvidence`;
4. map each backtest fold into existing `ForecastFoldEvaluation` using maximum feature availability, maximum label maturity, fold evaluation time, fold model MAE, and fold benchmark MAE;
5. never recompute the aggregate metrics in the application module.

- [x] **Step 4: Run GREEN and commit**

```bash
pytest -q tests/unit/forecasting tests/integration/forecasting tests/integration/runtime/test_professional_forecast_benchmark.py tests/regression/professional/test_v1_6_02_forecast_benchmark.py
git add src/research_os/runtime/core_artifacts.py src/research_os/application/professional_modules/expectation_forecast_peer.py src/research_os/application/plan.py tests/integration/runtime/test_professional_forecast_benchmark.py tests/regression/professional/test_v1_6_02_forecast_benchmark.py
git commit -m "feat: execute professional forecast benchmarks"
```

### Task 4: Integrate forecast sufficiency and reporting

**Files:**
- Modify: `src/research_os/sufficiency/service.py`
- Modify: `src/research_os/reporting/projectors/_market.py`
- Modify: `src/research_os/reporting/projectors/_registry.py`
- Modify: `src/research_os/reporting/projectors/_shared.py`
- Test: `tests/unit/sufficiency/test_service.py`
- Test: `tests/unit/reporting/test_v1_6_02_forecast.py`

**Interfaces:**
- Consumes: `ForecastBenchmarkEvidence`.
- Produces: forecast benchmark coverage/executability and investor-readable canonical metrics.

- [x] **Step 1: Write RED**

```python
def test_forecast_sufficiency_requires_oos_benchmark() -> None:
    domain = evaluate(state_with_forecast(out_of_sample=False)).require_domain("forecast")
    assert domain.benchmark_coverage == "MISSING"
    assert domain.model_executability == "BLOCKED"


def test_forecast_projector_exposes_metrics_and_promotion_reason() -> None:
    payload = project_artifact("forecast.benchmark_evidence", benchmark_evidence()).payload
    assert payload["样本外验证"] is True
    assert payload["基准模型"] == "最近一期值"
    assert payload["晋级结论"]
```

- [x] **Step 2: Implement projection and sufficiency mapping**

Use `_number` and `_model`; map known benchmark IDs through the existing human-label mapping. Show sample/fold count, all four metrics, benchmark MAE, improvement, stability, stage transition, applicability, boundary, caveats, and reasons.

- [x] **Step 3: Run and commit**

```bash
pytest -q tests/unit/sufficiency/test_service.py tests/unit/reporting/test_v1_6_02_forecast.py tests/integration/reporting/test_semantic_fingerprint_v1_6.py
git add src/research_os/sufficiency/service.py src/research_os/reporting/projectors tests/unit/sufficiency/test_service.py tests/unit/reporting/test_v1_6_02_forecast.py
git commit -m "feat: report forecast benchmark evidence"
```

### Task 5: Add real-company acceptance and M2 gate

**Files:**
- Create: `tests/fixtures/field_acceptance/v1_6_02/300034.SZ.json`
- Modify: `tests/regression/professional/test_v1_6_02_forecast_benchmark.py`
- Modify: `src/research_os/release/verification.py`
- Modify: `tests/regression/architecture/test_release_governance.py`

**Interfaces:**
- Consumes: PIT historical observations from original/versioned company evidence.
- Produces: at least one real-company OOS benchmark result and pack `v1-6-02-forecast-benchmark`.

- [x] **Step 1: Build the evidence-backed fixture supplement**

Add only observations whose source identity, publication/availability timestamps, reporting periods, values, and fingerprints can be verified. The fixture must contain enough chronologically ordered mature observations for the configured split. If 300034 cannot meet the policy from approved evidence, use 001287; do not lower the gate or synthesize realized outcomes.

- [x] **Step 2: Write acceptance RED**

```python
def test_at_least_one_real_company_executes_oos_benchmark() -> None:
    results = [run_v1_6_02_case(company_id) for company_id in REAL_COMPANY_IDS]
    evidence = [item.artifacts.require(FORECAST_BENCHMARK_EVIDENCE) for item in results]
    assert any(item.domain_status == "SUPPORTED" and item.out_of_sample for item in evidence)
    assert all(item.reason_codes or item.metrics for item in evidence)
```

- [x] **Step 3: Register the M2 pack**

```python
_V1_6_02_FORECAST_CHECKS = {
    "v1_6_02_forecast_unit": "tests/unit/forecasting",
    "v1_6_02_forecast_integration": "tests/integration/forecasting",
    "v1_6_02_forecast_runtime": "tests/integration/runtime/test_professional_forecast_benchmark.py",
    "v1_6_02_forecast_field": "tests/regression/professional/test_v1_6_02_forecast_benchmark.py",
}
```

Register, but do not select, the pack until M6.

- [x] **Step 4: Run M2 exit gate and commit**

```bash
pytest -q tests/unit/forecasting tests/integration/forecasting tests/integration/runtime/test_professional_forecast_benchmark.py tests/regression/professional/test_v1_6_02_forecast_benchmark.py tests/unit/sufficiency/test_service.py tests/unit/reporting/test_v1_6_02_forecast.py tests/regression/architecture/test_release_governance.py
python -m ruff check src/research_os/forecasting src/research_os/application/professional_modules/expectation_forecast_peer.py tests/unit/forecasting
git diff --check
git add tests/fixtures/field_acceptance/v1_6_02 src/research_os/release/verification.py tests/regression
git commit -m "test: gate v1.6.02 forecast benchmarking"
```
