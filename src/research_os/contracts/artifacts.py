from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass, fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum, StrEnum
from types import MappingProxyType
from typing import Callable, Generic, Mapping, TypeVar, cast

from pydantic import BaseModel

from research_os.contracts.evidence import EvidenceRef
from research_os.contracts.errors import (
    ArtifactDefinitionError,
    ArtifactNotFoundError,
    ArtifactProviderConflictError,
    ArtifactTypeMismatchError,
)


T = TypeVar("T")
ArtifactIdentity = tuple[str, str]
ArtifactReducer = Callable[[tuple[object, ...]], object]


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_artifact_value(value: object) -> object:
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, Enum):
        return {
            "type": "enum",
            "value": _canonical_artifact_value(value.value),
        }
    if isinstance(value, str):
        return {"type": "string", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": value}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ArtifactTypeMismatchError(
                "canonical artifact value requires finite floating-point values"
            )
        return {"type": "float", "value": 0.0 if value == 0 else value}
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ArtifactTypeMismatchError(
                "canonical artifact value requires finite Decimal values"
            )
        return {"type": "decimal", "value": str(value)}
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ArtifactTypeMismatchError(
                "canonical artifact value requires timezone-aware datetimes"
            )
        utc_value = value.astimezone(timezone.utc)
        return {
            "type": "datetime",
            "value": utc_value.isoformat(timespec="microseconds").replace(
                "+00:00", "Z"
            ),
        }
    if isinstance(value, date):
        return {"type": "date", "value": value.isoformat()}
    if isinstance(value, BaseModel):
        return {
            "type": "model",
            "value": _canonical_artifact_value(
                value.model_dump(mode="python", round_trip=True)
            ),
        }
    if is_dataclass(value) and not isinstance(value, type):
        return {
            "type": "dataclass",
            "value": _canonical_artifact_value(
                {field.name: getattr(value, field.name) for field in fields(value)}
            ),
        }
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ArtifactTypeMismatchError(
                "canonical artifact value requires string mapping keys"
            )
        return {
            "type": "mapping",
            "value": [
                [key, _canonical_artifact_value(value[key])]
                for key in sorted(value)
            ],
        }
    if isinstance(value, tuple):
        return {
            "type": "tuple",
            "value": [_canonical_artifact_value(item) for item in value],
        }
    if isinstance(value, list):
        return {
            "type": "list",
            "value": [_canonical_artifact_value(item) for item in value],
        }
    if isinstance(value, (set, frozenset)):
        items = [_canonical_artifact_value(item) for item in value]
        return {
            "type": "set",
            "value": sorted(items, key=_canonical_json),
        }
    raise ArtifactTypeMismatchError(
        f"cannot encode {type(value).__name__} as a canonical artifact value"
    )


def artifact_value_fingerprint(value: object) -> str:
    try:
        projection = _canonical_artifact_value(value)
        canonical_bytes = _canonical_json(projection).encode("utf-8")
    except ArtifactTypeMismatchError:
        raise
    except (RecursionError, TypeError, ValueError) as exc:
        raise ArtifactTypeMismatchError(
            "cannot encode cyclic or invalid data as a canonical artifact value"
        ) from exc
    return hashlib.sha256(canonical_bytes).hexdigest()


