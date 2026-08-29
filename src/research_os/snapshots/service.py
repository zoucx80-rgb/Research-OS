from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, ConfigDict
from research_os.domain.versions import VersionBundle

class SnapshotFrozenError(RuntimeError): pass

class ResearchSnapshot(BaseModel):
    model_config=ConfigDict(frozen=True)
    snapshot_id: str
    company_id: str
    decision_ts: datetime
    versions: VersionBundle

class SnapshotService:
    def __init__(self): self._snapshots={}
    def freeze(self,company_id,decision_ts,versions):
        snap=ResearchSnapshot(snapshot_id=str(uuid4()),company_id=company_id,decision_ts=decision_ts,
                              versions=VersionBundle.model_validate(versions))
        self._snapshots[snap.snapshot_id]=snap
        return snap
    def replace_versions(self,snapshot_id,versions):
        if snapshot_id in self._snapshots: raise SnapshotFrozenError(snapshot_id)
        raise KeyError(snapshot_id)
