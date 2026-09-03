from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from research_os.contracts.evidence import EvidenceRef
from research_os.forecasting.backtest import (
    BacktestMetric,
    BacktestResult,
    StabilityWindow,
)
from research_os.forecasting.benchmarks import builtin_benchmark_registry
from research_os.forecasting.promotion import decide_promotion
from research_os.policies import (
    PolicyOverride,
    PolicyRegistry,
    builtin_policy_definitions,
    builtin_policy_registry,
)


def _evaluation(*, model_mae: float, benchmark_mae: float) -> BacktestResult:
    reference = EvidenceRef(
        evidence_id="forecast:test",
        revision=1,
        content_fingerprint="a" * 64,
    )
    timestamp = datetime(2026, 1, 31, tzinfo=timezone.utc)
    metrics = (
        BacktestMetric(name="MAE", value=model_mae, evidence_refs=(reference,)),
        BacktestMetric(name="RMSE", value=model_mae, evidence_refs=(reference,)),
        BacktestMetric(name="DIRECTION_ACCURACY", value=1.0, evidence_refs=(reference,)),
        BacktestMetric(name="INTERVAL_COVERAGE", value=0.9, evidence_refs=(reference,)),
    )
    return BacktestResult(
        model_kind="STATSMODELS_OLS",
        feature_names=("orders",),
        target="revenue",
        benchmark_id="naive:last_value",
        benchmark_version="1.0.0",
        train_cutoff=timestamp,
        evaluation_ts=timestamp,
        out_of_sample=True,
        pit_compliant=True,
        folds=(),
        metrics=metrics,
        benchmark_mae=benchmark_mae,
        stability_windows=(
            StabilityWindow(
                window_id="window:1",
                model_mae=model_mae,
                benchmark_mae=benchmark_mae,
                evidence_refs=(reference,),
            ),
        ),
    )


def test_model_cannot_promote_if_not_better_than_naive() -> None:
    decision = decide_promotion(
        current_stage="candidate",
        evaluation=_evaluation(model_mae=12, benchmark_mae=10),
        benchmark_registry=builtin_benchmark_registry(),
        hypothesis_registered=True,
    )
    assert decision.next_stage == "candidate"
    assert "benchmark" in decision.reason


def test_validated_model_can_promote_to_production_only_with_all_gates() -> None:
    decision = decide_promotion(
        current_stage="validated",
        evaluation=_evaluation(model_mae=8, benchmark_mae=10),
        benchmark_registry=builtin_benchmark_registry(),
        hypothesis_registered=True,
    )
    assert decision.next_stage == "production"


def test_benchmark_improvement_policy_is_a_relative_ratio() -> None:
    base = builtin_policy_registry().require("forecast_promotion")
    policies = PolicyRegistry(
        builtin_policy_definitions(),
        overrides=(
            PolicyOverride(
                policy_id="forecast_promotion",
                base_policy_version=base.policy_version,
                operator="model-risk",
                reason="Require at least fifteen percent MAE improvement.",
                override_ts=datetime(2026, 2, 1, tzinfo=timezone.utc),
                parameters={
                    "minimum_benchmark_improvement": base.parameters[
                        "minimum_benchmark_improvement"
                    ].model_copy(update={"value": Decimal("0.15")})
                },
            ),
        ),
    )

    decision = decide_promotion(
        current_stage="candidate",
        evaluation=_evaluation(model_mae=8.6, benchmark_mae=10),
        benchmark_registry=builtin_benchmark_registry(),
        hypothesis_registered=True,
        policy_registry=policies,
    )

    assert decision.next_stage == "candidate"
    assert "benchmark" in decision.reason
