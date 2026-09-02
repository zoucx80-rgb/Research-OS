"""RFC 8785 encoding and controlled artifact decoding for Snapshot Schema 2.0."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Literal, TypeAlias

import rfc8785
from pydantic import BaseModel

from research_os.snapshots.models import ResearchSnapshotPayloadV2, ResearchSnapshotV2


CanonicalValue: TypeAlias = None | bool | int | float | str | list["CanonicalValue"] | dict[str, "CanonicalValue"]
ArtifactDecoder: TypeAlias = Callable[[object], object]


class SnapshotCodecError(ValueError):
    """Raised when an input cannot be safely represented by Snapshot Codec V2."""


def _pydantic_decoder(model: type[BaseModel]) -> ArtifactDecoder:
    def decode(value: object) -> object:
        return model.model_validate(value)

    return decode


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise SnapshotCodecError("Decimal values must be finite")
    if value.is_zero():
        return "0"
    text = format(value.normalize(), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _utc_rfc3339(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise SnapshotCodecError("datetime values must be timezone-aware")
    utc_value = value.astimezone(timezone.utc)
    text = utc_value.isoformat(timespec="microseconds").replace("+00:00", "Z")
    if "." not in text:
        return text
    prefix, suffix = text.split(".", maxsplit=1)
    fraction, zone = suffix[:-1], suffix[-1]
    fraction = fraction.rstrip("0")
    return f"{prefix}{zone}" if not fraction else f"{prefix}.{fraction}{zone}"


def _canonicalize(value: object) -> CanonicalValue:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return {"$ros_type": "integer", "value": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SnapshotCodecError("floating-point values must be finite")
        return 0.0 if value == 0 else value
    if isinstance(value, Decimal):
        return {"$ros_type": "decimal", "value": _decimal_text(value)}
    if isinstance(value, datetime):
        return {"$ros_type": "datetime", "value": _utc_rfc3339(value)}
    if isinstance(value, date):
        return {"$ros_type": "date", "value": value.isoformat()}
    if isinstance(value, Enum):
        return {"$ros_type": "enum", "value": _canonicalize(value.value)}
    if isinstance(value, BaseModel):
        return {
            "$ros_type": "pydantic",
            "value": _canonicalize(
                {
                    field_name: getattr(value, field_name)
                    for field_name in type(value).model_fields
                }
            ),
        }
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise SnapshotCodecError("mappings must use string keys")
        return {
            "$ros_type": "mapping",
            "items": [
                [key, _canonicalize(value[key])]
                for key in sorted(value)
            ],
        }
    if isinstance(value, tuple):
        return {"$ros_type": "tuple", "items": [_canonicalize(item) for item in value]}
    if isinstance(value, list):
        return {"$ros_type": "list", "items": [_canonicalize(item) for item in value]}
    if isinstance(value, (set, frozenset)):
        normalized = [_canonicalize(item) for item in value]
        return {
            "$ros_type": "frozenset" if isinstance(value, frozenset) else "set",
            "items": sorted(normalized, key=rfc8785.dumps),
        }
    raise SnapshotCodecError(f"cannot canonically encode {type(value).__name__}")


def _require_keys(value: dict[str, object], expected: set[str]) -> None:
    if set(value) != expected:
        raise SnapshotCodecError("canonical value has an invalid tagged shape")


def _decanonicalize(value: object) -> object:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(value):
            raise SnapshotCodecError("floating-point values must be finite")
        return float(value)
    if not isinstance(value, dict):
        raise SnapshotCodecError("canonical value must use a tagged container")
    kind = value.get("$ros_type")
    if not isinstance(kind, str):
        raise SnapshotCodecError("canonical value is missing its type tag")
    if kind in {"integer", "decimal", "datetime", "date", "enum", "pydantic"}:
        _require_keys(value, {"$ros_type", "value"})
        tagged_value = value["value"]
        try:
            if kind == "integer" and isinstance(tagged_value, str):
                return int(tagged_value)
            if kind == "decimal" and isinstance(tagged_value, str):
                decimal = Decimal(tagged_value)
                if decimal.is_finite():
                    return decimal
            if kind == "datetime" and isinstance(tagged_value, str):
                parsed = datetime.fromisoformat(tagged_value.replace("Z", "+00:00"))
                if parsed.tzinfo is not None and parsed.utcoffset() is not None:
                    return parsed.astimezone(timezone.utc)
            if kind == "date" and isinstance(tagged_value, str):
                return date.fromisoformat(tagged_value)
            if kind in {"enum", "pydantic"}:
                return _decanonicalize(tagged_value)
        except (TypeError, ValueError) as exc:
            raise SnapshotCodecError("canonical scalar value is invalid") from exc
        raise SnapshotCodecError("canonical scalar value is invalid")
    if kind not in {"mapping", "tuple", "list", "set", "frozenset"}:
        raise SnapshotCodecError("canonical value has an unknown type tag")
    _require_keys(value, {"$ros_type", "items"})
    items = value["items"]
    if not isinstance(items, list):
        raise SnapshotCodecError("canonical container items must be an array")
    if kind == "mapping":
        restored: dict[str, object] = {}
        for entry in items:
            if (
                not isinstance(entry, list)
                or len(entry) != 2
                or not isinstance(entry[0], str)
                or entry[0] in restored
            ):
                raise SnapshotCodecError("canonical mapping entry is invalid")
            restored[entry[0]] = _decanonicalize(entry[1])
        return restored
    restored_items = [_decanonicalize(item) for item in items]
    if kind == "tuple":
        return tuple(restored_items)
    if kind == "list":
        return restored_items
    try:
        return frozenset(restored_items) if kind == "frozenset" else set(restored_items)
    except TypeError as exc:
        raise SnapshotCodecError("canonical set contains an unhashable value") from exc


def _encode(value: object) -> bytes:
    try:
        return rfc8785.dumps(_canonicalize(value))
    except SnapshotCodecError:
        raise
    except (OverflowError, TypeError, ValueError, RecursionError) as exc:
        raise SnapshotCodecError("value cannot be encoded as RFC 8785 JSON") from exc


class ArtifactDecoderRegistry:
    """Explicit decoder allowlist keyed by artifact schema and type identity."""

    def __init__(self) -> None:
        self._decoders: dict[tuple[str, str, str], ArtifactDecoder] = {}

    def register(
        self,
        *,
        artifact_id: str,
        schema_version: str,
        type_id: str,
        decoder: ArtifactDecoder,
    ) -> None:
        key = artifact_id, schema_version, type_id
        if not all(isinstance(item, str) and item.strip() for item in key):
            raise SnapshotCodecError("artifact decoder identity fields must be non-empty")
        if not callable(decoder):
            raise SnapshotCodecError("artifact decoder must be callable")
        if key in self._decoders:
            raise SnapshotCodecError("artifact decoder is already registered")
        self._decoders[key] = decoder

    def decode(
        self,
        *,
        artifact_id: str,
        schema_version: str,
        type_id: str,
        payload: object,
    ) -> object:
        decoder = self._decoders.get((artifact_id, schema_version, type_id))
        if decoder is None:
            raise SnapshotCodecError("artifact decoder is not registered")
        try:
            return decoder(payload)
        except SnapshotCodecError:
            raise
        except (TypeError, ValueError) as exc:
            raise SnapshotCodecError("artifact decoder rejected payload") from exc


def build_core_artifact_decoder_registry() -> ArtifactDecoderRegistry:
    """Build the explicit allowlist for artifacts owned by the current Core API."""
    from research_os.runtime.core_artifacts import CORE_ARTIFACT_KEYS

    registry = ArtifactDecoderRegistry()
    for key in CORE_ARTIFACT_KEYS:
        value_type = key.value_type
        if not issubclass(value_type, BaseModel):
            raise SnapshotCodecError(
                f"core artifact {key.artifact_id} has no controlled model decoder"
            )
        registry.register(
            artifact_id=key.artifact_id,
            schema_version=key.schema_version,
            type_id=value_type.__qualname__,
            decoder=_pydantic_decoder(value_type),
        )
    return registry


class SnapshotCodecV2:
    codec_version: Literal["jcs-1"] = "jcs-1"

    def normalize_value(self, value: object) -> CanonicalValue:
        return _canonicalize(value)

    def encode_value(self, value: object) -> bytes:
        return _encode(value)

    def decode_value(self, value: bytes | str) -> object:
        try:
            encoded = value.decode("utf-8") if isinstance(value, bytes) else value
            return _decanonicalize(json.loads(encoded))
        except SnapshotCodecError:
            raise
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SnapshotCodecError("value is not valid canonical JSON") from exc

    def encode_research_projection(self, payload: ResearchSnapshotPayloadV2) -> bytes:
        if not isinstance(payload, ResearchSnapshotPayloadV2):
            raise SnapshotCodecError("research projection must be ResearchSnapshotPayloadV2")
        return _encode(payload)

    def research_digest(self, payload: ResearchSnapshotPayloadV2) -> str:
        return hashlib.sha256(self.encode_research_projection(payload)).hexdigest()

    def encode_envelope(self, snapshot: ResearchSnapshotV2) -> bytes:
        if not isinstance(snapshot, ResearchSnapshotV2):
            raise SnapshotCodecError("snapshot envelope must be ResearchSnapshotV2")
        return _encode(snapshot)

    def integrity_digest(self, snapshot: ResearchSnapshotV2) -> str:
        return hashlib.sha256(self.encode_envelope(snapshot)).hexdigest()
