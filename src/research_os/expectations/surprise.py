from pydantic import BaseModel

class SurpriseResult(BaseModel):
    period: str
    net_profit_surprise: float|None=None
    cfo_surprise: float|None=None
    inventory_surprise: float|None=None
    label: str

def _diff(actual,expected,key):
    a=actual.get(key); e=expected.get(key)
    return None if a is None or e is None else a-e

def decompose_surprise(actual:dict,expected:dict,period:str)->SurpriseResult:
    np=_diff(actual,expected,"net_profit"); cfo=_diff(actual,expected,"cfo"); inv=_diff(actual,expected,"inventory")
    if np is not None and np>0 and cfo is not None and cfo<0: label="HEADLINE_BEAT_QUALITY_MISS"
    elif np is not None and np>0: label="HEADLINE_BEAT"
    elif np is not None and np<0: label="HEADLINE_MISS"
    else: label="MIXED"
    return SurpriseResult(period=period,net_profit_surprise=np,cfo_surprise=cfo,inventory_surprise=inv,label=label)
