from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from research_os.knowledge.models import KnowledgeItem, KnowledgeQuery


@runtime_checkable
class KnowledgeProvider(Protocol):
    def query(self, query: KnowledgeQuery) -> list[KnowledgeItem]: ...


class NullKnowledgeProvider:
    def query(self, query: KnowledgeQuery) -> list[KnowledgeItem]:
        return []


class InMemoryKnowledgeProvider:
    def __init__(self, items: list[KnowledgeItem] | tuple[KnowledgeItem, ...] = ()):
        self._items = tuple(items)

    @staticmethod
    def _sort_key(item: KnowledgeItem):
        return (item.publish_ts or datetime.min.replace(tzinfo=timezone.utc), item.knowledge_id)

    def query(self, query: KnowledgeQuery) -> list[KnowledgeItem]:
        visible = [
            item
            for item in self._items
            if item.publish_ts is None or item.publish_ts <= query.as_of
        ]
        return sorted(visible, key=self._sort_key)
