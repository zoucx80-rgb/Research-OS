from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


COMPARISON_BASIS_REQUIRED = "COMPARISON_BASIS_REQUIRED"
COMPARISON_BASIS_MISMATCH = "COMPARISON_BASIS_MISMATCH"


def common_comparison_basis(
    facts: Mapping[str, Any],
    fact_names: Sequence[str],
) -> str | None:
    """Return a reason code when present delta facts are not comparable."""

    bases = [facts.get(f"{name}_comparison_basis") for name in fact_names]
    if any(not isinstance(value, str) or not value.strip() for value in bases):
        return COMPARISON_BASIS_REQUIRED
    if len(set(bases)) != 1:
        return COMPARISON_BASIS_MISMATCH
    return None


def comparable_ratio(
    facts: Mapping[str, Any],
    numerator: str,
    denominator: str,
) -> tuple[float | None, str | None]:
    numerator_value = facts.get(numerator)
    denominator_value = facts.get(denominator)
    if numerator_value is None or denominator_value is None:
        return None, None

    reason = common_comparison_basis(facts, (numerator, denominator))
    if reason is not None:
        return None, reason
    if denominator_value == 0:
        return None, None
    return numerator_value / denominator_value, None
