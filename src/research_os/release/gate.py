from pydantic import BaseModel

from .manifest import CURRENT_RELEASE
from .verification import resolve_release_checks


REQUIRED = tuple(resolve_release_checks(CURRENT_RELEASE))


class ReleaseGateResult(BaseModel):
    ready: bool
    passed: list[str]
    failed: list[str]


def evaluate_release_gate(status: dict[str, bool]) -> ReleaseGateResult:
    passed = [key for key in REQUIRED if status.get(key) is True]
    failed = [key for key in REQUIRED if status.get(key) is not True]
    return ReleaseGateResult(ready=not failed, passed=passed, failed=failed)
