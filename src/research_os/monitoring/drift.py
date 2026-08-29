from pydantic import BaseModel
class DriftAlert(BaseModel):
    max_score_delta: float
    changed_dimensions: list[str]
    requires_router_review: bool

def detect_business_model_drift(previous:dict[str,float],current:dict[str,float],threshold:float=.25)->DriftAlert:
    dims=set(previous)|set(current)
    deltas={k:abs(current.get(k,0)-previous.get(k,0)) for k in dims}
    max_delta=max(deltas.values(),default=0)
    return DriftAlert(max_score_delta=max_delta,changed_dimensions=sorted(k for k,v in deltas.items() if v>=threshold),requires_router_review=max_delta>=threshold)