def _canonical_evidence_refs(
    references: tuple[EvidenceRef, ...],
) -> tuple[EvidenceRef, ...]:
    by_id: dict[str, EvidenceRef] = {}
    for reference in references:
        current = by_id.get(reference.evidence_id)
        if current is not None and current != reference:
            raise ArtifactProviderConflictError(
                "artifact lineage has conflicting revisions or content for "
                f"{reference.evidence_id}"
            )
        by_id[reference.evidence_id] = reference
    return tuple(
        sorted(
            by_id.values(),
            key=lambda item: (
                item.evidence_id,
                item.revision,
                item.content_fingerprint,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class ArtifactKey(Generic[T]):
    artifact_id: str
    schema_version: str
    value_type: type[T]

    def __post_init__(self) -> None:
        if not isinstance(self.artifact_id, str) or not self.artifact_id.strip():
            raise ArtifactDefinitionError("artifact_id must be non-empty")
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise ArtifactDefinitionError("schema_version must be non-empty")
        if not isinstance(self.value_type, type):
            raise ArtifactDefinitionError("value_type must be a runtime type")

    @property
    def identity(self) -> ArtifactIdentity:
        return self.artifact_id, self.schema_version


class ArtifactMode(StrEnum):
    EXCLUSIVE = "exclusive"
    COLLECTION = "collection"


@dataclass(frozen=True, slots=True)
class ArtifactDefinition(Generic[T]):
    key: ArtifactKey[T]
    mode: ArtifactMode
    reducer_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.key, ArtifactKey):
            raise ArtifactDefinitionError("key must be an ArtifactKey")
        if not isinstance(self.mode, ArtifactMode):
            raise ArtifactDefinitionError("mode must be an ArtifactMode")
        if self.mode is ArtifactMode.COLLECTION and not (
            isinstance(self.reducer_id, str) and self.reducer_id.strip()
        ):
            raise ArtifactDefinitionError(
                f"collection artifact {self.key.artifact_id} requires a reducer"
            )
        if self.mode is ArtifactMode.EXCLUSIVE and self.reducer_id is not None:
            raise ArtifactDefinitionError(
                f"exclusive artifact {self.key.artifact_id} cannot declare a reducer"
            )


@dataclass(frozen=True, slots=True)
class ArtifactWrite(Generic[T]):
    key: ArtifactKey[T]
    value: T
    producer_id: str
    evidence_refs: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.key, ArtifactKey):
            raise ArtifactDefinitionError("key must be an ArtifactKey")
        if not isinstance(self.producer_id, str) or not self.producer_id.strip():
            raise ArtifactDefinitionError("producer_id must be non-empty")
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(reference, EvidenceRef) for reference in self.evidence_refs
        ):
            raise ArtifactDefinitionError("evidence_refs must contain EvidenceRef values")
        object.__setattr__(
            self,
            "evidence_refs",
            _canonical_evidence_refs(self.evidence_refs),
        )
        if not isinstance(self.value, self.key.value_type):
            raise ArtifactTypeMismatchError(
                f"artifact {self.key.artifact_id} requires "
                f"{self.key.value_type.__name__}, got {type(self.value).__name__}"
            )


@dataclass(frozen=True, slots=True)
class ArtifactEnvelope(Generic[T]):
    key: ArtifactKey[T]
    value: T
    producer_ids: tuple[str, ...]
    evidence_refs: tuple[EvidenceRef, ...]
    value_fingerprint: str


class ArtifactCatalog:
    def __init__(self) -> None:
        self._definitions: dict[ArtifactIdentity, ArtifactDefinition[object]] = {}
        self._reducers: dict[ArtifactIdentity, ArtifactReducer] = {}

    def register(
        self,
        definition: ArtifactDefinition[object],
        *,
        reducer: ArtifactReducer | None = None,
    ) -> None:
        identity = definition.key.identity
        if identity in self._definitions:
            raise ArtifactDefinitionError(
                f"duplicate artifact definition: {definition.key.artifact_id}@{definition.key.schema_version}"
            )
        if definition.mode is ArtifactMode.COLLECTION and reducer is None:
            raise ArtifactDefinitionError(
                f"collection artifact {definition.key.artifact_id} requires a reducer implementation"
            )
        if definition.mode is ArtifactMode.EXCLUSIVE and reducer is not None:
            raise ArtifactDefinitionError(
                f"exclusive artifact {definition.key.artifact_id} cannot register a reducer"
            )
        self._definitions[identity] = definition
        if reducer is not None:
            self._reducers[identity] = reducer

    def definition(self, key: ArtifactKey[T]) -> ArtifactDefinition[T]:
        definition = self._definitions.get(key.identity)
        if definition is None:
            raise ArtifactDefinitionError(
                f"artifact is not registered: {key.artifact_id}@{key.schema_version}"
            )
        if definition.key != key:
            raise ArtifactTypeMismatchError(
                f"artifact {key.artifact_id} schema {key.schema_version} is registered as "
                f"{definition.key.value_type.__name__}, not {key.value_type.__name__}"
            )
        return definition  # type: ignore[return-value]

    def reducer(self, key: ArtifactKey[object]) -> ArtifactReducer:
        try:
            return self._reducers[key.identity]
        except KeyError as exc:
            raise ArtifactDefinitionError(
                f"collection artifact {key.artifact_id} has no reducer implementation"
            ) from exc


