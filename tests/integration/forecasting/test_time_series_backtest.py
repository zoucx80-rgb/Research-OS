from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from research_os.contracts.evidence import EvidenceRef
from research_os.forecasting.backtest import (
    BacktestFold,
    ForecastObservation,
    TimeSeriesBacktester,
)
from research_os.forecasting.benchmarks import builtin_benchmark_registry
from research_os.forecasting.model_card import ForecastModelCard
from research_os.forecasting.promotion import decide_promotion


UTC = timezone.utc


def _ref(index: int) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=f"forecast:{index}",
        revision=1,
        content_fingerprint=f"{index:064x}",
    )


def _observation(index: int, *, feature_delay_days: int = 0) -> ForecastObservation:
    observed_ts = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=index)
    return ForecastObservation(
        observation_id=f"obs:{index}",
        observed_ts=observed_ts,
        feature_available_ts={
            "orders": observed_ts + timedelta(days=feature_delay_days),
        },
        label_mature_ts=observed_ts,
        features={"orders": float(index)},
        realized_outcome=float(index * 2 + (index % 2)),
        evidence_refs=(_ref(index),),
    )


def test_fold_rejects_post_cutoff_training_observation() -> None:
    cutoff = datetime(2026, 1, 3, tzinfo=UTC)
    with pytest.raises(ValidationError, match="post-cutoff observation"):
        BacktestFold(
            fold_id="fold:bad",
            train_cutoff=cutoff,
            evaluation_ts=datetime(2026, 2, 1, tzinfo=UTC),
            train_observations=(_observation(1), _observation(3)),
            test_observations=(_observation(4),),
        )


def test_fold_rejects_unavailable_feature_and_immature_label() -> None:
    cutoff = datetime(2026, 1, 4, tzinfo=UTC)
    with pytest.raises(ValidationError, match="feature availability"):
        BacktestFold(
            fold_id="fold:feature-leak",
            train_cutoff=cutoff,
            evaluation_ts=datetime(2026, 2, 1, tzinfo=UTC),
            train_observations=(_observation(2, feature_delay_days=5),),
            test_observations=(_observation(5),),
        )

    immature = _observation(5).model_copy(
        update={"label_mature_ts": datetime(2026, 3, 1, tzinfo=UTC)}
    )
    with pytest.raises(ValidationError, match="label maturity"):
        BacktestFold(
            fold_id="fold:label-leak",
            train_cutoff=cutoff,
            evaluation_ts=datetime(2026, 2, 1, tzinfo=UTC),
            train_observations=(_observation(2),),
            test_observations=(immature,),
        )


def test_realized_outcome_cannot_be_declared_as_a_contemporaneous_feature() -> None:
    observation = _observation(2).model_copy(
        update={
            "features": {"orders": 2.0, "realized_outcome": 5.0},
            "feature_available_ts": {
                "orders": datetime(2026, 1, 3, tzinfo=UTC),
                "realized_outcome": datetime(2026, 1, 3, tzinfo=UTC),
            },
        }
    )
    with pytest.raises(ValidationError, match="realized outcome"):
        BacktestFold(
            fold_id="fold:target-leak",
            train_cutoff=datetime(2026, 1, 3, tzinfo=UTC),
            evaluation_ts=datetime(2026, 2, 1, tzinfo=UTC),
            train_observations=(observation,),
            test_observations=(_observation(4),),
        )


def test_time_series_backtest_is_ordered_and_carries_metric_lineage() -> None:
    observations = tuple(_observation(index) for index in range(1, 13))
    result = TimeSeriesBacktester(builtin_benchmark_registry()).run(
        observations=observations,
        feature_names=("orders",),
        target="revenue",
        benchmark_id="naive:last_value",
        evaluation_ts=datetime(2026, 2, 1, tzinfo=UTC),
        n_splits=3,
    )

    assert result.out_of_sample is True
    assert len(result.folds) == 3
    assert all(
        max(item.observed_ts for item in fold.train_observations)
        < min(item.observed_ts for item in fold.test_observations)
        for fold in result.folds
    )
    assert {metric.name for metric in result.metrics} == {
        "MAE",
        "RMSE",
        "DIRECTION_ACCURACY",
        "INTERVAL_COVERAGE",
    }
    assert all(metric.evidence_refs for metric in result.metrics)
    assert result.stability_windows
    assert all(window.evidence_refs for window in result.stability_windows)

    card = ForecastModelCard.from_backtest(
        model_id="ols:revenue",
        model_version="1.0.0",
        result=result,
        environment={"python": "3.12", "statsmodels": "0.14"},
        limitations=("Synthetic sample; no regime-change coverage.",),
    )
    assert card.features == ("orders",)
    assert card.target == "revenue"
    assert card.train_cutoff == result.train_cutoff
    assert len(card.fold_availability) == 3
    assert card.label_maturity
    assert card.evaluation_ts == result.evaluation_ts
    assert card.environment["statsmodels"] == "0.14"
    assert card.limitations
    assert card.model_dump(mode="json")["environment"]["python"] == "3.12"


def test_promotion_requires_registered_benchmark_and_oos_result() -> None:
    registry = builtin_benchmark_registry()
    no_result = decide_promotion(
        current_stage="candidate",
        evaluation=None,
        benchmark_registry=registry,
        hypothesis_registered=True,
    )
    assert no_result.next_stage == "candidate"
    assert "out-of-sample" in no_result.reason

    observations = tuple(_observation(index) for index in range(1, 13))
    evaluation = TimeSeriesBacktester(registry).run(
        observations=observations,
        feature_names=("orders",),
        target="revenue",
        benchmark_id="naive:last_value",
        evaluation_ts=datetime(2026, 2, 1, tzinfo=UTC),
        n_splits=3,
    )
    unregistered = decide_promotion(
        current_stage="candidate",
        evaluation=evaluation.model_copy(update={"benchmark_id": "missing"}),
        benchmark_registry=registry,
        hypothesis_registered=True,
    )
    assert unregistered.next_stage == "candidate"
    assert "registered benchmark" in unregistered.reason
