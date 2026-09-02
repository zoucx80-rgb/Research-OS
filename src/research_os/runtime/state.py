from __future__ import annotations

from typing import TypeVar

from research_os.contracts.artifacts import ArtifactKey, ArtifactSnapshot


T = TypeVar("T")


class ResearchStateView:
    def __init__(self, snapshot: ArtifactSnapshot):
        self._snapshot = snapshot

    def get(self, key: ArtifactKey[T]) -> T | None:
        if not isinstance(key, ArtifactKey):
            raise TypeError("typed state requires an ArtifactKey")
        return self._snapshot.get(key)

    def require(self, key: ArtifactKey[T]) -> T:
        if not isinstance(key, ArtifactKey):
            raise TypeError("typed state requires an ArtifactKey")
        return self._snapshot.require(key)
