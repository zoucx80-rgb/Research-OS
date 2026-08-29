from __future__ import annotations

import heapq
from collections import defaultdict

from research_os.runtime.context import ResearchContext
from research_os.runtime.modules import ModuleResult, ResearchModule
from research_os.runtime.state import ResearchState


class PipelineDefinitionError(ValueError):
    pass


class ModuleExecutionError(RuntimeError):
    pass


class ResearchEngine:
    def __init__(self, modules: list[ResearchModule]):
        self._modules = tuple(modules)

    def _ordered_modules(self) -> list[ResearchModule]:
        modules_by_id: dict[str, ResearchModule] = {}
        providers: dict[str, str] = {}

        for module in self._modules:
            module_id = module.spec.module_id
            if module_id in modules_by_id:
                raise PipelineDefinitionError(f"duplicate module_id: {module_id}")
            modules_by_id[module_id] = module
            for capability in module.spec.provides:
                existing = providers.get(capability)
                if existing is not None:
                    raise PipelineDefinitionError(
                        f"duplicate provider for capability {capability}: {existing}, {module_id}"
                    )
                providers[capability] = module_id

        dependencies: dict[str, set[str]] = {module_id: set() for module_id in modules_by_id}
        dependents: dict[str, set[str]] = defaultdict(set)
        for module_id, module in modules_by_id.items():
            for capability in module.spec.requires:
                provider = providers.get(capability)
                if provider is None:
                    raise PipelineDefinitionError(
                        f"module {module_id} requires missing capability {capability}"
                    )
                dependencies[module_id].add(provider)
                dependents[provider].add(module_id)

        indegree = {module_id: len(required) for module_id, required in dependencies.items()}
        ready = [module_id for module_id, degree in indegree.items() if degree == 0]
        heapq.heapify(ready)
        ordered_ids: list[str] = []

        while ready:
            module_id = heapq.heappop(ready)
            ordered_ids.append(module_id)
            for dependent in sorted(dependents.get(module_id, ())):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    heapq.heappush(ready, dependent)

        if len(ordered_ids) != len(modules_by_id):
            unresolved = sorted(module_id for module_id, degree in indegree.items() if degree > 0)
            raise PipelineDefinitionError(
                f"dependency cycle detected among modules: {', '.join(unresolved)}"
            )

        return [modules_by_id[module_id] for module_id in ordered_ids]

    def run(self, context: ResearchContext) -> ResearchState:
        ordered = self._ordered_modules()
        state = ResearchState()

        for module in ordered:
            module_id = module.spec.module_id
            try:
                result = module.run(context, state.view())
            except Exception as exc:
                raise ModuleExecutionError(f"module {module_id} failed") from exc

            if not isinstance(result, ModuleResult):
                raise PipelineDefinitionError(
                    f"module {module_id} returned invalid result type {type(result).__name__}"
                )
            if result.module_id != module_id:
                raise PipelineDefinitionError(
                    f"module result identity mismatch: expected {module_id}, got {result.module_id}"
                )

            undeclared = set(result.artifacts) - set(module.spec.provides)
            if undeclared:
                raise PipelineDefinitionError(
                    f"module {module_id} returned undeclared artifacts: {', '.join(sorted(undeclared))}"
                )

            overwritten = set(result.artifacts) & set(state.artifacts)
            if overwritten:
                raise PipelineDefinitionError(
                    f"module {module_id} attempted artifact overwrite: {', '.join(sorted(overwritten))}"
                )

            state._record(result)

        return state
