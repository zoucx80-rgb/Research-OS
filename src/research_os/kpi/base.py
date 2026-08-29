from typing import Mapping, Protocol
from pydantic import BaseModel, Field
from research_os.router.models import BusinessModelProfile

class MetricResult(BaseModel):
    metric_id: str
    value: float | None
    unit: str | None=None
    status: str="valid"
    formula_version: str
    evidence_ids: list[str]=Field(default_factory=list)

class KpiPack(Protocol):
    pack_id: str
    pack_version: str
    def calculate(self,facts: Mapping[str,float|None])->list[MetricResult]: ...

class CorePack:
    pack_id="core"; pack_version="core@1.0.0"
    def calculate(self,facts): return []

class KpiPackRegistry:
    def __init__(self,packs): self.packs={p.pack_id:p for p in packs}
    @classmethod
    def default(cls):
        from .manufacturing import ManufacturingPack
        from .distributor import DistributorPack
        return cls([CorePack(),ManufacturingPack(),DistributorPack()])
    def resolve(self,profile: BusinessModelProfile):
        ids=["core"]
        mapping={"manufacturer":"manufacturing","manufacturing":"manufacturing","distributor":"distributor"}
        for model in [profile.primary_model,*profile.secondary_models]:
            pid=mapping.get(model,model)
            if pid in self.packs and pid not in ids: ids.append(pid)
        return [self.packs[x] for x in ids]
