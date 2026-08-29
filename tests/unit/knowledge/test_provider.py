from datetime import datetime, timezone

from research_os.knowledge.models import KnowledgeItem, KnowledgeQuery
from research_os.knowledge.provider import InMemoryKnowledgeProvider, NullKnowledgeProvider


DECISION_TS = datetime(2026, 8, 29, tzinfo=timezone.utc)


def test_in_memory_knowledge_provider_filters_future_items_and_orders_deterministically():
    provider = InMemoryKnowledgeProvider([
        KnowledgeItem(
            knowledge_id="future",
            content={"definition": "future"},
            source_id="source:future",
            publish_ts=datetime(2027, 1, 1, tzinfo=timezone.utc),
            version="1",
            evidence_ids=["ev:future"],
        ),
        KnowledgeItem(
            knowledge_id="undated",
            content={"definition": "advisory"},
            source_id="source:undated",
            publish_ts=None,
            version="1",
            evidence_ids=[],
        ),
        KnowledgeItem(
            knowledge_id="old",
            content={"definition": "known"},
            source_id="source:old",
            publish_ts=datetime(2026, 1, 1, tzinfo=timezone.utc),
            version="1",
            evidence_ids=["ev:old"],
        ),
    ])
    result = provider.query(KnowledgeQuery(topic="definition", as_of=DECISION_TS))
    assert [item.knowledge_id for item in result] == ["undated", "old"]


def test_null_knowledge_provider_is_deterministic():
    provider = NullKnowledgeProvider()
    query = KnowledgeQuery(topic="anything", as_of=DECISION_TS)
    assert provider.query(query) == []
    assert provider.query(query) == []


def test_knowledge_query_uses_isolated_tag_sets():
    first = KnowledgeQuery(topic="a", as_of=DECISION_TS)
    second = KnowledgeQuery(topic="b", as_of=DECISION_TS)
    assert first.tags == set()
    assert second.tags == set()
