from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from research_os.contracts.evidence import EvidenceRef
from research_os.forecasting import (
    ForecastBenchmarkEvidence,
    ForecastExperimentInput,
    ForecastMetricEvidence,
    ForecastObservation,
    ForecastStabilityEvidence,
)


DECISION_TS = datetime(2026, 9, 4, tzinfo=timezone.utc)


def _observation(index: int) -> ForecastObservation:
    observed_ts = datetime(2020 + index, 1, 1, tzinfo=timezone.utc)
    return ForecastObservation(
        observation_id=f"obs:{index}",
        observed_ts=observed_ts,
        feature_available_ts={"orders": observed_ts - timedelta(days=1)},
        label_mature_ts=observed_ts + timedelta(days=90),
        features={"orders": float(index)},
        realized_outcome=float(index * 2),
        evidence_refs=(
            EvidenceRef(
                evidence_id=f"ev:forecast:{index}",
                revision=1,
                content_fingerprint=f"{index:064x}",
            ),
        ),
    )


def _experiment(**updates: object) -> ForecastExperimentInput:
    payload = {
        "hypothesis_key": "hyp:revenue",
        "model_key": "ols:revenue",
        "target_metric": "revenue_growth",
        "horizon": "FY+1",
        "feature_names": ("orders",),
        "observations": (_observation(2), _observation(1)),
        "benchmark_id": "naive:last_value",
        "evaluation_ts": DECISION_TS,
        "n_splits": 3,
        "current_model_stage": "experimental",
        "applicability": "annual comparable periods",
        "model_boundary": "linear explanatory forecast",
    }
    payload.update(updates)
    return ForecastExperimentInput.model_validate(payload)


def test_experiment_requires_unique_features_and_utc_evaluation() -> None:
    with pytest.raises(ValidationError, match="feature names must be unique"):
        _experiment(feature_names=("orders", "orders"))

    with pytest.raises(ValidationError, match="evaluation_ts must be timezone-aware"):
        _experiment(evaluation_ts=datetime(2026, 9, 4))


def test_experiment_rejects_target_leakage_and_canonicalizes_observations() -> None:
    with pytest.raises(ValidationError, match="target metric cannot be a feature"):
        _experiment(feature_names=("revenue_growth",))

    experiment = _experiment()
    assert tuple(item.observation_id for item in experiment.observations) == ("obs:1", "obs:2")

    with pytest.raises(ValidationError, match="observation identities must be unique"):
        _experiment(observations=(_observation(1), _observation(1)))


def test_benchmark_evidence_canonicalizes_metrics_windows_and_codes() -> None:
    reference = _observation(1).evidence_refs[0]
    evidence = ForecastBenchmarkEvidence(
        domain_status="SUPPORTED",
        model_key="ols:revenue",
        target_metric="revenue_growth",
        horizon="FY+1",
        benchmark_key="naive:last_value",
        benchmark_version="1.0.0",
        sample_count=6,
        fold_count=2,
        out_of_sample=True,
        pit_compliant=True,
        metrics=(
            ForecastMetricEvidence(
                metric_name="RMSE", value=Decimal("0.2"), evidence_refs=(reference,)
            ),
            ForecastMetricEvidence(
                metric_name="MAE", value=Decimal("0.1"), evidence_refs=(reference,)
            ),
        ),
        stability_windows=(
            ForecastStabilityEvidence(
                window_key="fold:2",
                model_mae=Decimal("0.1"),
                benchmark_mae=Decimal("0.2"),
                evidence_refs=(reference,),
            ),
            ForecastStabilityEvidence(
                window_key="fold:1",
                model_mae=Decimal("0.1"),
                benchmark_mae=Decimal("0.2"),
                evidence_refs=(reference,),
            ),
        ),
        reason_codes=("B", "A"),
    )

    assert tuple(item.metric_name for item in evidence.metrics) == ("MAE", "RMSE")
    assert tuple(item.window_key for item in evidence.stability_windows) == ("fold:1", "fold:2")
    assert evidence.reason_codes == ("A", "B")

    duplicate_metric_payload = evidence.model_dump()
    duplicate_metric_payload["metrics"] = (evidence.metrics[0], evidence.metrics[0])
    with pytest.raises(ValidationError, match="forecast metric names must be unique"):
        ForecastBenchmarkEvidence.model_validate(duplicate_metric_payload)


def test_metric_and_stability_evidence_require_revision_bound_lineage() -> None:
    with pytest.raises(ValidationError, match="forecast metric evidence requires lineage"):
        ForecastMetricEvidence(metric_name="MAE", value=Decimal("0.1"))

    with pytest.raises(ValidationError, match="forecast stability evidence requires lineage"):
        ForecastStabilityEvidence(
            window_key="fold:1",
            model_mae=Decimal("0.1"),
            benchmark_mae=Decimal("0.2"),
        )
