from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from research_os.forecasting.backtest import BacktestResult


class FoldAvailability(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fold_id: str
    train_cutoff: datetime
    feature_availability: tuple[datetime, ...]
    label_maturity: tuple[datetime, ...]


class ForecastModelCard(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    model_id: str
    model_version: str
    model_kind: str
    features: tuple[str, ...] = Field(min_length=1)
    target: str
    benchmark_id: str
    benchmark_version: str
    train_cutoff: datetime
    fold_availability: tuple[FoldAvailability, ...] = Field(min_length=1)
    label_maturity: tuple[datetime, ...] = Field(min_length=1)
    evaluation_ts: datetime
    environment: Mapping[str, str]
    limitations: tuple[str, ...] = Field(min_length=1)

    @field_validator("environment")
    @classmethod
    def _freeze_environment(cls, value: Mapping[str, str]) -> Mapping[str, str]:
        if not value or any(
            not key.strip() or not item.strip() for key, item in value.items()
        ):
            raise ValueError("model-card environment entries must be non-empty")
        return MappingProxyType(dict(sorted(value.items())))

    @field_serializer("environment")
    def _serialize_environment(self, value: Mapping[str, str]) -> dict[str, str]:
        return dict(value)

    @classmethod
    def from_backtest(
        cls,
        *,
        model_id: str,
        model_version: str,
        result: BacktestResult,
        environment: Mapping[str, str],
        limitations: tuple[str, ...],
    ) -> ForecastModelCard:
        fold_availability = tuple(
            FoldAvailability(
                fold_id=fold.fold_id,
                train_cutoff=fold.train_cutoff,
                feature_availability=tuple(
                    timestamp
                    for item in fold.train_observations
                    for timestamp in item.feature_available_ts.values()
                ),
                label_maturity=tuple(
                    item.label_mature_ts for item in fold.train_observations
                ),
            )
            for fold in result.folds
        )
        label_maturity = tuple(
            item.label_mature_ts
            for fold in result.folds
            for item in fold.test_observations
        )
        return cls(
            model_id=model_id,
            model_version=model_version,
            model_kind=result.model_kind,
            features=result.feature_names,
            target=result.target,
            benchmark_id=result.benchmark_id,
            benchmark_version=result.benchmark_version,
            train_cutoff=result.train_cutoff,
            fold_availability=fold_availability,
            label_maturity=label_maturity,
            evaluation_ts=result.evaluation_ts,
            environment=environment,
            limitations=limitations,
        )


__all__ = ["FoldAvailability", "ForecastModelCard"]
