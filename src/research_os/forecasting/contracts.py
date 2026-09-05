from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.contracts.artifact_values import DomainArtifact, LineageValue
from research_os.forecasting.backtest import ForecastObservation
from research_os.forecasting.promotion import ModelStage


ForecastMetricName = Literal["MAE", "RMSE", "DIRECTION_ACCURACY", "INTERVAL_COVERAGE"]


def _canonical_strings(values: tuple[str, ...], *, label: str) -> tuple[str, ...]:
    normalized = tuple(value.strip() for value in values)
    if any(not value for value in normalized):
        raise ValueError(f"{label} must be non-empty")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} must be unique")
    return tuple(sorted(normalized))


def _finite(value: Decimal, *, label: str) -> Decimal:
    if not value.is_finite():
        raise ValueError(f"{label} must be finite")
    return value


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

    @field_validator(
        "hypothesis_key",
        "model_key",
        "target_metric",
        "horizon",
        "benchmark_id",
        "applicability",
        "model_boundary",
    )
    @classmethod
    def _non_empty_identities(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("forecast experiment fields must be non-empty")
        return normalized

    @field_validator("feature_names")
    @classmethod
    def _unique_features(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("feature names must be non-empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("feature names must be unique")
        return normalized

    @field_validator("observations")
    @classmethod
    def _canonical_observations(
        cls,
        value: tuple[ForecastObservation, ...],
    ) -> tuple[ForecastObservation, ...]:
        identities = tuple(item.observation_id for item in value)
        if len(identities) != len(set(identities)):
            raise ValueError("forecast observation identities must be unique")
        return tuple(sorted(value, key=lambda item: (item.observed_ts, item.observation_id)))

    @field_validator("evaluation_ts")
    @classmethod
    def _utc_evaluation(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluation_ts must be timezone-aware")
        return value.astimezone(timezone.utc)

    @field_validator("caveats")
    @classmethod
    def _canonical_caveats(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return _canonical_strings(value, label="forecast caveats")

    @model_validator(mode="after")
    def _target_is_not_a_feature(self) -> Self:
        if self.target_metric in self.feature_names or "realized_outcome" in self.feature_names:
            raise ValueError("target metric cannot be a feature")
        return self


class ForecastMetricEvidence(LineageValue):
    metric_name: ForecastMetricName
    value: Decimal

    @field_validator("value")
    @classmethod
    def _finite_value(cls, value: Decimal) -> Decimal:
        return _finite(value, label="forecast metric value")

    @model_validator(mode="after")
    def _requires_lineage(self) -> Self:
        if not (self.evidence_refs or self.assumption_refs):
            raise ValueError("forecast metric evidence requires lineage")
        return self


class ForecastStabilityEvidence(LineageValue):
    window_key: str
    model_mae: Decimal
    benchmark_mae: Decimal

    @field_validator("window_key")
    @classmethod
    def _non_empty_window(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("forecast stability window key must be non-empty")
        return normalized

    @field_validator("model_mae", "benchmark_mae")
    @classmethod
    def _finite_mae(cls, value: Decimal) -> Decimal:
        return _finite(value, label="forecast stability MAE")

    @model_validator(mode="after")
    def _requires_lineage(self) -> Self:
        if not (self.evidence_refs or self.assumption_refs):
            raise ValueError("forecast stability evidence requires lineage")
        return self


class ForecastBenchmarkEvidence(DomainArtifact):
    model_key: str | None = None
    target_metric: str | None = None
    horizon: str | None = None
    benchmark_key: str | None = None
    benchmark_version: str | None = None
    sample_count: int = Field(default=0, ge=0)
    fold_count: int = Field(default=0, ge=0)
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

    @field_validator(
        "model_key",
        "target_metric",
        "horizon",
        "benchmark_key",
        "benchmark_version",
        "promotion_reason",
        "applicability",
        "model_boundary",
    )
    @classmethod
    def _non_empty_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("forecast benchmark identity fields must be non-empty")
        return normalized

    @field_validator("benchmark_mae", "improvement")
    @classmethod
    def _finite_optional_metric(cls, value: Decimal | None) -> Decimal | None:
        return None if value is None else _finite(value, label="forecast benchmark metric")

    @field_validator("metrics")
    @classmethod
    def _canonical_metrics(
        cls,
        value: tuple[ForecastMetricEvidence, ...],
    ) -> tuple[ForecastMetricEvidence, ...]:
        identities = tuple(item.metric_name for item in value)
        if len(identities) != len(set(identities)):
            raise ValueError("forecast metric names must be unique")
        order = {
            name: index
            for index, name in enumerate(("MAE", "RMSE", "DIRECTION_ACCURACY", "INTERVAL_COVERAGE"))
        }
        return tuple(sorted(value, key=lambda item: order[item.metric_name]))

    @field_validator("stability_windows")
    @classmethod
    def _canonical_windows(
        cls,
        value: tuple[ForecastStabilityEvidence, ...],
    ) -> tuple[ForecastStabilityEvidence, ...]:
        identities = tuple(item.window_key for item in value)
        if len(identities) != len(set(identities)):
            raise ValueError("forecast stability window identities must be unique")
        return tuple(sorted(value, key=lambda item: item.window_key))

    @field_validator("caveats", "reason_codes")
    @classmethod
    def _canonical_codes(cls, value: tuple[str, ...], info: object) -> tuple[str, ...]:
        return _canonical_strings(
            value,
            label=getattr(info, "field_name", "forecast codes").replace("_", " "),
        )

    @model_validator(mode="after")
    def _folds_fit_sample(self) -> Self:
        if self.fold_count > self.sample_count:
            raise ValueError("forecast fold count cannot exceed sample count")
        return self
