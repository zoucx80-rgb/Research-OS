from __future__ import annotations

from collections.abc import Iterable

from research_os.completion.models import ExecutionCompletionResult
from research_os.contracts.errors import CompletionEvaluationError
from research_os.runtime.module_plan import ModulePlan
from research_os.runtime.modules import ModuleResult


class ExecutionCompletionEvaluator:
    """Evaluate execution completion from compiled plans and module outcomes."""

    def evaluate(
        self,
        plans: Iterable[ModulePlan],
        module_results: Iterable[ModuleResult],
    ) -> ExecutionCompletionResult:
        modules = {
            module.spec.module_id: module.spec
            for plan in plans
            for module in plan.modules
        }
        statuses = {}
        for result in module_results:
            if result.module_id not in modules:
                raise CompletionEvaluationError(
                    f"module result is not part of the compiled plans: {result.module_id}"
                )
            if result.module_id in statuses:
                raise CompletionEvaluationError(
                    f"duplicate module result: {result.module_id}"
                )
            statuses[result.module_id] = result.status

        blocking = tuple(
            sorted(
                module_id
                for module_id, spec in modules.items()
                if spec.required_for_completion
                and statuses.get(module_id) not in {"PASS", "NOT_APPLICABLE"}
            )
        )
        return ExecutionCompletionResult(
            final_status="INCOMPLETE" if blocking else "COMPLETE",
            blocking_capabilities=blocking,
            module_statuses=statuses,
        )
