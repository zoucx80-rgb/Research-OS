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


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return copy.deepcopy(value)


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
    def freeze(
        self,
        company_id,
        decision_ts,
        versions,
        payload=None,
        *,
        component_fingerprints=None,
        strategy_resolution=None,
    ):
        frozen_payload=copy.deepcopy(payload or {})
        if component_fingerprints is not None:
            frozen_payload["component_fingerprints"]=_jsonable(component_fingerprints)
        if strategy_resolution is not None:
            frozen_payload["strategy_resolution"]=_jsonable(strategy_resolution)
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
