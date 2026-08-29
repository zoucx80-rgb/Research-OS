from pydantic import BaseModel
class PeerNormalizationError(ValueError): pass
class ComparableMetric(BaseModel):
    value: float|None
    period_type: str
    scope: str
    accounting_definition: str
    frequency: str
    share_count_convention: str
    business_model_interpretation: str

def normalize_peer_metric(left:ComparableMetric,right:ComparableMetric):
    fields=["period_type","scope","accounting_definition","frequency","share_count_convention","business_model_interpretation"]
    mismatches=[f for f in fields if getattr(left,f)!=getattr(right,f)]
    if mismatches: raise PeerNormalizationError("incompatible peer metrics: "+",".join(mismatches))
    return left,right
