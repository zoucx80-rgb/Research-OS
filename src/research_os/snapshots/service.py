import copy, hashlib, json
from datetime import datetime
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field
from research_os.domain.versions import VersionBundle

class SnapshotFrozenError(RuntimeError): pass

def _hash_payload(payload:dict[str,Any])->str:
    raw=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str).encode()
    return hashlib.sha256(raw).hexdigest()

class ResearchSnapshot(BaseModel):
    model_config=ConfigDict(frozen=True)
    snapshot_id: str
    company_id: str
    decision_ts: datetime
    versions: VersionBundle
    payload: dict[str,Any]=Field(default_factory=dict)
    payload_hash: str

class SnapshotService:
    def __init__(self): self._snapshots={}
    def freeze(self,company_id,decision_ts,versions,payload=None):
        frozen_payload=copy.deepcopy(payload or {})
        snap=ResearchSnapshot(snapshot_id=str(uuid4()),company_id=company_id,decision_ts=decision_ts,
                              versions=VersionBundle.model_validate(versions),payload=frozen_payload,payload_hash=_hash_payload(frozen_payload))
        self._snapshots[snap.snapshot_id]=snap
        return snap
    def replace_versions(self,snapshot_id,versions):
        if snapshot_id in self._snapshots: raise SnapshotFrozenError(snapshot_id)
        raise KeyError(snapshot_id)
    def verify(self,snapshot_id:str)->bool:
        snap=self._snapshots[snapshot_id]
        return _hash_payload(snap.payload)==snap.payload_hash
