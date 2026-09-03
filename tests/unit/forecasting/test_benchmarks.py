from __future__ import annotations

import pytest

from research_os.forecasting.benchmarks import (
    BenchmarkDefinition,
    BenchmarkRegistry,
    BenchmarkRegistryConflictError,
)


def test_registered_benchmarks_are_versioned_and_deterministic() -> None:
    last_value = BenchmarkDefinition(
        benchmark_id="naive:last_value",
        version="1.0.0",
        strategy="LAST_VALUE",
    )
    historical_mean = BenchmarkDefinition(
        benchmark_id="naive:historical_mean",
        version="1.0.0",
        strategy="HISTORICAL_MEAN",
    )

    registry = BenchmarkRegistry((historical_mean, last_value))

    assert [item.benchmark_id for item in registry.definitions] == [
        "naive:historical_mean",
        "naive:last_value",
    ]
    assert registry.predict("naive:last_value", (1.0, 2.0, 5.0)) == 5.0
    assert registry.predict("naive:historical_mean", (1.0, 2.0, 6.0)) == 3.0
    assert len(registry.fingerprint) == 64


def test_benchmark_registry_rejects_duplicate_identity_and_missing_history() -> None:
    definition = BenchmarkDefinition(
        benchmark_id="naive:last_value",
        version="1.0.0",
        strategy="LAST_VALUE",
    )

    with pytest.raises(BenchmarkRegistryConflictError, match="duplicate"):
        BenchmarkRegistry((definition, definition))

    registry = BenchmarkRegistry((definition,))
    with pytest.raises(ValueError, match="history"):
        registry.predict("naive:last_value", ())
