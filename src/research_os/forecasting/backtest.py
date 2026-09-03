from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from math import isfinite
from typing import Literal

import numpy as np
import statsmodels.api as sm  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sklearn.metrics import mean_absolute_error, root_mean_squared_error  # type: ignore[import-untyped]
from sklearn.model_selection import TimeSeriesSplit  # type: ignore[import-untyped]

from research_os.contracts.evidence import EvidenceRef
from research_os.forecasting.benchmarks import BenchmarkRegistry


def _utc(value: datetime, *, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _unique_refs(references: Sequence[EvidenceRef]) -> tuple[EvidenceRef, ...]:
    return tuple(
        {
            (item.evidence_id, item.revision, item.content_fingerprint): item
            for item in references
        }.values()
    )


class ForecastObservation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    observation_id: str
    observed_ts: datetime
    feature_available_ts: Mapping[str, datetime]
    label_mature_ts: datetime
    features: Mapping[str, float]
    realized_outcome: float
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)

    @field_validator("observation_id")
    @classmethod
    def _identity_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("observation identity must be non-empty")
        return normalized

    @field_validator("observed_ts", "label_mature_ts")
    @classmethod
    def _timestamps_are_utc(cls, value: datetime, info: object) -> datetime:
        return _utc(value, field=getattr(info, "field_name", "timestamp"))

    @field_validator("feature_available_ts")
    @classmethod
    def _feature_timestamps_are_utc(
        cls, value: Mapping[str, datetime]
    ) -> Mapping[str, datetime]:
        return {
            name: _utc(timestamp, field=f"feature_available_ts.{name}")
            for name, timestamp in value.items()
        }

    @model_validator(mode="after")
    def _features_have_availability_and_finite_values(self) -> ForecastObservation:
        if not self.features:
            raise ValueError("forecast observation requires features")
        if set(self.features) != set(self.feature_available_ts):
            raise ValueError("every feature must have exactly one availability timestamp")
        if not isfinite(self.realized_outcome) or any(
            not isfinite(value) for value in self.features.values()
        ):
            raise ValueError("forecast values must be finite")
        return self


