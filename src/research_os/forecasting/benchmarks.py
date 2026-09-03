from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from statistics import fmean
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


BenchmarkStrategy = Literal["LAST_VALUE", "HISTORICAL_MEAN"]


class BenchmarkDefinition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    benchmark_id: str
    version: str
    strategy: BenchmarkStrategy
    description: str = "Registered forecast benchmark."

    @field_validator("benchmark_id", "version", "description")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("benchmark identity fields must be non-empty")
        return normalized


class BenchmarkRegistryConflictError(ValueError):
    pass


class BenchmarkRegistry:
    __slots__ = ("_definitions", "definitions", "fingerprint")
    _definitions: dict[str, BenchmarkDefinition]
    definitions: tuple[BenchmarkDefinition, ...]
    fingerprint: str

    def __init__(self, definitions: Iterable[BenchmarkDefinition] = ()) -> None:
        by_id: dict[str, BenchmarkDefinition] = {}
        for definition in definitions:
            if definition.benchmark_id in by_id:
                raise BenchmarkRegistryConflictError(
                    f"duplicate benchmark ID: {definition.benchmark_id}"
                )
            by_id[definition.benchmark_id] = definition
        ordered = tuple(by_id[key] for key in sorted(by_id))
        payload = [item.model_dump(mode="json") for item in ordered]
        fingerprint = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        object.__setattr__(self, "_definitions", by_id)
        object.__setattr__(self, "definitions", ordered)
        object.__setattr__(self, "fingerprint", fingerprint)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("BenchmarkRegistry is immutable")

    def get(self, benchmark_id: str) -> BenchmarkDefinition | None:
        return self._definitions.get(benchmark_id)

    def require(self, benchmark_id: str) -> BenchmarkDefinition:
        definition = self.get(benchmark_id)
        if definition is None:
            raise KeyError(f"unregistered benchmark: {benchmark_id}")
        return definition

    def predict(self, benchmark_id: str, history: Sequence[float]) -> float:
        if not history:
            raise ValueError("benchmark prediction requires observed history")
        definition = self.require(benchmark_id)
        if definition.strategy == "LAST_VALUE":
            return float(history[-1])
        return float(fmean(history))


def builtin_benchmark_registry() -> BenchmarkRegistry:
    return BenchmarkRegistry(
        (
            BenchmarkDefinition(
                benchmark_id="naive:last_value",
                version="1.0.0",
                strategy="LAST_VALUE",
                description="Use the most recent mature outcome.",
            ),
            BenchmarkDefinition(
                benchmark_id="naive:historical_mean",
                version="1.0.0",
                strategy="HISTORICAL_MEAN",
                description="Use the mean of mature historical outcomes.",
            ),
        )
    )


__all__ = [
    "BenchmarkDefinition",
    "BenchmarkRegistry",
    "BenchmarkRegistryConflictError",
    "BenchmarkStrategy",
    "builtin_benchmark_registry",
]
