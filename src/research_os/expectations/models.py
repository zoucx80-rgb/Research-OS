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
    expectation_type: str="sell_side"
    source_count: int|None=None
    source_quality: float|None=Field(default=None,ge=0,le=1)


class ExpectationSnapshot(ConsensusVintage):
    decision_ts: datetime


class ExpectationEvidence(BaseModel):
    model_config=ConfigDict(frozen=True)
    expectation_source: str
    expectation_publish_ts: datetime
    expectation_period: str
    metric: str
    expected_value: float
    actual_value: float
    surprise: float
    vintage: str


class ExpectationService:
    def __init__(self): self._items=[]
    def add(self,vintage:ConsensusVintage): self._items.append(vintage); return vintage
    def snapshot(self,company_id:str,decision_ts:datetime,expectation_type:str="sell_side"):
        candidates=[v for v in self._items if v.company_id==company_id and v.as_of<=decision_ts and v.expectation_type==expectation_type]
        if not candidates: raise LookupError(f"no expectation available for {company_id} at {decision_ts}")
        v=max(candidates,key=lambda x:x.as_of)
        return ExpectationSnapshot(**v.model_dump(),decision_ts=decision_ts)