class BacktestFold(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fold_id: str
    train_cutoff: datetime
    evaluation_ts: datetime
    train_observations: tuple[ForecastObservation, ...] = Field(min_length=1)
    test_observations: tuple[ForecastObservation, ...] = Field(min_length=1)

    @field_validator("train_cutoff", "evaluation_ts")
    @classmethod
    def _timestamps_are_utc(cls, value: datetime, info: object) -> datetime:
        return _utc(value, field=getattr(info, "field_name", "timestamp"))

    @model_validator(mode="after")
    def _reject_temporal_leakage(self) -> BacktestFold:
        if "realized_outcome" in {
            feature
            for item in (*self.train_observations, *self.test_observations)
            for feature in item.features
        }:
            raise ValueError("realized outcome cannot be used as a feature")
        if any(
            item.observed_ts > self.train_cutoff for item in self.train_observations
        ):
            raise ValueError("post-cutoff observation cannot enter training")
        if any(
            available_ts > self.train_cutoff
            for item in self.train_observations
            for available_ts in item.feature_available_ts.values()
        ):
            raise ValueError("training feature availability exceeds train cutoff")
        if any(
            item.label_mature_ts > self.train_cutoff
            for item in self.train_observations
        ):
            raise ValueError("training label maturity exceeds train cutoff")
        if any(
            available_ts > item.observed_ts
            for item in self.test_observations
            for available_ts in item.feature_available_ts.values()
        ):
            raise ValueError("test feature availability exceeds forecast origin")
        if any(
            item.label_mature_ts > self.evaluation_ts
            for item in self.test_observations
        ):
            raise ValueError("test label maturity exceeds evaluation timestamp")
        train_times = tuple(item.observed_ts for item in self.train_observations)
        test_times = tuple(item.observed_ts for item in self.test_observations)
        if train_times != tuple(sorted(train_times)) or test_times != tuple(
            sorted(test_times)
        ):
            raise ValueError("time-series folds must preserve chronological order")
        if max(train_times) >= min(test_times):
            raise ValueError("time-series training must strictly precede test data")
        return self


BacktestMetricName = Literal[
    "MAE", "RMSE", "DIRECTION_ACCURACY", "INTERVAL_COVERAGE"
]


class BacktestMetric(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: BacktestMetricName
    value: float
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)

    @field_validator("value")
    @classmethod
    def _finite(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("backtest metric must be finite")
        return value


class StabilityWindow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    window_id: str
    model_mae: float
    benchmark_mae: float
    evidence_refs: tuple[EvidenceRef, ...] = Field(min_length=1)


class BacktestResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model_kind: Literal["STATSMODELS_OLS"]
    feature_names: tuple[str, ...] = Field(min_length=1)
    target: str
    benchmark_id: str
    benchmark_version: str
    train_cutoff: datetime
    evaluation_ts: datetime
    out_of_sample: bool
    pit_compliant: bool
    folds: tuple[BacktestFold, ...]
    metrics: tuple[BacktestMetric, ...] = Field(min_length=4)
    benchmark_mae: float
    stability_windows: tuple[StabilityWindow, ...] = Field(min_length=1)

    @field_validator("train_cutoff", "evaluation_ts")
    @classmethod
    def _timestamps_are_utc(cls, value: datetime, info: object) -> datetime:
        return _utc(value, field=getattr(info, "field_name", "timestamp"))

    def metric(self, name: BacktestMetricName) -> BacktestMetric:
        for metric in self.metrics:
            if metric.name == name:
                return metric
        raise KeyError(f"missing backtest metric: {name}")

    @property
    def stable(self) -> bool:
        return all(
            window.model_mae < window.benchmark_mae
            for window in self.stability_windows
        )


class TimeSeriesBacktester:
    def __init__(self, benchmarks: BenchmarkRegistry) -> None:
        self._benchmarks = benchmarks

    def run(
        self,
        *,
        observations: Sequence[ForecastObservation],
        feature_names: Sequence[str],
        target: str,
        benchmark_id: str,
        evaluation_ts: datetime,
        n_splits: int = 3,
    ) -> BacktestResult:
        benchmark = self._benchmarks.require(benchmark_id)
        ordered = tuple(observations)
        if len(ordered) < n_splits + 2:
            raise ValueError("insufficient observations for requested time-series splits")
        if tuple(item.observed_ts for item in ordered) != tuple(
            sorted(item.observed_ts for item in ordered)
        ):
            raise ValueError(
                "observations must be chronologically ordered; shuffle is forbidden"
            )
        selected_features = tuple(feature_names)
        if (
            not selected_features
            or target in selected_features
            or "realized_outcome" in selected_features
        ):
            raise ValueError("target or realized outcome cannot be selected as a feature")
        if any(
            feature not in item.features
            for item in ordered
            for feature in selected_features
        ):
            raise ValueError("selected feature is missing from an observation")

        evaluation_ts = _utc(evaluation_ts, field="evaluation_ts")
        splitter = TimeSeriesSplit(n_splits=n_splits)
        folds: list[BacktestFold] = []
        actuals: list[float] = []
        predictions: list[float] = []
        benchmark_predictions: list[float] = []
        lower_bounds: list[float] = []
        upper_bounds: list[float] = []
        anchors: list[float] = []
        windows: list[StabilityWindow] = []

        for fold_number, (train_indices, test_indices) in enumerate(
            splitter.split(np.arange(len(ordered))), start=1
        ):
            train = tuple(ordered[int(index)] for index in train_indices)
            test = tuple(ordered[int(index)] for index in test_indices)
            fold = BacktestFold(
                fold_id=f"fold:{fold_number}",
                train_cutoff=train[-1].observed_ts,
                evaluation_ts=evaluation_ts,
                train_observations=train,
                test_observations=test,
            )
            folds.append(fold)

            x_train = np.asarray(
                [[item.features[name] for name in selected_features] for item in train],
                dtype=float,
            )
            y_train = np.asarray(
                [item.realized_outcome for item in train], dtype=float
            )
            x_test = np.asarray(
                [[item.features[name] for name in selected_features] for item in test],
                dtype=float,
            )
            fitted = sm.OLS(
                y_train, sm.add_constant(x_train, has_constant="add")
            ).fit()
            prediction = fitted.get_prediction(
                sm.add_constant(x_test, has_constant="add")
            ).summary_frame(alpha=0.05)
            fold_actuals = [item.realized_outcome for item in test]
            fold_predictions = [float(value) for value in prediction["mean"]]
            fold_benchmarks = [
                self._benchmarks.predict(benchmark_id, tuple(y_train))
                for _ in test
            ]
            fold_refs = _unique_refs(
                [
                    reference
                    for item in (*train, *test)
                    for reference in item.evidence_refs
                ]
            )
            windows.append(
                StabilityWindow(
                    window_id=fold.fold_id,
                    model_mae=float(mean_absolute_error(fold_actuals, fold_predictions)),
                    benchmark_mae=float(
                        mean_absolute_error(fold_actuals, fold_benchmarks)
                    ),
                    evidence_refs=fold_refs,
                )
            )
            actuals.extend(fold_actuals)
            predictions.extend(fold_predictions)
            benchmark_predictions.extend(fold_benchmarks)
            lower_bounds.extend(float(value) for value in prediction["obs_ci_lower"])
            upper_bounds.extend(float(value) for value in prediction["obs_ci_upper"])
            anchors.extend(float(y_train[-1]) for _ in test)

        references = _unique_refs(
            [
                reference
                for fold in folds
                for item in (*fold.train_observations, *fold.test_observations)
                for reference in item.evidence_refs
            ]
        )
        direction_hits = [
            np.sign(predicted - anchor) == np.sign(actual - anchor)
            for predicted, actual, anchor in zip(predictions, actuals, anchors, strict=True)
        ]
        coverage_hits = [
            lower <= actual <= upper
            for lower, actual, upper in zip(
                lower_bounds, actuals, upper_bounds, strict=True
            )
        ]
        metrics = (
            BacktestMetric(
                name="MAE",
                value=float(mean_absolute_error(actuals, predictions)),
                evidence_refs=references,
            ),
            BacktestMetric(
                name="RMSE",
                value=float(root_mean_squared_error(actuals, predictions)),
                evidence_refs=references,
            ),
            BacktestMetric(
                name="DIRECTION_ACCURACY",
                value=fmean_bool(direction_hits),
                evidence_refs=references,
            ),
            BacktestMetric(
                name="INTERVAL_COVERAGE",
                value=fmean_bool(coverage_hits),
                evidence_refs=references,
            ),
        )
        return BacktestResult(
            model_kind="STATSMODELS_OLS",
            feature_names=selected_features,
            target=target,
            benchmark_id=benchmark.benchmark_id,
            benchmark_version=benchmark.version,
            train_cutoff=folds[-1].train_cutoff,
            evaluation_ts=evaluation_ts,
            out_of_sample=True,
            pit_compliant=True,
            folds=tuple(folds),
            metrics=metrics,
            benchmark_mae=float(
                mean_absolute_error(actuals, benchmark_predictions)
            ),
            stability_windows=tuple(windows),
        )


def fmean_bool(values: Sequence[bool | np.bool_]) -> float:
    if not values:
        raise ValueError("metric requires observations")
    return sum(bool(value) for value in values) / len(values)


__all__ = [
    "BacktestFold",
    "BacktestMetric",
    "BacktestResult",
    "ForecastObservation",
    "StabilityWindow",
    "TimeSeriesBacktester",
]
