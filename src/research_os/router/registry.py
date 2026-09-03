from datetime import date, datetime, timezone
from pydantic import BaseModel


class RouterOverride(BaseModel):
    company_id: str
    old_model: str | None = None
    new_model: str
    reason: str
    effective_at: date
    created_at: datetime
    actor: str = "system"
    router_version: str = "router@1.0.0"
    manual_override: bool = True


class RouterOverrideRegistry:
    def __init__(self):
        self._items: dict[str, list[RouterOverride]] = {}

    def set_override(self, company_id, new_model, reason, effective_at, actor="system"):
        hist = self._items.setdefault(company_id, [])
        old = hist[-1].new_model if hist else None
        item = RouterOverride(
            company_id=company_id,
            old_model=old,
            new_model=new_model,
            reason=reason,
            effective_at=effective_at,
            created_at=datetime.now(timezone.utc),
            actor=actor,
        )
        hist.append(item)
        return item

    def history(self, company_id):
        return list(self._items.get(company_id, []))

    def resolve(self, company_id, default_model):
        hist = self._items.get(company_id, [])
        return hist[-1].new_model if hist else default_model
