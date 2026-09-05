from __future__ import annotations

import pytest

from research_os.valuation.methods import PEMethod
from research_os.valuation.registry import (
    ValuationMethodRegistry,
    builtin_valuation_method_registry,
)


def test_builtin_registry_contains_supported_methods() -> None:
    registry = builtin_valuation_method_registry()

    assert tuple(item.method_id for item in registry.methods) == ("dcf", "pb", "pe", "sotp")
    assert registry.require("pe").method_id == "pe"


def test_conflicting_method_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate valuation method"):
        ValuationMethodRegistry((PEMethod(), PEMethod()))


def test_registry_is_immutable_and_missing_method_fails_closed() -> None:
    registry = builtin_valuation_method_registry()

    with pytest.raises(KeyError, match="unregistered valuation method: ps"):
        registry.require("ps")
    with pytest.raises(AttributeError, match="immutable"):
        registry.methods = ()
