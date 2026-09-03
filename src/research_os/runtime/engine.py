from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from research_os.contracts.artifacts import (
    ArtifactCatalog,
    ArtifactSnapshot,
    ArtifactStore,
    ArtifactWrite,
)
from research_os.contracts.errors import ArtifactContractError, ResearchExecutionError
from research_os.runtime.context import ResearchContext
from research_os.runtime.module_plan import ModulePlan
from research_os.runtime.modules import ModuleResult, ResearchModule
from research_os.runtime.state import ResearchStateView

if TYPE_CHECKING:
    from research_os.completion.models import ExecutionCompletionResult
    from research_os.readiness.models import ResearchReadinessAssessment


class PipelineDefinitionError(ResearchExecutionError):
    code = "PIPELINE_DEFINITION_ERROR"


class ModuleExecutionError(ResearchExecutionError):
    code = "MODULE_EXECUTION_FAILED"


@dataclass(frozen=True, slots=True)
class TypedExecutionResult:
    snapshot: ArtifactSnapshot
    module_results: tuple[ModuleResult, ...]


@dataclass(frozen=True, slots=True)
class FinalizedExecution:
    execution: TypedExecutionResult
    completion: ExecutionCompletionResult
    readiness: ResearchReadinessAssessment


def _snapshot_semantic_identity(snapshot: ArtifactSnapshot) -> tuple[object, ...]:
    """Compare immutable bootstrap snapshots by durable semantic identity."""
    return tuple(
        (
            envelope.key.artifact_id,
            envelope.key.schema_version,
            envelope.key.value_type.__qualname__,
            envelope.producer_ids,
            tuple(
                (
                    reference.evidence_id,
                    reference.revision,
                    reference.content_fingerprint,
                )
                for reference in envelope.evidence_refs
            ),
            envelope.value_fingerprint,
        )
        for envelope in snapshot.envelopes()
    )


class ResearchEngine:
    def finalize(
        self,
        *,
        plans: tuple[ModulePlan, ...],
        execution: TypedExecutionResult,
        catalog: ArtifactCatalog,
        readiness_evaluator: object,
    ) -> FinalizedExecution:
        """Run the sole post-module semantic sequence inside the Engine boundary."""
        from research_os.completion import ExecutionCompletionEvaluator
        from research_os.readiness import ResearchReadinessEvaluator

        if not isinstance(readiness_evaluator, ResearchReadinessEvaluator):
            raise TypeError("readiness_evaluator must be ResearchReadinessEvaluator")
        completion = ExecutionCompletionEvaluator().evaluate(
            plans,
            execution.module_results,
        )
        readiness = readiness_evaluator.evaluate(
            completion,
            execution.snapshot,
        )
        from research_os.runtime.core_artifacts import RESEARCH_READINESS

        readiness_store = ArtifactStore(catalog)
        readiness_store.write(
            cast(
                ArtifactWrite[object],
                ArtifactWrite(
                    key=RESEARCH_READINESS,
                    value=readiness,
                    producer_id="core:research-readiness",
                ),
            )
        )
        finalized_execution = TypedExecutionResult(
            snapshot=execution.snapshot.merged_with(readiness_store.freeze()),
            module_results=execution.module_results,
        )
        return FinalizedExecution(
            execution=finalized_execution,
            completion=completion,
            readiness=readiness,
        )

    def execute(
        self,
        plan: ModulePlan,
        context: ResearchContext,
        catalog: ArtifactCatalog,
        initial_snapshot: ArtifactSnapshot | None = None,
    ) -> TypedExecutionResult:
        """Execute a compiled Core API 2.0 plan through the sole module invoker."""
        if (
            initial_snapshot is not None
            and plan.initial_snapshot is not None
            and _snapshot_semantic_identity(initial_snapshot)
            != _snapshot_semantic_identity(plan.initial_snapshot)
        ):
            raise PipelineDefinitionError(
                "initial snapshot differs from the snapshot validated by the plan"
            )
        base_snapshot = initial_snapshot or plan.initial_snapshot or ArtifactStore(catalog).freeze()
        writes = ArtifactStore(catalog)
        module_results: list[ModuleResult] = []

        for module in plan.modules:
            result = self._invoke_module(
                module,
                context,
                ResearchStateView(base_snapshot.merged_with(writes.freeze())),
            )
            module_id = module.spec.module_id
            if result.module_id != module_id:
                raise PipelineDefinitionError(
                    f"module result identity mismatch: expected {module_id}, "
                    f"got {result.module_id}",
                    context={"module_id": module_id},
                )

            if result.status == "FAIL":
                raise ModuleExecutionError(
                    f"module {module_id} reported FAIL",
                    context={"module_id": module_id, "run_id": context.run_id},
                )

            declared = set(module.spec.provides)
            written: set[object] = set()
            for write in result.writes:
                if not isinstance(write, ArtifactWrite):
                    raise PipelineDefinitionError(
                        f"module {module_id} returned invalid artifact write type "
                        f"{type(write).__name__}",
                        context={"module_id": module_id},
                    )
                if write.key not in declared:
                    raise PipelineDefinitionError(
                        f"module {module_id} returned undeclared artifact write: "
                        f"{write.key.artifact_id}@{write.key.schema_version}",
                        context={"module_id": module_id},
                    )
                if write.producer_id != module_id:
                    raise PipelineDefinitionError(
                        f"module {module_id} artifact producer ID mismatch: "
                        f"got {write.producer_id}",
                        context={"module_id": module_id},
                    )
                if not isinstance(write.value, write.key.value_type):
                    raise PipelineDefinitionError(
                        f"module {module_id} artifact runtime value type mismatch for "
                        f"{write.key.artifact_id}: expected "
                        f"{write.key.value_type.__name__}, "
                        f"got {type(write.value).__name__}",
                        context={"module_id": module_id},
                    )
                if write.key in written:
                    raise PipelineDefinitionError(
                        f"module {module_id} returned duplicate artifact writes for "
                        f"{write.key.artifact_id}@{write.key.schema_version}",
                        context={"module_id": module_id},
                    )
                written.add(write.key)

            missing = declared - written
            if missing:
                missing_artifacts = ", ".join(
                    f"{key.artifact_id}@{key.schema_version}"
                    for key in sorted(missing, key=lambda key: key.identity)
                )
                raise PipelineDefinitionError(
                    f"module {module_id} returned missing declared artifact writes: "
                    f"{missing_artifacts}",
                    context={"module_id": module_id},
                )
            try:
                for write in result.writes:
                    writes.write(write)
            except ArtifactContractError as exc:
                raise PipelineDefinitionError(
                    f"module {module.spec.module_id} returned invalid artifact writes: {exc}",
                    context={"module_id": module.spec.module_id},
                ) from exc
            module_results.append(result)

        return TypedExecutionResult(
            snapshot=base_snapshot.merged_with(writes.freeze()),
            module_results=tuple(module_results),
        )

    @staticmethod
    def _invoke_module(
        module: ResearchModule,
        context: ResearchContext,
        state: ResearchStateView,
    ) -> ModuleResult:
        module_id = module.spec.module_id
        try:
            result = module.run(context, state)
        except Exception as exc:
            error_context = {"module_id": module_id}
            run_id = getattr(context, "run_id", None)
            if isinstance(run_id, str):
                error_context["run_id"] = run_id
            raise ModuleExecutionError(
                f"module {module_id} failed",
                context=error_context,
            ) from exc
        if not isinstance(result, ModuleResult):
            raise PipelineDefinitionError(
                f"module {module_id} returned invalid result type {type(result).__name__}",
                context={"module_id": module_id},
            )
        return result
