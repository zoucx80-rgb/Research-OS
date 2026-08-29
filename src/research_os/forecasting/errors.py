from typing import Literal
from pydantic import BaseModel
Attribution=Literal["demand_error","price_error","margin_error","working_capital_error","financing_cost_error","model_structural_error","data_revision_error"]
class ForecastErrorRecord(BaseModel):
    metric: str
    predicted: float
    actual: float
    period: str
    attribution: Attribution
    error: float
    absolute_error: float

def close_forecast(*,metric,predicted,actual,period,attribution)->ForecastErrorRecord:
    e=actual-predicted
    return ForecastErrorRecord(metric=metric,predicted=predicted,actual=actual,period=period,attribution=attribution,error=e,absolute_error=abs(e))
