from pydantic import BaseModel, Field
class ProbabilityForecast(BaseModel):
    probability: float=Field(ge=0,le=1)
    outcome: int|None=None
class CalibrationRecord(BaseModel):
    probability: float
    outcome: int
    brier: float

def brier_score(probability:float,outcome:int)->float:
    if not 0<=probability<=1: raise ValueError("probability must be within [0,1]")
    if outcome not in (0,1): raise ValueError("outcome must be binary")
    return (probability-outcome)**2
