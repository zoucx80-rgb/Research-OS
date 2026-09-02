from __future__ import annotations

from research_os.application.command import ResearchRunCommand
from research_os.application.result import (
    ComponentFingerprint,
    ResearchRunResult,
    ResearchSnapshotDescriptor,
    RunVersionSet,
)
from research_os.completion import ExecutionCompletionResult
from research_os.plugins.resolver import StrategyResolution
from research_os.readiness import ResearchReadinessAssessment
from research_os.runtime.engine import TypedExecutionResult


class RunFinalizer:
    """Assemble immutable run metadata without producing semantic artifacts."""

    def finalize(
        self,
        *,
        command: ResearchRunCommand,
        execution: TypedExecutionResult,
        strategy: StrategyResolution,
        completion: ExecutionCompletionResult,
        readiness: ResearchReadinessAssessment,
        versions: RunVersionSet,
        component_fingerprints: tuple[ComponentFingerprint, ...],
        snapshot: ResearchSnapshotDescriptor | None = None,
    ) -> ResearchRunResult:
        return ResearchRunResult(
            run_id=command.context.run_id,
            company=command.context.company,
            decision_ts=command.context.decision_ts,
            baseline=command.context.baseline,
            strategy_resolution=strategy,
            artifacts=execution.snapshot,
            module_results=execution.module_results,
            execution_completion=completion,
            research_readiness=readiness,
            versions=versions,
            component_fingerprints=component_fingerprints,
            snapshot=snapshot,
        )
