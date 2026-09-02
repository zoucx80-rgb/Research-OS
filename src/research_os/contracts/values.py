from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict

from research_os.period.models import ReportingPeriod


class AccountingScope(BaseModel):
    model_config = ConfigDict(frozen=True)

    accounting_standard: str | None = None
    consolidation: Literal["consolidated", "standalone", "unknown"] = "unknown"
    segment: str | None = None
    geography: str | None = None
    continuing_operations: bool | None = None

    @classmethod
    def from_facts(cls, facts: Mapping[str, Any]) -> AccountingScope:
        raw = facts.get("accounting_scope")
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, Mapping):
            return cls.model_validate(dict(raw))
        return cls(
            accounting_standard=facts.get("accounting_standard"),
            consolidation=facts.get("consolidation") or "unknown",
            segment=facts.get("segment"),
            geography=facts.get("geography"),
            continuing_operations=facts.get("continuing_operations"),
        )


__all__ = ["AccountingScope", "ReportingPeriod"]
