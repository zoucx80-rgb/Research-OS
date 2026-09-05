from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from research_os.valuation.methods import (
    DCFMethod,
    PBMethod,
    PEMethod,
    SOTPMethod,
    ValuationMethodInput,
    ValuationMethodResult,
)


class ValuationMethod(Protocol):
    method_id: str

    def execute(self, inputs: ValuationMethodInput) -> ValuationMethodResult: ...


class ValuationMethodRegistry:
    __slots__ = ("_methods", "methods")
    _methods: dict[str, ValuationMethod]
    methods: tuple[ValuationMethod, ...]

    def __init__(self, methods: Iterable[ValuationMethod]) -> None:
        by_id: dict[str, ValuationMethod] = {}
        for method in methods:
            if method.method_id in by_id:
                raise ValueError(f"duplicate valuation method: {method.method_id}")
            by_id[method.method_id] = method
        object.__setattr__(self, "_methods", by_id)
        object.__setattr__(self, "methods", tuple(by_id[key] for key in sorted(by_id)))

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ValuationMethodRegistry is immutable")

    def get(self, method_id: str) -> ValuationMethod | None:
        return self._methods.get(method_id)

    def require(self, method_id: str) -> ValuationMethod:
        method = self.get(method_id)
        if method is None:
            raise KeyError(f"unregistered valuation method: {method_id}")
        return method


def builtin_valuation_method_registry() -> ValuationMethodRegistry:
    return ValuationMethodRegistry((DCFMethod(), PBMethod(), PEMethod(), SOTPMethod()))


__all__ = [
    "ValuationMethod",
    "ValuationMethodRegistry",
    "builtin_valuation_method_registry",
]
