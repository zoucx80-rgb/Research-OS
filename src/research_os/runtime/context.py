from __future__ import annotations

import copy
from datetime import datetime
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, model_validator

from research_os.contracts.evidence import EvidenceRef, evidence_content_fingerprint
from research_os.contracts.values import AccountingScope
from research_os.domain.evidence import Evidence
from research_os.period.models import ReportingPeriod


@runtime_checkable
class EvidenceSource(Protocol):
    def as_of(self, company_id: str, decision_ts: datetime) -> list[Evidence]: ...


@runtime_checkable
class KnowledgeView(Protocol):
    def query(self, query: Any) -> list[Any]: ...


class EvidenceView:
    """Immutable evidence fixed to one company and decision-time cutoff."""

    __slots__ = ("company_id", "decision_ts", "_by_ref", "_refs")
    company_id: str
    decision_ts: datetime
    _by_ref: dict[EvidenceRef, Evidence]
    _refs: tuple[EvidenceRef, ...]

    def __init__(
        self,
        evidence: EvidenceSource | Iterable[Evidence],
        *,
        company_id: str,
        decision_ts: datetime,
    ) -> None:
        rows = (
            evidence.as_of(company_id, decision_ts)
            if isinstance(evidence, EvidenceSource)
            else evidence
        )
        copied = tuple(item.model_copy(deep=True) for item in rows)
        foreign = sorted({item.company_id for item in copied if item.company_id != company_id})
        if foreign:
            raise ValueError(
                f"cross-company evidence is not allowed for {company_id}: {', '.join(foreign)}"
            )

        selected: dict[str, Evidence] = {}
        fingerprints: dict[tuple[str, int], str] = {}
        for item in copied:
            if item.publish_ts > decision_ts:
                continue
            revision_key = item.evidence_id, item.revision_no
            fingerprint = evidence_content_fingerprint(item)
            existing = fingerprints.get(revision_key)
            if existing is not None and existing != fingerprint:
                raise ValueError(
                    f"conflicting evidence revision: {item.evidence_id}@{item.revision_no}"
                )
            fingerprints[revision_key] = fingerprint
            current = selected.get(item.evidence_id)
            if current is None or (item.publish_ts, item.revision_no) > (
                current.publish_ts,
                current.revision_no,
            ):
                selected[item.evidence_id] = item

        ordered = tuple(
            sorted(
                selected.values(),
                key=lambda item: (item.publish_ts, item.revision_no, item.evidence_id),
            )
        )
        refs = tuple(
            EvidenceRef(
                evidence_id=item.evidence_id,
                revision=item.revision_no,
                content_fingerprint=evidence_content_fingerprint(item),
            )
            for item in ordered
        )
        object.__setattr__(self, "company_id", company_id)
        object.__setattr__(self, "decision_ts", decision_ts)
        object.__setattr__(self, "_refs", refs)
        object.__setattr__(
            self,
            "_by_ref",
            {reference: item for reference, item in zip(refs, ordered, strict=True)},
        )

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("EvidenceView is immutable")

    def __deepcopy__(self, memo: dict[int, object]) -> EvidenceView:
        return self

    def get(self, reference: EvidenceRef) -> Evidence | None:
        if not isinstance(reference, EvidenceRef):
            raise TypeError("EvidenceView.get requires an EvidenceRef")
        item = self._by_ref.get(reference)
        return None if item is None else item.model_copy(deep=True)

    def refs(self) -> tuple[EvidenceRef, ...]:
        return self._refs


