"""Shared lineage helpers for professional Phase-B modules."""

from __future__ import annotations

from pydantic import BaseModel
from research_os.contracts.evidence import EvidenceRef
from research_os.runtime.context import ResearchContext
from typing import Iterable


def _lineage_refs(*values: object) -> tuple[EvidenceRef, ...]:
    """Collect revision-bound evidence references from frozen typed inputs."""

    by_identity: dict[tuple[str, int, str], EvidenceRef] = {}

    def visit(value: object) -> None:
        if isinstance(value, EvidenceRef):
            by_identity[(value.evidence_id, value.revision, value.content_fingerprint)] = value
            return
        if isinstance(value, BaseModel):
            if "evidence_refs" in type(value).model_fields:
                for reference in getattr(value, "evidence_refs", ()):
                    visit(reference)
            for field_name in type(value).model_fields:
                if field_name in {"evidence_refs", "assumption_refs"}:
                    continue
                visit(getattr(value, field_name))
            return
        if isinstance(value, dict):
            for item in value.values():
                visit(item)
            return
        if isinstance(value, (tuple, list, set, frozenset)):
            for item in value:
                visit(item)

    for value in values:
        visit(value)
    return tuple(by_identity[key] for key in sorted(by_identity))


def _fact_refs(context: ResearchContext, fact_ids: Iterable[str]) -> tuple[EvidenceRef, ...]:
    return _lineage_refs(*(context.facts.evidence_refs(fact_id) for fact_id in fact_ids))
