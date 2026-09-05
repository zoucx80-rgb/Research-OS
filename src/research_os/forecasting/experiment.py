from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from research_os.forecasting.benchmarks import BenchmarkRegistry
from research_os.forecasting.contracts import ForecastExperimentInput


class ForecastExperimentAssessment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["READY", "INSUFFICIENT_EVIDENCE"]
    reason_codes: tuple[str, ...] = ()

    @field_validator("reason_codes")
    @classmethod
    def _canonical_reasons(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(item.strip() for item in value)
        if any(not item for item in normalized):
            raise ValueError("forecast experiment reason codes must be non-empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("forecast experiment reason codes must be unique")
        return tuple(sorted(normalized))

    @model_validator(mode="after")
    def _status_matches_reasons(self) -> Self:
        if self.status == "READY" and self.reason_codes:
            raise ValueError("ready forecast experiment cannot have insufficiency reasons")
        if self.status == "INSUFFICIENT_EVIDENCE" and not self.reason_codes:
            raise ValueError("insufficient forecast experiment requires reason codes")
        return self


class ForecastExperimentValidator:
    def __init__(self, benchmark_registry: BenchmarkRegistry) -> None:
        self._benchmarks = benchmark_registry

    def assess(
        self,
        experiment: ForecastExperimentInput,
        *,
        registered_hypotheses: set[str] | frozenset[str],
        decision_ts: datetime,
    ) -> ForecastExperimentAssessment:
        decision_ts = self._utc(decision_ts, field="decision_ts")
        if experiment.evaluation_ts > decision_ts:
            raise ValueError("evaluation timestamp exceeds decision timestamp")
        observed_times = tuple(item.observed_ts for item in experiment.observations)
        if observed_times != tuple(sorted(observed_times)):
            raise ValueError("forecast observations must be chronological")
        if any(item.observed_ts > experiment.evaluation_ts for item in experiment.observations):
            raise ValueError("observation timestamp exceeds evaluation timestamp")
        if any(
            available_ts > experiment.evaluation_ts
            for item in experiment.observations
            for available_ts in item.feature_available_ts.values()
        ):
            raise ValueError("feature availability exceeds evaluation timestamp")
        if any(item.label_mature_ts > experiment.evaluation_ts for item in experiment.observations):
            raise ValueError("label maturity exceeds evaluation timestamp")
        missing_features = sorted(
            {
                feature
                for item in experiment.observations
                for feature in experiment.feature_names
                if feature not in item.features
            }
        )
        if missing_features:
            raise ValueError(
                "selected forecast features are missing: " + ", ".join(missing_features)
            )

        reasons = []
        if len(experiment.observations) < experiment.n_splits + 2:
            reasons.append("INSUFFICIENT_OBSERVATIONS")
        if self._benchmarks.get(experiment.benchmark_id) is None:
            reasons.append("UNREGISTERED_BENCHMARK")
        if experiment.hypothesis_key not in registered_hypotheses:
            reasons.append("HYPOTHESIS_NOT_PREREGISTERED")
        return ForecastExperimentAssessment(
            status="INSUFFICIENT_EVIDENCE" if reasons else "READY",
            reason_codes=tuple(reasons),
        )

    @staticmethod
    def _utc(value: datetime, *, field: str) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{field} must be timezone-aware")
        return value.astimezone(timezone.utc)
