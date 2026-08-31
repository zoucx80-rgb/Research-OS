from __future__ import annotations

from collections.abc import Callable, Iterable

from .execution import pytest_batch_runner
from .manifest import CURRENT_RELEASE
from .verification import resolve_release_checks


CHECKS: dict[str, str] = resolve_release_checks(CURRENT_RELEASE)


def run_release_checks(
    runner: Callable[[str], bool] | None = None,
    batch_runner: Callable[[Iterable[str]], bool] | None = None,
) -> dict[str, bool]:
    """Run the checks selected by the canonical release manifest."""

    if runner is not None:
        return {name: bool(runner(nodeid)) for name, nodeid in CHECKS.items()}
    batch = batch_runner or pytest_batch_runner
    passed = bool(batch(CHECKS.values()))
    return {name: passed for name in CHECKS}
