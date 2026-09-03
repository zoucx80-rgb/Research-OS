from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from research_os.domain.evidence import Evidence


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EvidenceRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    revision: int = Field(ge=1)
    content_fingerprint: str

    @field_validator("evidence_id", "content_fingerprint")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("evidence reference fields must be non-empty")
        return value

    @field_validator("content_fingerprint")
    @classmethod
    def _sha256(cls, value: str) -> str:
        if not _SHA256.fullmatch(value):
            raise ValueError("content_fingerprint must be lowercase SHA-256 hex")
        return value


class EvidenceSet(BaseModel):
    """A runtime-validated immutable collection of PIT-bound evidence rows."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: tuple[Evidence, ...] = Field(default_factory=tuple)
    evidence_refs: tuple[EvidenceRef, ...] = Field(default_factory=tuple)

    @model_validator(mode="after")
    def _bind_every_item_to_its_revision(self) -> EvidenceSet:
        by_id = {reference.evidence_id: reference for reference in self.evidence_refs}
        if len(by_id) != len(self.evidence_refs):
            raise ValueError("PIT evidence references must have unique evidence IDs")
        for item in self.items:
            reference = by_id.get(item.evidence_id)
            if (
                reference is None
                or reference.revision != item.revision_no
                or reference.content_fingerprint != evidence_content_fingerprint(item)
            ):
                raise ValueError(
                    f"PIT evidence item is not bound to its revision: {item.evidence_id}"
                )
        if {item.evidence_id for item in self.items} != set(by_id):
            raise ValueError("PIT evidence references must match evidence items exactly")
        return self


def evidence_content_fingerprint(evidence: Evidence) -> str:
    def canonicalize(value: object) -> object:
        if value is None:
            return {"type": "null"}
        if isinstance(value, bool):
            return {"type": "boolean", "value": value}
        if isinstance(value, Enum):
            return {"type": "enum", "value": canonicalize(value.value)}
        if isinstance(value, str):
            return {"type": "string", "value": value}
        if isinstance(value, int):
            return {"type": "integer", "value": value}
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("evidence values must contain finite floats")
            return {"type": "float", "value": 0.0 if value == 0 else value}
        if isinstance(value, Decimal):
            if not value.is_finite():
                raise ValueError("evidence values must contain finite decimals")
            return {"type": "decimal", "value": str(value)}
        if isinstance(value, datetime):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("evidence datetimes must be timezone-aware")
            return {
                "type": "datetime",
                "value": value.astimezone(timezone.utc)
                .isoformat(timespec="microseconds")
                .replace("+00:00", "Z"),
            }
        if isinstance(value, date):
            return {"type": "date", "value": value.isoformat()}
        if isinstance(value, BaseModel):
            return {
                "type": "model",
                "value": canonicalize(value.model_dump(mode="python", round_trip=True)),
            }
        if is_dataclass(value) and not isinstance(value, type):
            return {
                "type": "dataclass",
                "value": canonicalize(
                    {field.name: getattr(value, field.name) for field in fields(value)}
                ),
            }
        if isinstance(value, Mapping):
            if any(not isinstance(key, str) for key in value):
                raise ValueError("evidence mappings must use string keys")
            return {
                "type": "mapping",
                "value": [[key, canonicalize(value[key])] for key in sorted(value)],
            }
        if isinstance(value, tuple):
            return {
                "type": "tuple",
                "value": [canonicalize(item) for item in value],
            }
        if isinstance(value, list):
            return {
                "type": "list",
                "value": [canonicalize(item) for item in value],
            }
        if isinstance(value, (set, frozenset)):
            items = [canonicalize(item) for item in value]
            return {
                "type": "set",
                "value": sorted(
                    items,
                    key=lambda item: json.dumps(
                        item,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                ),
            }
        raise ValueError(f"evidence value type {type(value).__name__} is not canonicalizable")

    try:
        payload = canonicalize(evidence)
    except RecursionError as exc:
        raise ValueError("evidence values must not contain cycles") from exc
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
