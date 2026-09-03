from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from research_os.forecasting.backtest import BacktestResult
from research_os.forecasting.benchmarks import BenchmarkRegistry
from research_os.policies.builtins import builtin_policy_registry
from research_os.policies.registry import PolicyRegistry


ModelStage = Literal["experimental", "candidate", "validated", "production", "degraded", "retired"]


class PromotionDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    current_stage: ModelStage
    next_stage: ModelStage
    reason: str


def decide_promotion(
    *,
    current_stage: ModelStage,
    evaluation: BacktestResult | None,
    benchmark_registry: BenchmarkRegistry,
    hypothesis_registered: bool,
    policy_registry: PolicyRegistry | None = None,
) -> PromotionDecision:
    policies = policy_registry or builtin_policy_registry()
    minimum_folds = policies.integer_value("forecast_promotion", "minimum_out_of_sample_folds")
    minimum_improvement = float(
        policies.decimal_value("forecast_promotion", "minimum_benchmark_improvement")
    )
    require_pit = policies.boolean_value("forecast_promotion", "require_pit_compliance")
    require_stability = policies.boolean_value("forecast_promotion", "require_stability")

    if evaluation is None or not evaluation.out_of_sample:
        return _hold(current_stage, "out-of-sample evaluation is required")
    if benchmark_registry.get(evaluation.benchmark_id) is None:
        return _hold(current_stage, "a registered benchmark is required")
    if len(evaluation.stability_windows) < minimum_folds:
        return _hold(current_stage, "insufficient out-of-sample folds")
    if require_pit and not evaluation.pit_compliant:
        return _hold(current_stage, "PIT compliance failed")
    if not hypothesis_registered:
        return _hold(current_stage, "hypothesis was not preregistered")
    model_mae = evaluation.metric("MAE").value
    if evaluation.benchmark_mae <= 0:
        return _hold(current_stage, "registered benchmark MAE must be positive")
    improvement = (evaluation.benchmark_mae - model_mae) / evaluation.benchmark_mae
    if improvement <= minimum_improvement:
        return _hold(current_stage, "model did not beat registered benchmark")
    if require_stability and not evaluation.stable:
        return _hold(current_stage, "stability gate failed")

    transitions: dict[ModelStage, ModelStage] = {
        "experimental": "candidate",
        "candidate": "validated",
        "validated": "production",
        "production": "production",
        "degraded": "degraded",
        "retired": "retired",
    }
    return PromotionDecision(
        current_stage=current_stage,
        next_stage=transitions[current_stage],
        reason="all promotion gates passed",
    )


def _hold(current_stage: ModelStage, reason: str) -> PromotionDecision:
    return PromotionDecision(
        current_stage=current_stage,
        next_stage=current_stage,
        reason=reason,
    )


__all__ = ["ModelStage", "PromotionDecision", "decide_promotion"]