class ArtifactSnapshot:
    __slots__ = ("_envelopes",)
    _envelopes: Mapping[ArtifactIdentity, ArtifactEnvelope[object]]

    def __init__(self, envelopes: Mapping[ArtifactIdentity, ArtifactEnvelope[object]]):
        object.__setattr__(
            self,
            "_envelopes",
            MappingProxyType(copy.deepcopy(dict(envelopes))),
        )

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("ArtifactSnapshot is immutable")

    def __deepcopy__(self, memo: dict[int, object]) -> ArtifactSnapshot:
        return self

    def _find(self, key: ArtifactKey[T]) -> ArtifactEnvelope[T] | None:
        envelope = self._envelopes.get(key.identity)
        if envelope is None:
            return None
        if envelope.key != key:
            raise ArtifactTypeMismatchError(
                f"artifact {key.artifact_id} does not match requested type/schema"
            )
        return cast(ArtifactEnvelope[T], envelope)

    def require(self, key: ArtifactKey[T]) -> T:
        envelope = self._find(key)
        if envelope is None:
            raise ArtifactNotFoundError(
                f"required artifact is missing: {key.artifact_id}@{key.schema_version}"
            )
        return copy.deepcopy(envelope.value)

    def get(self, key: ArtifactKey[T]) -> T | None:
        envelope = self._find(key)
        return None if envelope is None else copy.deepcopy(envelope.value)

    def envelope(self, key: ArtifactKey[T]) -> ArtifactEnvelope[T] | None:
        envelope = self._find(key)
        return None if envelope is None else copy.deepcopy(envelope)

    def envelopes(self) -> tuple[ArtifactEnvelope[object], ...]:
        return tuple(
            copy.deepcopy(self._envelopes[identity])
            for identity in sorted(self._envelopes)
        )

    def merged_with(self, other: ArtifactSnapshot) -> ArtifactSnapshot:
        overlap = set(self._envelopes) & set(other._envelopes)
        if overlap:
            artifact_ids = ", ".join(
                f"{artifact_id}@{schema_version}"
                for artifact_id, schema_version in sorted(overlap)
            )
            raise ArtifactProviderConflictError(
                f"cannot merge snapshots with overlapping artifacts: {artifact_ids}"
            )
        return ArtifactSnapshot({**self._envelopes, **other._envelopes})


class ArtifactStore:
    def __init__(self, catalog: ArtifactCatalog):
        self._catalog = catalog
        self._writes: dict[ArtifactIdentity, list[ArtifactWrite[object]]] = {}

    def write(self, write: ArtifactWrite[object]) -> None:
        definition = self._catalog.definition(write.key)
        existing = self._writes.setdefault(write.key.identity, [])
        if definition.mode is ArtifactMode.EXCLUSIVE and existing:
            raise ArtifactProviderConflictError(
                f"exclusive artifact {write.key.artifact_id} already has provider "
                f"{existing[0].producer_id}; rejected {write.producer_id}"
            )
        if any(item.producer_id == write.producer_id for item in existing):
            raise ArtifactProviderConflictError(
                f"artifact {write.key.artifact_id} has duplicate provider {write.producer_id}"
            )
        existing.append(copy.deepcopy(write))

    def freeze(self) -> ArtifactSnapshot:
        envelopes: dict[ArtifactIdentity, ArtifactEnvelope[object]] = {}
        for identity, registered_writes in self._writes.items():
            writes = tuple(sorted(registered_writes, key=lambda item: item.producer_id))
            definition = self._catalog.definition(writes[0].key)
            if definition.mode is ArtifactMode.EXCLUSIVE:
                value = copy.deepcopy(writes[0].value)
            else:
                values = tuple(copy.deepcopy(item.value) for item in writes)
                value = self._catalog.reducer(writes[0].key)(values)
                if not isinstance(value, writes[0].key.value_type):
                    raise ArtifactTypeMismatchError(
                        f"reducer for {writes[0].key.artifact_id} returned "
                        f"{type(value).__name__}, expected {writes[0].key.value_type.__name__}"
                    )
            envelopes[identity] = ArtifactEnvelope(
                key=writes[0].key,
                value=copy.deepcopy(value),
                producer_ids=tuple(item.producer_id for item in writes),
                evidence_refs=_canonical_evidence_refs(
                    tuple(
                        reference
                        for item in writes
                        for reference in item.evidence_refs
                    )
                ),
                value_fingerprint=artifact_value_fingerprint(value),
            )
        return ArtifactSnapshot(envelopes)
