from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ConsensusVintage(BaseModel):
    model_config=ConfigDict(frozen=True)
    company_id: str
    as_of: datetime
    forecast_period: str
    revenue: float|None=None
    net_profit: float|None=None
    eps: float|None=None
    gross_margin: float|None=None
    source_count: int|None=None
    source_quality: float|None=Field(default=None,ge=0,le=1)

class ExpectationSnapshot(ConsensusVintage):
    decision_ts: datetime

class ExpectationService:
    def __init__(self): self._items=[]
    def add(self,vintage:ConsensusVintage): self._items.append(vintage); return vintage
    def snapshot(self,company_id:str,decision_ts:datetime):
        candidates=[v for v in self._items if v.company_id==company_id and v.as_of<=decision_ts]
        if not candidates: raise LookupError(f"no expectation available for {company_id} at {decision_ts}")
        v=max(candidates,key=lambda x:x.as_of)
        return ExpectationSnapshot(**v.model_dump(),decision_ts=decision_ts)