class FactView:
    """Immutable provider-facing facts and their revision-bound evidence lineage."""

    __slots__ = (
        "company_id",
        "decision_ts",
        "reporting_period",
        "accounting_scope",
        "_values",
        "_evidence_refs_by_fact",
    )
    company_id: str
    decision_ts: datetime
    reporting_period: ReportingPeriod
    accounting_scope: AccountingScope
    _values: dict[str, Any]
    _evidence_refs_by_fact: dict[str, tuple[EvidenceRef, ...]]

    def __init__(
        self,
        *,
        company_id: str,
        decision_ts: datetime,
        values: Mapping[str, Any],
        evidence_refs_by_fact: Mapping[str, tuple[EvidenceRef, ...]],
        reporting_period: ReportingPeriod,
        accounting_scope: AccountingScope,
    ) -> None:
        copied_values = copy.deepcopy(dict(values))
        copied_refs: dict[str, tuple[EvidenceRef, ...]] = {}
        for fact_id, references in evidence_refs_by_fact.items():
            if fact_id not in copied_values:
                raise ValueError(f"evidence references provided for unknown fact: {fact_id}")
            if not isinstance(references, tuple) or any(
                not isinstance(reference, EvidenceRef) for reference in references
            ):
                raise TypeError("fact evidence references must be EvidenceRef tuples")
            by_evidence_id: dict[str, EvidenceRef] = {}
            for reference in references:
                current = by_evidence_id.get(reference.evidence_id)
                if current is not None and current != reference:
                    raise ValueError(
                        "fact lineage has conflicting revisions or content for "
                        f"{reference.evidence_id}"
                    )
                by_evidence_id[reference.evidence_id] = reference
            copied_refs[fact_id] = tuple(
                reference.model_copy(deep=True)
                for reference in sorted(
                    by_evidence_id.values(),
                    key=lambda item: (
                        item.evidence_id,
                        item.revision,
                        item.content_fingerprint,
                    ),
                )
            )

        missing_lineage = sorted(
            fact_id
            for fact_id, value in copied_values.items()
            if value is not None and not copied_refs.get(fact_id)
        )
        if missing_lineage:
            raise ValueError(
                "fact values are missing evidence references: " + ", ".join(missing_lineage)
            )
        if not isinstance(reporting_period, ReportingPeriod):
            raise TypeError("reporting_period must be an explicit ReportingPeriod")
        if not isinstance(accounting_scope, AccountingScope):
            raise TypeError("accounting_scope must be an explicit AccountingScope")

        object.__setattr__(self, "company_id", company_id)
        object.__setattr__(self, "decision_ts", decision_ts)
        object.__setattr__(
            self,
            "reporting_period",
            reporting_period.model_copy(deep=True),
        )
        object.__setattr__(
            self,
            "accounting_scope",
            accounting_scope.model_copy(deep=True),
        )
        object.__setattr__(self, "_values", copied_values)
        object.__setattr__(self, "_evidence_refs_by_fact", copied_refs)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("FactView is immutable")

    def __deepcopy__(self, memo: dict[int, object]) -> FactView:
        return self

    def get(self, fact_id: str, default: Any = None) -> Any:
        return copy.deepcopy(self._values.get(fact_id, default))

    def evidence_refs(self, fact_id: str) -> tuple[EvidenceRef, ...]:
        return tuple(
            reference.model_copy(deep=True)
            for reference in self._evidence_refs_by_fact.get(fact_id, ())
        )

    def as_mapping(self) -> Mapping[str, Any]:
        return MappingProxyType(copy.deepcopy(self._values))


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


class ResearchContext(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    run_id: str
    company: CompanyRef
    decision_ts: datetime
    baseline: BaselineFingerprint
    evidence: EvidenceView
    facts: FactView
    knowledge: KnowledgeView | None = None

    @model_validator(mode="after")
    def _validate_bound_views(self) -> ResearchContext:
        if self.evidence.company_id != self.company.company_id:
            raise ValueError("evidence view company does not match research context")
        if self.facts.company_id != self.company.company_id:
            raise ValueError("fact view company does not match research context")
        if self.evidence.decision_ts != self.decision_ts:
            raise ValueError("evidence view cutoff does not match research context")
        if self.facts.decision_ts != self.decision_ts:
            raise ValueError("fact view cutoff does not match research context")
        for fact_id in self.facts.as_mapping():
            fact_value = self.facts.get(fact_id)
            resolved = []
            for reference in self.facts.evidence_refs(fact_id):
                evidence = self.evidence.get(reference)
                if evidence is None:
                    raise ValueError(
                        f"fact evidence reference does not resolve: {fact_id} -> "
                        f"{reference.evidence_id}@{reference.revision}"
                    )
                resolved.append(evidence)
            if resolved and not any(
                item.value == fact_value or item.normalized_value == fact_value for item in resolved
            ):
                raise ValueError(f"evidence does not support fact value: {fact_id}")
        return self
