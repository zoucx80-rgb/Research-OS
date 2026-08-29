from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Mapping, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from research_os.domain.evidence import Evidence


@runtime_checkable
class EvidenceView(Protocol):
    def as_of(self, decision_ts: datetime) -> list[Evidence]: ...
    def get(self, evidence_id: str) -> Evidence | None: ...


@runtime_checkable
class FactView(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...
    def evidence_ids(self, key: str) -> list[str]: ...
    def as_mapping(self) -> Mapping[str, Any]: ...


@runtime_checkable
class KnowledgeView(Protocol):
    def query(self, query: Any) -> list[Any]: ...


class CompanyRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    company_id: str
    security_id: str | None = None
    exchange: str | None = None
    display_name: str | None = None


class BaselineFingerprint(BaseModel):
    model_config = ConfigDict(frozen=True)

    repository_full_name: str
    repository_id: int
    branch: str
    commit_sha: str
    research_os_version: str
    core_api_version: str


class ResearchOptions(BaseModel):
    model_config = ConfigDict(frozen=True)


class LegacyEvidenceView:
    def __init__(self, evidence: list[Evidence] | tuple[Evidence, ...]):
        self._evidence = tuple(evidence)
        self._by_id = {item.evidence_id: item for item in self._evidence}

    def as_of(self, decision_ts: datetime) -> list[Evidence]:
        return sorted(
            (item for item in self._evidence if item.publish_ts <= decision_ts),
            key=lambda item: (item.publish_ts, item.revision_no, item.evidence_id),
        )

    def get(self, evidence_id: str) -> Evidence | None:
        return self._by_id.get(evidence_id)


class LegacyFactView:
    def __init__(
        self,
        *,
        values: Mapping[str, Any],
        evidence_by_fact: Mapping[str, list[str] | tuple[str, ...]],
    ):
        self._values = copy.deepcopy(dict(values))
        self._evidence_by_fact = {
            key: tuple(evidence_ids)
            for key, evidence_ids in evidence_by_fact.items()
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self._values.get(key, default)

    def evidence_ids(self, key: str) -> list[str]:
        return list(self._evidence_by_fact.get(key, ()))

    def as_mapping(self) -> Mapping[str, Any]:
        return copy.deepcopy(self._values)


class ResearchContext(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    run_id: str
    company: CompanyRef
    decision_ts: datetime
    baseline: BaselineFingerprint
    evidence: EvidenceView
    facts: FactView
    knowledge: KnowledgeView | None = None
    options: ResearchOptions
