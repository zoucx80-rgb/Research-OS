from __future__ import annotations

from dataclasses import dataclass

from research_os.completion import ExecutionCompletionEvaluator
from research_os.runtime.module_plan import ModulePlan
from research_os.runtime.modules import ModuleResult, ModuleSpec


@dataclass(frozen=True)
class _Module:
    spec: ModuleSpec

    def run(self, context, state):  # pragma: no cover - never executed here
        raise AssertionError("completion evaluation must not execute modules")


def _module(module_id: str, *, required: bool = True) -> _Module:
    return _Module(
        ModuleSpec(
            module_id=module_id,
            module_version="2.0.0",
            required_for_completion=required,
        )
    )


def test_completion_uses_required_plan_modules_and_keeps_not_applicable_nonblocking():
    plan = ModulePlan(
        modules=(
            _module("required:pass"),
            _module("required:na"),
            _module("optional:fail", required=False),
        )
    )
    results = (
        ModuleResult(module_id="required:pass", status="PASS"),
        ModuleResult(module_id="required:na", status="NOT_APPLICABLE"),
        ModuleResult(module_id="optional:fail", status="FAIL"),
    )

    completion = ExecutionCompletionEvaluator().evaluate((plan,), results)

    assert completion.final_status == "COMPLETE"
    assert completion.blocking_capabilities == ()
    assert dict(completion.module_statuses) == {
        "optional:fail": "FAIL",
        "required:na": "NOT_APPLICABLE",
        "required:pass": "PASS",
    }


def test_completion_blocks_missing_failed_and_insufficient_required_modules():
    plan = ModulePlan(
        modules=(
            _module("required:missing"),
            _module("required:failed"),
            _module("required:no-evidence"),
        )
    )
    results = (
        ModuleResult(module_id="required:failed", status="FAIL"),
        ModuleResult(module_id="required:no-evidence", status="INSUFFICIENT_EVIDENCE"),
    )

    completion = ExecutionCompletionEvaluator().evaluate((plan,), results)

    assert completion.final_status == "INCOMPLETE"
    assert completion.blocking_capabilities == (
        "required:failed",
        "required:missing",
        "required:no-evidence",
    )
