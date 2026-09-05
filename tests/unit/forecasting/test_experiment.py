from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from research_os.contracts.evidence import EvidenceRef
from research_os.forecasting import (
    ForecastExperimentInput,
    ForecastExperimentValidator,
    ForecastObservation,
    builtin_benchmark_registry,
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


def _experiment(count: int, **updates: object) -> ForecastExperimentInput:
    payload = {
        "hypothesis_key": "hyp:revenue",
        "model_key": "ols:revenue",
        "target_metric": "revenue_growth",
        "horizon": "FY+1",
        "feature_names": ("orders",),
        "observations": tuple(_observation(index) for index in range(1, count + 1)),
        "benchmark_id": "naive:last_value",
        "evaluation_ts": DECISION_TS,
        "n_splits": 3,
        "applicability": "annual comparable periods",
        "model_boundary": "linear explanatory forecast",
    }
    payload.update(updates)
    return ForecastExperimentInput.model_validate(payload)


def _validator() -> ForecastExperimentValidator:
    return ForecastExperimentValidator(builtin_benchmark_registry())


def test_insufficient_sample_is_typed_not_exception() -> None:
    assessment = _validator().assess(
        _experiment(4),
        registered_hypotheses={"hyp:revenue"},
        decision_ts=DECISION_TS,
    )

    assert assessment.status == "INSUFFICIENT_EVIDENCE"
    assert assessment.reason_codes == ("INSUFFICIENT_OBSERVATIONS",)


def test_unregistered_benchmark_and_hypothesis_are_typed_insufficient() -> None:
    assessment = _validator().assess(
        _experiment(5, benchmark_id="unknown"),
        registered_hypotheses={"hyp:other"},
        decision_ts=DECISION_TS,
    )

    assert assessment.status == "INSUFFICIENT_EVIDENCE"
    assert assessment.reason_codes == (
        "HYPOTHESIS_NOT_PREREGISTERED",
        "UNREGISTERED_BENCHMARK",
    )


def test_ready_experiment_meets_sample_benchmark_and_registration_gates() -> None:
    assessment = _validator().assess(
        _experiment(5),
        registered_hypotheses={"hyp:revenue"},
        decision_ts=DECISION_TS,
    )

    assert assessment.status == "READY"
    assert assessment.reason_codes == ()


def test_future_evaluation_and_immature_labels_are_execution_errors() -> None:
    with pytest.raises(ValueError, match="evaluation timestamp exceeds decision timestamp"):
        _validator().assess(
            _experiment(5, evaluation_ts=DECISION_TS + timedelta(seconds=1)),
            registered_hypotheses={"hyp:revenue"},
            decision_ts=DECISION_TS,
        )

    immature = _observation(5).model_copy(
        update={"label_mature_ts": DECISION_TS + timedelta(seconds=1)}
    )
    experiment = _experiment(
        5,
        observations=(*tuple(_observation(index) for index in range(1, 5)), immature),
    )
    with pytest.raises(ValueError, match="label maturity exceeds evaluation timestamp"):
        _validator().assess(
            experiment,
            registered_hypotheses={"hyp:revenue"},
            decision_ts=DECISION_TS,
        )
