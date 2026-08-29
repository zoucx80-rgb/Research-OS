from pydantic import BaseModel, Field
from typing import Literal

Relation=Literal["positive","negative","nonlinear","conditional"]

class DriverNode(BaseModel):
    driver_id: str
    name: str
    driver_type: str
    observable_metric: str | None=None
    direction: str | None=None
    lag_quarters: int=Field(default=0,ge=0)
    confidence_grade: str="D"
    evidence_ids: list[str]=Field(default_factory=list)
    critical: bool=False

class DriverEdge(BaseModel):
    from_driver: str
    to_driver: str
    relation: Relation
    lag_quarters: int=Field(default=0,ge=0)
    evidence_strength: float|None=Field(default=None,ge=0,le=1)
    statistical_support: str|None=None
    mechanism_description: str|None=None

class DriverGraphResult(BaseModel):
    company_id: str
    nodes: list[DriverNode]
    edges: list[DriverEdge]
