from pydantic import BaseModel, Field
class ModelFitnessInputs(BaseModel):
    data_quality: float=Field(ge=0,le=1)
    earnings_stability: float=Field(ge=0,le=1)
    cash_flow_visibility: float=Field(ge=0,le=1)
    capital_structure_fit: float=Field(ge=0,le=1)
    business_model_fit: float=Field(ge=0,le=1)
    forecast_stability: float=Field(ge=0,le=1)
def fitness_score(x:ModelFitnessInputs)->float:
    return x.data_quality*x.earnings_stability*x.cash_flow_visibility*x.capital_structure_fit*x.business_model_fit*x.forecast_stability
