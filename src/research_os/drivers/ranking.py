from pydantic import BaseModel, Field

class ScoredDriver(BaseModel):
    driver_id: str
    materiality: float=Field(ge=0,le=1)
    uncertainty: float=Field(ge=0,le=1)
    observability: float=Field(ge=0,le=1)
    decision_relevance: float=Field(ge=0,le=1)

class RankedDriver(BaseModel):
    driver_id: str
    score: float

def rank_drivers(drivers:list[ScoredDriver])->list[RankedDriver]:
    out=[RankedDriver(driver_id=d.driver_id,score=d.materiality*d.uncertainty*d.observability*d.decision_relevance) for d in drivers]
    return sorted(out,key=lambda x:x.score,reverse=True)
