from pydantic import BaseModel, Field

class BusinessModelProfile(BaseModel):
    company_id: str
    primary_model: str
    secondary_models: list[str]=Field(default_factory=list)
    confidence: float=Field(ge=0,le=1)
    evidence_ids: list[str]=Field(default_factory=list)
    router_version: str="router@1.0.0"
    manual_override: bool=False
