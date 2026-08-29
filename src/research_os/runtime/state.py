from __future__ import annotations

import copy
from types import MappingProxyType
from typing import Any, Mapping


class ResearchStateView:
    def __init__(self, artifacts: dict[str, Any]):
        self._artifacts = artifacts

    def get(self, capability: str, default: Any = None) -> Any:
        if capability not in self._artifacts:
            return default
        return copy.deepcopy(self._artifacts[capability])

    def __contains__(self, capability: str) -> bool:
        return capability in self._artifacts

    def as_mapping(self) -> Mapping[str, Any]:
        return MappingProxyType(copy.deepcopy(self._artifacts))


class ResearchState:
    def __init__(self):
        self._artifacts: dict[str, Any] = {}
        self._module_results: dict[str, Any] = {}

    def view(self) -> ResearchStateView:
        return ResearchStateView(self._artifacts)

    def get(self, capability: str, default: Any = None) -> Any:
        return self.view().get(capability, default)

    @property
    def artifacts(self) -> Mapping[str, Any]:
        return MappingProxyType(copy.deepcopy(self._artifacts))

    @property
    def module_results(self) -> Mapping[str, Any]:
        return MappingProxyType(dict(self._module_results))

    def _record(self, result: Any) -> None:
        self._module_results[result.module_id] = result
        for capability, value in result.artifacts.items():
            self._artifacts[capability] = copy.deepcopy(value)
