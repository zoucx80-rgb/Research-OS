from __future__ import annotations

import heapq
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable

from research_os.contracts.artifacts import (
    ArtifactCatalog,
    ArtifactKey,
    ArtifactMode,
    ArtifactSnapshot,
)
from research_os.contracts.errors import ArtifactContractError, PlanCompilationError
from research_os.runtime.modules import ResearchModule


class ModulePlanCompilationError(PlanCompilationError):
    """Raised when typed module dependencies cannot form an executable plan."""


class ModulePlanDependencyMissingError(ModulePlanCompilationError):
    code = "PLAN_DEPENDENCY_MISSING"


class ModulePlanDependencyCycleError(ModulePlanCompilationError):
    code = "PLAN_DEPENDENCY_CYCLE"


@dataclass(frozen=True, slots=True)
class ModulePlan:
    """An immutable, deterministically ordered typed module execution plan."""

    modules: tuple[ResearchModule, ...]
    initial_snapshot: ArtifactSnapshot | None = None

    @property
    def module_ids(self) -> tuple[str, ...]:
        return tuple(module.spec.module_id for module in self.modules)


class ModulePlanCompiler:
    """Compiles Core API 2.0 typed artifact dependencies into a ModulePlan."""

    def __init__(self, catalog: ArtifactCatalog) -> None:
        self._catalog = catalog

    def compile(
        self,
        modules: Iterable[ResearchModule],
        *,
        initial_snapshot: ArtifactSnapshot | None = None,
    ) -> ModulePlan:
        modules_by_id: dict[str, ResearchModule] = {}
        providers: dict[ArtifactKey[Any], list[str]] = defaultdict(list)

        for module in modules:
            spec = module.spec
            module_id = spec.module_id
            if module_id in modules_by_id:
                raise ModulePlanCompilationError(
                    f"duplicate module_id: {module_id}",
                    context={"module_id": module_id},
                )
            modules_by_id[module_id] = module
            for key in spec.provides:
                self._definition_for(key)
                if self._provided_by_initial_snapshot(initial_snapshot, key):
                    raise ModulePlanCompilationError(
                        f"initial snapshot already provides artifact "
                        f"{key.artifact_id}@{key.schema_version}; module {module_id} "
                        "cannot provide it again",
                        context={
                            "module_id": module_id,
                            "artifact_id": key.artifact_id,
                            "schema_version": key.schema_version,
                        },
                    )
                providers[key].append(module_id)

        for key, provider_ids in providers.items():
            definition = self._definition_for(key)
            if definition.mode is ArtifactMode.EXCLUSIVE and len(provider_ids) > 1:
                raise ModulePlanCompilationError(
                    f"exclusive artifact {key.artifact_id} has multiple providers: "
                    f"{', '.join(sorted(provider_ids))}",
                    context={
                        "artifact_id": key.artifact_id,
                        "schema_version": key.schema_version,
                        "module_ids": ",".join(sorted(provider_ids)),
                    },
                )
            if definition.mode is ArtifactMode.COLLECTION:
                try:
                    self._catalog.reducer(key)
                except ArtifactContractError as exc:
                    raise ModulePlanCompilationError(
                        f"collection artifact {key.artifact_id} requires a reducer",
                        context={
                            "artifact_id": key.artifact_id,
                            "schema_version": key.schema_version,
                        },
                    ) from exc

        dependencies: dict[str, set[str]] = {
            module_id: set() for module_id in modules_by_id
        }
        dependents: dict[str, set[str]] = defaultdict(set)
        for module_id, module in modules_by_id.items():
            for key in module.spec.requires:
                self._definition_for(key)
                provider_ids = providers.get(key, [])
                if provider_ids:
                    for provider_id in provider_ids:
                        dependencies[module_id].add(provider_id)
                        dependents[provider_id].add(module_id)
                elif not self._provided_by_initial_snapshot(initial_snapshot, key):
                    raise ModulePlanDependencyMissingError(
                        f"module {module_id} requires missing artifact "
                        f"{key.artifact_id}@{key.schema_version}",
                        context={
                            "module_id": module_id,
                            "artifact_id": key.artifact_id,
                            "schema_version": key.schema_version,
                        },
                    )

        ordered_ids = self._topological_order(dependencies, dependents)
        return ModulePlan(
            modules=tuple(modules_by_id[module_id] for module_id in ordered_ids),
            initial_snapshot=initial_snapshot,
        )

    def _definition_for(self, key: ArtifactKey[Any]) -> Any:
        try:
            return self._catalog.definition(key)
        except ArtifactContractError as exc:
            raise ModulePlanCompilationError(
                f"artifact {key.artifact_id}@{key.schema_version} is not registered",
                context={
                    "artifact_id": key.artifact_id,
                    "schema_version": key.schema_version,
                },
            ) from exc

    @staticmethod
    def _provided_by_initial_snapshot(
        initial_snapshot: ArtifactSnapshot | None, key: ArtifactKey[Any]
    ) -> bool:
        if initial_snapshot is None:
            return False
        try:
            return initial_snapshot.envelope(key) is not None
        except ArtifactContractError as exc:
            raise ModulePlanCompilationError(
                f"initial snapshot artifact {key.artifact_id}@{key.schema_version} "
                "does not match the catalog",
                context={
                    "artifact_id": key.artifact_id,
                    "schema_version": key.schema_version,
                },
            ) from exc

    @staticmethod
    def _topological_order(
        dependencies: dict[str, set[str]], dependents: dict[str, set[str]]
    ) -> list[str]:
        indegree = {
            module_id: len(required) for module_id, required in dependencies.items()
        }
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

        if len(ordered_ids) != len(dependencies):
            unresolved = sorted(
                module_id for module_id, degree in indegree.items() if degree > 0
            )
            raise ModulePlanDependencyCycleError(
                f"dependency cycle detected among modules: {', '.join(unresolved)}",
                context={"module_ids": ",".join(unresolved)},
            )
        return ordered_ids
